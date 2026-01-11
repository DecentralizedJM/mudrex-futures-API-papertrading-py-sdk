"""
Funding rate payment engine for paper trading.
Simulates 8-hour funding payments on perpetual futures.

Funding Logic:
- Funding is exchanged every 8 hours (00:00, 08:00, 16:00 UTC)
- Positive funding rate: LONG pays SHORT
- Negative funding rate: SHORT pays LONG

Payment Calculation:
- Payment = Position Value × Funding Rate
- Position Value = Quantity × Mark Price

Example:
- LONG 1 BTC @ $100,000 mark price
- Funding rate = +0.01% (0.0001)
- Payment = $100,000 × 0.0001 = $10 (LONG pays $10)
"""

import threading
import time
import uuid
import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Callable, Any, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .engine import PaperTradingEngine
    from .external_data import ExternalDataService

logger = logging.getLogger(__name__)


@dataclass
class FundingPayment:
    """Record of a funding payment."""
    payment_id: str
    position_id: str
    symbol: str
    side: str  # "LONG" or "SHORT"
    funding_rate: Decimal
    position_value: Decimal  # Notional value at payment time
    payment_amount: Decimal  # Positive = received, Negative = paid
    payment_time: datetime
    mark_price: Decimal
    quantity: Decimal
    
    @property
    def is_received(self) -> bool:
        """Whether funding was received (vs paid)."""
        return self.payment_amount > 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "payment_id": self.payment_id,
            "position_id": self.position_id,
            "symbol": self.symbol,
            "side": self.side,
            "funding_rate": str(self.funding_rate),
            "position_value": str(self.position_value),
            "payment_amount": str(self.payment_amount),
            "payment_time": self.payment_time.isoformat(),
            "mark_price": str(self.mark_price),
            "quantity": str(self.quantity),
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "FundingPayment":
        """Create from dictionary."""
        return cls(
            payment_id=data["payment_id"],
            position_id=data["position_id"],
            symbol=data["symbol"],
            side=data["side"],
            funding_rate=Decimal(data["funding_rate"]),
            position_value=Decimal(data["position_value"]),
            payment_amount=Decimal(data["payment_amount"]),
            payment_time=datetime.fromisoformat(data["payment_time"]),
            mark_price=Decimal(data["mark_price"]),
            quantity=Decimal(data["quantity"]),
        )


@dataclass
class FundingStats:
    """Statistics for funding payments."""
    total_paid: Decimal = Decimal("0")
    total_received: Decimal = Decimal("0")
    net_funding: Decimal = Decimal("0")
    payment_count: int = 0
    
    def add_payment(self, amount: Decimal):
        """Add a payment to stats."""
        self.payment_count += 1
        if amount > 0:
            self.total_received += amount
        else:
            self.total_paid += abs(amount)
        self.net_funding = self.total_received - self.total_paid


class FundingMonitor:
    """
    Background monitor for funding rate payments.
    
    Features:
    - Automatic 8-hour funding settlement
    - Real-time funding rate from external data
    - Funding payment history
    - Statistics tracking
    
    Usage:
        monitor = FundingMonitor(engine, external_data)
        monitor.start()  # Start background monitoring
        # ... trading happens ...
        monitor.stop()   # Stop when done
    """
    
    # Standard funding hours (UTC)
    FUNDING_HOURS = [0, 8, 16]
    
    def __init__(
        self,
        engine: "PaperTradingEngine",
        external_data: "ExternalDataService",
        check_interval: int = 60,  # Check every minute
        enabled: bool = True,
        on_funding_payment: Optional[Callable[[FundingPayment], None]] = None,
    ):
        """
        Initialize the funding monitor.
        
        Args:
            engine: Paper trading engine to apply payments to
            external_data: External data service for funding rates
            check_interval: How often to check for funding (seconds)
            enabled: Whether funding is enabled
            on_funding_payment: Optional callback when funding is paid/received
        """
        self._engine = engine
        self._external_data = external_data
        self._check_interval = check_interval
        self._enabled = enabled
        self._on_funding_payment = on_funding_payment
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Track last processed funding time per position
        self._last_funding_time: Dict[str, datetime] = {}
        
        # Payment history
        self._payments: List[FundingPayment] = []
        self._stats = FundingStats()
    
    @property
    def enabled(self) -> bool:
        """Whether funding is enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        """Enable or disable funding."""
        self._enabled = value
    
    @property
    def is_running(self) -> bool:
        """Whether the monitor is running."""
        return self._running
    
    @property
    def payments(self) -> List[FundingPayment]:
        """Get all funding payments."""
        return self._payments.copy()
    
    @property
    def stats(self) -> FundingStats:
        """Get funding statistics."""
        return self._stats
    
    def start(self):
        """Start the background funding monitor."""
        if self._running:
            logger.warning("Funding monitor already running")
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="FundingMonitor",
            daemon=True
        )
        self._thread.start()
        logger.info("Funding monitor started")
    
    def stop(self):
        """Stop the background funding monitor."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Funding monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                if self._enabled:
                    self._process_funding()
            except Exception as e:
                logger.error(f"Error in funding monitor: {e}")
            
            time.sleep(self._check_interval)
    
    def _process_funding(self):
        """Check and process funding for all open positions."""
        positions = self._engine.list_open_positions()
        if not positions:
            return
        
        now = datetime.now(timezone.utc)
        
        for position in positions:
            try:
                self._process_position_funding(position, now)
            except Exception as e:
                logger.error(f"Error processing funding for {position.position_id}: {e}")
    
    def _process_position_funding(self, position: Any, now: datetime):
        """Process funding for a single position."""
        # Get the last funding time we processed for this position
        last_processed = self._last_funding_time.get(position.position_id)
        
        # Find all funding times that should have occurred since position opened
        # or since last processed
        start_time = last_processed or position.opened_at
        
        # Get funding times between start_time and now
        funding_times = self._get_funding_times_between(start_time, now)
        
        if not funding_times:
            return
        
        # Process each funding time
        for funding_time in funding_times:
            # Skip if already processed
            if last_processed and funding_time <= last_processed:
                continue
            
            # Get funding info
            try:
                funding_info = self._external_data.get_funding_info(position.symbol)
            except Exception as e:
                logger.warning(f"Failed to get funding info for {position.symbol}: {e}")
                continue
            
            # Calculate payment
            payment = self._calculate_funding_payment(
                position=position,
                funding_rate=funding_info.funding_rate,
                mark_price=funding_info.mark_price,
                funding_time=funding_time,
            )
            
            # Apply payment
            self._apply_funding_payment(payment)
            
            # Update last processed time
            self._last_funding_time[position.position_id] = funding_time
            
            logger.info(
                f"Funding payment: {position.symbol} {position.side.value} "
                f"rate={funding_info.funding_rate:.6f} amount={payment.payment_amount:.4f}"
            )
    
    def _get_funding_times_between(
        self, 
        start: datetime, 
        end: datetime
    ) -> List[datetime]:
        """Get all funding times between start and end."""
        funding_times = []
        
        # Start from the beginning of the start day
        current = start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        while current <= end:
            for hour in self.FUNDING_HOURS:
                funding_time = current.replace(hour=hour)
                if start < funding_time <= end:
                    funding_times.append(funding_time)
            current += timedelta(days=1)
        
        return sorted(funding_times)
    
    def _calculate_funding_payment(
        self,
        position: Any,
        funding_rate: Decimal,
        mark_price: Decimal,
        funding_time: datetime,
    ) -> FundingPayment:
        """
        Calculate funding payment for a position.
        
        Funding formula:
        - Position Value = Quantity × Mark Price
        - Payment = Position Value × Funding Rate
        
        Direction:
        - Positive rate + LONG = pay (negative payment)
        - Positive rate + SHORT = receive (positive payment)
        - Negative rate + LONG = receive (positive payment)
        - Negative rate + SHORT = pay (negative payment)
        """
        position_value = position.quantity * mark_price
        raw_payment = position_value * funding_rate
        
        # Determine payment direction based on position side
        is_long = position.side.value == "LONG"
        
        if funding_rate > 0:
            # Positive rate: LONG pays, SHORT receives
            payment_amount = -raw_payment if is_long else raw_payment
        else:
            # Negative rate: SHORT pays, LONG receives
            payment_amount = raw_payment if is_long else -raw_payment
        
        return FundingPayment(
            payment_id=f"fund_{uuid.uuid4().hex[:12]}",
            position_id=position.position_id,
            symbol=position.symbol,
            side=position.side.value,
            funding_rate=funding_rate,
            position_value=position_value,
            payment_amount=payment_amount,
            payment_time=funding_time,
            mark_price=mark_price,
            quantity=position.quantity,
        )
    
    def _apply_funding_payment(self, payment: FundingPayment):
        """Apply a funding payment to the engine."""
        with self._lock:
            # Apply to wallet balance
            self._engine._wallet.balance += payment.payment_amount
            
            # Track in position's cumulative funding
            for pos in self._engine._positions.values():
                if pos.position_id == payment.position_id:
                    if not hasattr(pos, 'cumulative_funding'):
                        pos.cumulative_funding = Decimal("0")
                    pos.cumulative_funding += payment.payment_amount
                    break
            
            # Record payment
            self._payments.append(payment)
            self._stats.add_payment(payment.payment_amount)
            
            # Callback
            if self._on_funding_payment:
                try:
                    self._on_funding_payment(payment)
                except Exception as e:
                    logger.error(f"Error in funding callback: {e}")
    
    def process_funding_now(self, symbol: Optional[str] = None) -> List[FundingPayment]:
        """
        Manually trigger funding processing for immediate settlement.
        Useful for testing or forcing funding calculation.
        
        Args:
            symbol: Optional symbol to process (all if None)
            
        Returns:
            List of funding payments applied
        """
        payments = []
        positions = self._engine.list_open_positions()
        
        if symbol:
            positions = [p for p in positions if p.symbol == symbol]
        
        now = datetime.now(timezone.utc)
        
        for position in positions:
            try:
                funding_info = self._external_data.get_funding_info(position.symbol)
                
                payment = self._calculate_funding_payment(
                    position=position,
                    funding_rate=funding_info.funding_rate,
                    mark_price=funding_info.mark_price,
                    funding_time=now,
                )
                
                self._apply_funding_payment(payment)
                payments.append(payment)
                
            except Exception as e:
                logger.error(f"Error processing manual funding for {position.position_id}: {e}")
        
        return payments
    
    def get_position_funding(self, position_id: str) -> List[FundingPayment]:
        """Get all funding payments for a specific position."""
        return [p for p in self._payments if p.position_id == position_id]
    
    def get_symbol_funding(self, symbol: str) -> List[FundingPayment]:
        """Get all funding payments for a specific symbol."""
        return [p for p in self._payments if p.symbol == symbol]
    
    def get_total_funding(self) -> Decimal:
        """Get net total funding (received - paid)."""
        return self._stats.net_funding
    
    def clear_history(self):
        """Clear funding payment history and reset stats."""
        with self._lock:
            self._payments.clear()
            self._last_funding_time.clear()
            self._stats = FundingStats()
    
    def to_state(self) -> Dict:
        """Serialize state for persistence."""
        return {
            "payments": [p.to_dict() for p in self._payments],
            "last_funding_time": {
                k: v.isoformat() for k, v in self._last_funding_time.items()
            },
            "stats": {
                "total_paid": str(self._stats.total_paid),
                "total_received": str(self._stats.total_received),
                "net_funding": str(self._stats.net_funding),
                "payment_count": self._stats.payment_count,
            },
        }
    
    def from_state(self, state: Dict):
        """Restore state from persistence."""
        self._payments = [
            FundingPayment.from_dict(p) for p in state.get("payments", [])
        ]
        self._last_funding_time = {
            k: datetime.fromisoformat(v) 
            for k, v in state.get("last_funding_time", {}).items()
        }
        
        stats_data = state.get("stats", {})
        self._stats = FundingStats(
            total_paid=Decimal(stats_data.get("total_paid", "0")),
            total_received=Decimal(stats_data.get("total_received", "0")),
            net_funding=Decimal(stats_data.get("net_funding", "0")),
            payment_count=stats_data.get("payment_count", 0),
        )
