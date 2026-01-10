"""
SL/TP Monitor
=============

Background task that monitors positions for stop-loss and take-profit triggers.
"""

import logging
import threading
import time
from decimal import Decimal
from typing import TYPE_CHECKING, Callable, Optional

from mudrex.paper.models import PaperPositionStatus, CloseReason

if TYPE_CHECKING:
    from mudrex.paper.engine import PaperTradingEngine

logger = logging.getLogger(__name__)


class SLTPMonitor:
    """
    Background task that monitors positions for stop-loss/take-profit triggers.
    
    Design:
    - Polling-based (no websocket complexity in V1)
    - Configurable interval (default: 5 seconds)
    - Uses last traded price from Mudrex API
    - Thread-safe
    
    Example:
        >>> from mudrex.paper import PaperTradingEngine, SLTPMonitor
        >>> 
        >>> engine = PaperTradingEngine(...)
        >>> monitor = SLTPMonitor(engine, interval=5)
        >>> 
        >>> # Start monitoring
        >>> monitor.start()
        >>> 
        >>> # ... trading happens ...
        >>> 
        >>> # Stop when done
        >>> monitor.stop()
    """
    
    def __init__(
        self,
        engine: "PaperTradingEngine",
        interval: int = 5,
        on_sl_triggered: Optional[Callable] = None,
        on_tp_triggered: Optional[Callable] = None,
        on_liquidation_warning: Optional[Callable] = None,
    ):
        """
        Initialize the SL/TP monitor.
        
        Args:
            engine: PaperTradingEngine instance to monitor
            interval: Check interval in seconds (default: 5)
            on_sl_triggered: Callback when stop-loss triggers
            on_tp_triggered: Callback when take-profit triggers
            on_liquidation_warning: Callback when position nears liquidation
        """
        self.engine = engine
        self.interval = interval
        self.on_sl_triggered = on_sl_triggered
        self.on_tp_triggered = on_tp_triggered
        self.on_liquidation_warning = on_liquidation_warning
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Statistics
        self.sl_triggered_count = 0
        self.tp_triggered_count = 0
        self.checks_performed = 0
    
    def start(self) -> None:
        """Start the background monitoring thread."""
        if self._running:
            logger.warning("SL/TP monitor already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
        logger.info(f"SL/TP monitor started (interval: {self.interval}s)")
    
    def stop(self) -> None:
        """Stop the background monitoring thread."""
        self._running = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.interval + 1)
        
        logger.info("SL/TP monitor stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                self.check_all_positions()
                self.engine.check_limit_orders()
            except Exception as e:
                logger.error(f"Error in SL/TP monitor: {e}")
            
            time.sleep(self.interval)
    
    def check_all_positions(self) -> None:
        """
        Check all open positions for SL/TP triggers.
        
        This is the main monitoring function that:
        1. Gets all open positions
        2. Fetches current price for each symbol
        3. Checks if SL or TP should trigger
        4. Executes position close if triggered
        """
        with self._lock:
            self.checks_performed += 1
            
            # Get all open positions
            open_positions = list(self.engine.positions.values())
            open_positions = [p for p in open_positions if p.status == PaperPositionStatus.OPEN]
            
            if not open_positions:
                return
            
            # Group by symbol to minimize API calls
            symbols = set(p.symbol for p in open_positions)
            prices = self.engine.price_feed.get_prices_batch(list(symbols))
            
            for position in open_positions:
                if position.symbol not in prices:
                    continue
                
                current_price = prices[position.symbol]
                
                # Update position PnL
                position.update_pnl(current_price)
                
                # Check triggers
                triggered = self._check_position_triggers(position, current_price)
                
                if not triggered:
                    # Check liquidation warning
                    self._check_liquidation_warning(position, current_price)
    
    def _check_position_triggers(
        self,
        position,
        current_price: Decimal
    ) -> bool:
        """
        Check if SL or TP should trigger for a position.
        
        Priority: TP is checked first (profit-taking is primary intent).
        
        Returns: True if a trigger fired
        """
        # Check Take Profit first (user's primary intent)
        if position.takeprofit_price:
            tp = Decimal(str(position.takeprofit_price))
            
            if position.side == "LONG" and current_price >= tp:
                self._trigger_takeprofit(position, current_price)
                return True
            elif position.side == "SHORT" and current_price <= tp:
                self._trigger_takeprofit(position, current_price)
                return True
        
        # Check Stop Loss
        if position.stoploss_price:
            sl = Decimal(str(position.stoploss_price))
            
            if position.side == "LONG" and current_price <= sl:
                self._trigger_stoploss(position, current_price)
                return True
            elif position.side == "SHORT" and current_price >= sl:
                self._trigger_stoploss(position, current_price)
                return True
        
        return False
    
    def _trigger_stoploss(self, position, price: Decimal) -> None:
        """Execute stop-loss close."""
        logger.info(
            f"🔴 STOP-LOSS TRIGGERED: {position.position_id} "
            f"{position.side} {position.symbol} @ {price}"
        )
        
        try:
            self.engine._close_position_internal(position, price, CloseReason.STOPLOSS)
            self.sl_triggered_count += 1
            
            if self.on_sl_triggered:
                self.on_sl_triggered(position, price)
                
        except Exception as e:
            logger.error(f"Failed to execute stop-loss for {position.position_id}: {e}")
    
    def _trigger_takeprofit(self, position, price: Decimal) -> None:
        """Execute take-profit close."""
        logger.info(
            f"🟢 TAKE-PROFIT TRIGGERED: {position.position_id} "
            f"{position.side} {position.symbol} @ {price}"
        )
        
        try:
            self.engine._close_position_internal(position, price, CloseReason.TAKEPROFIT)
            self.tp_triggered_count += 1
            
            if self.on_tp_triggered:
                self.on_tp_triggered(position, price)
                
        except Exception as e:
            logger.error(f"Failed to execute take-profit for {position.position_id}: {e}")
    
    def _check_liquidation_warning(self, position, current_price: Decimal) -> None:
        """Check if position is approaching liquidation (warning only)."""
        if not position.liquidation_price:
            position.liquidation_price = position.calculate_liquidation_price()
        
        if not position.liquidation_price:
            return
        
        liq_price = Decimal(str(position.liquidation_price))
        
        # Calculate distance to liquidation as percentage
        if position.side == "LONG":
            distance = (current_price - liq_price) / current_price * 100
            is_near = distance < 10  # Within 10% of liquidation
        else:
            distance = (liq_price - current_price) / current_price * 100
            is_near = distance < 10
        
        if is_near:
            logger.warning(
                f"⚠️ LIQUIDATION WARNING: {position.position_id} {position.symbol} "
                f"is {distance:.1f}% from liquidation (current: {current_price}, liq: {liq_price})"
            )
            
            if self.on_liquidation_warning:
                self.on_liquidation_warning(position, current_price, liq_price)
    
    def get_status(self) -> dict:
        """Get monitor status and statistics."""
        return {
            "running": self._running,
            "interval": self.interval,
            "checks_performed": self.checks_performed,
            "sl_triggered_count": self.sl_triggered_count,
            "tp_triggered_count": self.tp_triggered_count,
        }
    
    @property
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running


class ManualTriggerChecker:
    """
    Manual SL/TP checker for non-threaded usage.
    
    Use this if you prefer to control when checks happen
    (e.g., in a single-threaded bot or during backtesting).
    
    Example:
        >>> checker = ManualTriggerChecker(engine)
        >>> 
        >>> while True:
        ...     # Your trading logic
        ...     checker.check()
        ...     time.sleep(5)
    """
    
    def __init__(self, engine: "PaperTradingEngine"):
        self.engine = engine
        self._monitor = SLTPMonitor(engine, interval=0)
    
    def check(self) -> dict:
        """
        Perform a single check of all positions.
        
        Returns:
            Dictionary with check results
        """
        before_sl = self._monitor.sl_triggered_count
        before_tp = self._monitor.tp_triggered_count
        
        self._monitor.check_all_positions()
        self.engine.check_limit_orders()
        
        return {
            "sl_triggered": self._monitor.sl_triggered_count - before_sl,
            "tp_triggered": self._monitor.tp_triggered_count - before_tp,
        }
