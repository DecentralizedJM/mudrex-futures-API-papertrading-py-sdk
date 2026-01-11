"""
Liquidation engine for paper trading.
Simulates automatic position liquidation when margin is exhausted.

Liquidation Logic (ISOLATED Margin):
- Each position has its own margin (initial margin = notional / leverage)
- Liquidation occurs when unrealized loss >= margin - maintenance margin
- Maintenance margin rate is typically 0.5% of position notional

Liquidation Price Formula:
LONG:  Liq Price = Entry × (1 - 1/Leverage + MMR)
SHORT: Liq Price = Entry × (1 + 1/Leverage - MMR)

Where MMR = Maintenance Margin Rate (default 0.5% = 0.005)

Liquidation Fees:
- Liquidation fee = 0.5% of position value at liquidation
- Remaining margin after fee is returned to wallet
"""

import threading
import time
import uuid
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Optional, List, Callable, Any, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from .engine import PaperTradingEngine
    from .external_data import ExternalDataService

logger = logging.getLogger(__name__)


class LiquidationReason(Enum):
    """Reason for liquidation."""
    MARGIN_CALL = "margin_call"  # Mark price hit liquidation price
    MANUAL = "manual"  # Manually triggered
    BANKRUPTCY = "bankruptcy"  # Position value went negative


@dataclass
class LiquidationEvent:
    """Record of a liquidation event."""
    liquidation_id: str
    position_id: str
    symbol: str
    side: str
    reason: LiquidationReason
    entry_price: Decimal
    liquidation_price: Decimal
    mark_price_at_liq: Decimal
    quantity: Decimal
    margin_lost: Decimal  # Initial margin that was lost
    liquidation_fee: Decimal
    remaining_margin: Decimal  # Amount returned to wallet (usually 0)
    liquidation_time: datetime
    leverage: int
    
    @property
    def total_loss(self) -> Decimal:
        """Total loss from liquidation."""
        return self.margin_lost + self.liquidation_fee
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "liquidation_id": self.liquidation_id,
            "position_id": self.position_id,
            "symbol": self.symbol,
            "side": self.side,
            "reason": self.reason.value,
            "entry_price": str(self.entry_price),
            "liquidation_price": str(self.liquidation_price),
            "mark_price_at_liq": str(self.mark_price_at_liq),
            "quantity": str(self.quantity),
            "margin_lost": str(self.margin_lost),
            "liquidation_fee": str(self.liquidation_fee),
            "remaining_margin": str(self.remaining_margin),
            "liquidation_time": self.liquidation_time.isoformat(),
            "leverage": self.leverage,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "LiquidationEvent":
        """Create from dictionary."""
        return cls(
            liquidation_id=data["liquidation_id"],
            position_id=data["position_id"],
            symbol=data["symbol"],
            side=data["side"],
            reason=LiquidationReason(data["reason"]),
            entry_price=Decimal(data["entry_price"]),
            liquidation_price=Decimal(data["liquidation_price"]),
            mark_price_at_liq=Decimal(data["mark_price_at_liq"]),
            quantity=Decimal(data["quantity"]),
            margin_lost=Decimal(data["margin_lost"]),
            liquidation_fee=Decimal(data["liquidation_fee"]),
            remaining_margin=Decimal(data["remaining_margin"]),
            liquidation_time=datetime.fromisoformat(data["liquidation_time"]),
            leverage=data["leverage"],
        )


@dataclass
class MarginStatus:
    """Current margin status for a position."""
    position_id: str
    symbol: str
    side: str
    entry_price: Decimal
    mark_price: Decimal
    quantity: Decimal
    leverage: int
    
    initial_margin: Decimal
    maintenance_margin: Decimal
    unrealized_pnl: Decimal
    margin_balance: Decimal  # initial_margin + unrealized_pnl
    margin_ratio: Decimal  # margin_balance / maintenance_margin
    liquidation_price: Decimal
    
    is_at_risk: bool  # margin_ratio < 1.5
    is_liquidatable: bool  # margin_ratio <= 1.0
    distance_to_liq: Decimal  # percentage distance to liquidation price


class LiquidationEngine:
    """
    Liquidation engine for paper trading.
    
    Features:
    - Automatic liquidation when mark price hits liquidation price
    - Real-time margin ratio monitoring
    - Liquidation event history
    - Warning callbacks when positions at risk
    
    Configuration:
    - maintenance_margin_rate: Default 0.5% (0.005)
    - liquidation_fee_rate: Default 0.5% (0.005)
    - warning_threshold: Warn when margin_ratio < 1.5
    
    Usage:
        engine = LiquidationEngine(paper_engine, external_data)
        engine.start()  # Start background monitoring
        # ... trading happens ...
        engine.stop()   # Stop when done
    """
    
    # Default rates
    DEFAULT_MMR = Decimal("0.005")  # 0.5% maintenance margin rate
    DEFAULT_LIQ_FEE = Decimal("0.005")  # 0.5% liquidation fee
    DEFAULT_WARNING_THRESHOLD = Decimal("1.5")  # Warn at 150% margin ratio
    
    def __init__(
        self,
        engine: "PaperTradingEngine",
        external_data: "ExternalDataService",
        maintenance_margin_rate: Optional[Decimal] = None,
        liquidation_fee_rate: Optional[Decimal] = None,
        warning_threshold: Optional[Decimal] = None,
        check_interval: int = 5,  # Check every 5 seconds
        enabled: bool = True,
        on_liquidation: Optional[Callable[[LiquidationEvent], None]] = None,
        on_margin_warning: Optional[Callable[[MarginStatus], None]] = None,
    ):
        """
        Initialize the liquidation engine.
        
        Args:
            engine: Paper trading engine
            external_data: External data service for mark prices
            maintenance_margin_rate: MMR for liquidation calc (default 0.5%)
            liquidation_fee_rate: Fee charged on liquidation (default 0.5%)
            warning_threshold: Margin ratio threshold for warnings (default 1.5)
            check_interval: How often to check positions (seconds)
            enabled: Whether liquidation is enabled
            on_liquidation: Callback when position is liquidated
            on_margin_warning: Callback when position is at risk
        """
        self._engine = engine
        self._external_data = external_data
        self._mmr = maintenance_margin_rate or self.DEFAULT_MMR
        self._liq_fee_rate = liquidation_fee_rate or self.DEFAULT_LIQ_FEE
        self._warning_threshold = warning_threshold or self.DEFAULT_WARNING_THRESHOLD
        self._check_interval = check_interval
        self._enabled = enabled
        self._on_liquidation = on_liquidation
        self._on_margin_warning = on_margin_warning
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Track warned positions to avoid duplicate warnings
        self._warned_positions: set = set()
        
        # Liquidation history
        self._liquidations: List[LiquidationEvent] = []
    
    @property
    def enabled(self) -> bool:
        """Whether liquidation is enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        """Enable or disable liquidation."""
        self._enabled = value
    
    @property
    def is_running(self) -> bool:
        """Whether the engine is running."""
        return self._running
    
    @property
    def liquidations(self) -> List[LiquidationEvent]:
        """Get all liquidation events."""
        return self._liquidations.copy()
    
    @property
    def maintenance_margin_rate(self) -> Decimal:
        """Get maintenance margin rate."""
        return self._mmr
    
    @property
    def liquidation_fee_rate(self) -> Decimal:
        """Get liquidation fee rate."""
        return self._liq_fee_rate
    
    def start(self):
        """Start the background liquidation monitor."""
        if self._running:
            logger.warning("Liquidation engine already running")
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="LiquidationEngine",
            daemon=True
        )
        self._thread.start()
        logger.info("Liquidation engine started")
    
    def stop(self):
        """Stop the background liquidation monitor."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Liquidation engine stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                if self._enabled:
                    self._check_positions()
            except Exception as e:
                logger.error(f"Error in liquidation engine: {e}")
            
            time.sleep(self._check_interval)
    
    def _check_positions(self):
        """Check all open positions for liquidation."""
        positions = self._engine.list_open_positions()
        
        for position in positions:
            try:
                status = self.get_margin_status(position)
                
                if status.is_liquidatable:
                    self._liquidate_position(position, status)
                elif status.is_at_risk:
                    self._warn_margin(status)
                else:
                    # Clear warning if position is safe now
                    self._warned_positions.discard(position.position_id)
                    
            except Exception as e:
                logger.error(f"Error checking position {position.position_id}: {e}")
    
    def calculate_liquidation_price(
        self,
        entry_price: Decimal,
        leverage: int,
        side: str,  # "LONG" or "SHORT"
        mmr: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate the liquidation price for a position.
        
        Formula (ISOLATED margin):
        LONG:  Liq = Entry × (1 - 1/Leverage + MMR)
        SHORT: Liq = Entry × (1 + 1/Leverage - MMR)
        
        Args:
            entry_price: Position entry price
            leverage: Position leverage
            side: "LONG" or "SHORT"
            mmr: Maintenance margin rate (default 0.5%)
            
        Returns:
            Liquidation price
        """
        mmr = mmr or self._mmr
        leverage_factor = Decimal("1") / Decimal(leverage)
        
        if side == "LONG":
            # LONG liquidates when price drops
            liq_price = entry_price * (Decimal("1") - leverage_factor + mmr)
        else:
            # SHORT liquidates when price rises
            liq_price = entry_price * (Decimal("1") + leverage_factor - mmr)
        
        return liq_price.quantize(Decimal("0.01"))
    
    def get_margin_status(self, position: Any) -> MarginStatus:
        """
        Get current margin status for a position.
        
        Args:
            position: Position object from engine
            
        Returns:
            MarginStatus with all margin information
        """
        # Get current mark price
        try:
            mark_price = self._external_data.get_mark_price(position.symbol)
        except Exception:
            # Fall back to position's current price or entry
            mark_price = getattr(position, 'current_price', position.entry_price)
        
        side = position.side.value
        entry_price = position.entry_price
        quantity = position.quantity
        leverage = position.leverage
        
        # Calculate position values
        notional = quantity * entry_price
        initial_margin = notional / Decimal(leverage)
        maintenance_margin = notional * self._mmr
        
        # Calculate unrealized PnL
        if side == "LONG":
            unrealized_pnl = quantity * (mark_price - entry_price)
        else:
            unrealized_pnl = quantity * (entry_price - mark_price)
        
        # Margin balance = initial margin + unrealized PnL
        margin_balance = initial_margin + unrealized_pnl
        
        # Margin ratio = margin_balance / maintenance_margin
        if maintenance_margin > 0:
            margin_ratio = margin_balance / maintenance_margin
        else:
            margin_ratio = Decimal("999")  # Safe
        
        # Liquidation price
        liq_price = self.calculate_liquidation_price(entry_price, leverage, side)
        
        # Distance to liquidation (percentage)
        if side == "LONG":
            distance_to_liq = ((mark_price - liq_price) / mark_price) * 100
        else:
            distance_to_liq = ((liq_price - mark_price) / mark_price) * 100
        
        return MarginStatus(
            position_id=position.position_id,
            symbol=position.symbol,
            side=side,
            entry_price=entry_price,
            mark_price=mark_price,
            quantity=quantity,
            leverage=leverage,
            initial_margin=initial_margin,
            maintenance_margin=maintenance_margin,
            unrealized_pnl=unrealized_pnl,
            margin_balance=margin_balance,
            margin_ratio=margin_ratio,
            liquidation_price=liq_price,
            is_at_risk=margin_ratio < self._warning_threshold,
            is_liquidatable=margin_ratio <= Decimal("1"),
            distance_to_liq=distance_to_liq,
        )
    
    def _liquidate_position(self, position: Any, status: MarginStatus):
        """Liquidate a position."""
        with self._lock:
            logger.warning(
                f"LIQUIDATING {position.symbol} {position.side.value} - "
                f"Mark: {status.mark_price}, Liq: {status.liquidation_price}"
            )
            
            # Calculate liquidation values
            notional_at_liq = position.quantity * status.mark_price
            liquidation_fee = notional_at_liq * self._liq_fee_rate
            
            # The margin is lost (minus any remaining after covering losses)
            margin_lost = status.initial_margin + status.unrealized_pnl
            if margin_lost < 0:
                margin_lost = status.initial_margin  # Can't lose more than initial
            
            remaining_margin = max(Decimal("0"), status.margin_balance - liquidation_fee)
            
            # Create liquidation event
            event = LiquidationEvent(
                liquidation_id=f"liq_{uuid.uuid4().hex[:12]}",
                position_id=position.position_id,
                symbol=position.symbol,
                side=position.side.value,
                reason=LiquidationReason.MARGIN_CALL,
                entry_price=position.entry_price,
                liquidation_price=status.liquidation_price,
                mark_price_at_liq=status.mark_price,
                quantity=position.quantity,
                margin_lost=margin_lost,
                liquidation_fee=liquidation_fee,
                remaining_margin=remaining_margin,
                liquidation_time=datetime.now(timezone.utc),
                leverage=position.leverage,
            )
            
            # Force close position in engine
            try:
                # Close at liquidation price (or current mark)
                self._engine.close_position(
                    position_id=position.position_id,
                    close_price=status.mark_price,
                    reason="LIQUIDATED"
                )
            except Exception as e:
                # If engine close fails, manually remove position
                logger.error(f"Error closing liquidated position: {e}")
                if position.position_id in self._engine._positions:
                    del self._engine._positions[position.position_id]
            
            # Deduct liquidation fee from wallet
            self._engine._wallet.balance -= liquidation_fee
            
            # Record event
            self._liquidations.append(event)
            
            # Clear warning
            self._warned_positions.discard(position.position_id)
            
            # Callback
            if self._on_liquidation:
                try:
                    self._on_liquidation(event)
                except Exception as e:
                    logger.error(f"Error in liquidation callback: {e}")
            
            logger.warning(
                f"Position {position.position_id} liquidated. "
                f"Loss: {event.total_loss}, Fee: {liquidation_fee}"
            )
    
    def _warn_margin(self, status: MarginStatus):
        """Issue margin warning for at-risk position."""
        if status.position_id in self._warned_positions:
            return  # Already warned
        
        self._warned_positions.add(status.position_id)
        
        logger.warning(
            f"MARGIN WARNING: {status.symbol} {status.side} - "
            f"Margin ratio: {status.margin_ratio:.2f}, "
            f"Distance to liq: {status.distance_to_liq:.1f}%"
        )
        
        if self._on_margin_warning:
            try:
                self._on_margin_warning(status)
            except Exception as e:
                logger.error(f"Error in margin warning callback: {e}")
    
    def check_position_now(self, position_id: str) -> Optional[MarginStatus]:
        """
        Manually check a specific position.
        
        Args:
            position_id: Position to check
            
        Returns:
            MarginStatus or None if position not found
        """
        for position in self._engine.list_open_positions():
            if position.position_id == position_id:
                return self.get_margin_status(position)
        return None
    
    def get_all_margin_status(self) -> List[MarginStatus]:
        """Get margin status for all open positions."""
        positions = self._engine.list_open_positions()
        return [self.get_margin_status(p) for p in positions]
    
    def get_at_risk_positions(self) -> List[MarginStatus]:
        """Get all positions that are at risk of liquidation."""
        return [s for s in self.get_all_margin_status() if s.is_at_risk]
    
    def get_total_liquidation_losses(self) -> Decimal:
        """Get total losses from all liquidations."""
        return sum(liq.total_loss for liq in self._liquidations)
    
    def clear_history(self):
        """Clear liquidation history."""
        with self._lock:
            self._liquidations.clear()
            self._warned_positions.clear()
    
    def to_state(self) -> Dict:
        """Serialize state for persistence."""
        return {
            "liquidations": [liq.to_dict() for liq in self._liquidations],
            "mmr": str(self._mmr),
            "liq_fee_rate": str(self._liq_fee_rate),
        }
    
    def from_state(self, state: Dict):
        """Restore state from persistence."""
        self._liquidations = [
            LiquidationEvent.from_dict(liq) 
            for liq in state.get("liquidations", [])
        ]
        if "mmr" in state:
            self._mmr = Decimal(state["mmr"])
        if "liq_fee_rate" in state:
            self._liq_fee_rate = Decimal(state["liq_fee_rate"])
