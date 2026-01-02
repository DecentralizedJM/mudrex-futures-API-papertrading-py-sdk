"""
Trading Bot Example
===================

A simple trading bot that demonstrates:
- Market monitoring using SYMBOLS directly
- Position management
- Risk management with SL/TP
- Error handling

⚠️ WARNING: This is for educational purposes only!
Do NOT use in production without proper testing and risk management.
"""

import os
import time
import logging
from decimal import Decimal
from typing import Optional

from mudrex import MudrexClient
from mudrex.exceptions import MudrexAPIError, MudrexRateLimitError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class SimpleTradingBot:
    """
    A simple trading bot example.
    
    This bot:
    1. Monitors a single asset using SYMBOL (e.g., "BTCUSDT", "XRPUSDT")
    2. Opens positions based on simple logic
    3. Manages risk with stop-loss and take-profit
    4. Closes positions when targets are hit
    
    Example usage:
        bot = SimpleTradingBot(
            api_secret="your-secret",
            symbol="XRPUSDT",  # Trade any symbol!
            leverage="5",
            position_size="100",
        )
        bot.run()
    """
    
    def __init__(
        self,
        api_secret: str,
        symbol: str = "BTCUSDT",  # Use symbol directly!
        leverage: str = "5",
        position_size: str = "0.001",
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 4.0,
    ):
        self.client = MudrexClient(api_secret=api_secret)
        self.symbol = symbol  # Trading symbol like "BTCUSDT", "XRPUSDT"
        self.leverage = leverage
        self.position_size = position_size
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        self._running = False
    
    def setup(self) -> None:
        """Set up the bot before trading."""
        logger.info(f"Setting up bot for {self.symbol}...")
        
        # Check balances
        futures_balance = self.client.wallet.get_futures_balance()
        logger.info(f"Futures balance: ${futures_balance.balance}")
        
        if Decimal(futures_balance.balance) < 10:
            logger.warning("Low balance! Consider transferring more funds.")
        
        # Set leverage using SYMBOL directly
        self.client.leverage.set(
            symbol=self.symbol,  # Just pass the symbol!
            leverage=self.leverage,
            margin_type="ISOLATED"
        )
        logger.info(f"Leverage set to {self.leverage}x")
        
        # Get asset details using SYMBOL
        asset_info = self.client.assets.get(self.symbol)
        logger.info(f"Trading {asset_info.symbol}")
        logger.info(f"  Min qty: {asset_info.min_quantity}")
        logger.info(f"  Max leverage: {asset_info.max_leverage}x")
    
    def get_current_position(self) -> Optional[dict]:
        """Get current position for the symbol, if any."""
        positions = self.client.positions.list_open()
        for pos in positions:
            if pos.symbol == self.symbol:
                return pos
        return None
    
    def calculate_sl_tp(self, entry_price: float, side: str) -> tuple:
        """Calculate stop-loss and take-profit prices."""
        if side == "LONG":
            stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
            take_profit = entry_price * (1 + self.take_profit_pct / 100)
        else:  # SHORT
            stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
            take_profit = entry_price * (1 - self.take_profit_pct / 100)
        
        return str(round(stop_loss, 4)), str(round(take_profit, 4))
    
    def open_position(self, side: str, entry_price: float) -> None:
        """Open a new position using SYMBOL."""
        stop_loss, take_profit = self.calculate_sl_tp(entry_price, side)
        
        logger.info(f"Opening {side} position on {self.symbol}...")
        logger.info(f"  Entry: ${entry_price}")
        logger.info(f"  Stop Loss: ${stop_loss}")
        logger.info(f"  Take Profit: ${take_profit}")
        
        try:
            # Use symbol parameter - SDK handles is_symbol automatically!
            order = self.client.orders.create_market_order(
                symbol=self.symbol,  # Just the symbol!
                side=side,
                quantity=self.position_size,
                leverage=self.leverage,
                stoploss_price=stop_loss,
                takeprofit_price=take_profit,
            )
            logger.info(f"Order placed: {order.order_id}")
        except MudrexAPIError as e:
            logger.error(f"Failed to open position: {e}")
    
    def check_and_close_position(self, position) -> bool:
        """Check if position should be closed based on PnL."""
        pnl_pct = position.pnl_percentage
        
        # Log position status
        logger.info(f"Position: {position.side.value} {position.quantity} {self.symbol}")
        logger.info(f"  PnL: ${position.unrealized_pnl} ({pnl_pct:.2f}%)")
        
        # Auto-close logic (SL/TP should handle this, but as backup)
        if pnl_pct <= -self.stop_loss_pct:
            logger.warning(f"Stop-loss triggered! Closing position...")
            self.client.positions.close(position.position_id)
            return True
        
        if pnl_pct >= self.take_profit_pct:
            logger.info(f"Take-profit triggered! Closing position...")
            self.client.positions.close(position.position_id)
            return True
        
        return False
    
    def run_once(self) -> None:
        """Run one iteration of the bot logic."""
        try:
            # Check for existing position
            position = self.get_current_position()
            
            if position:
                # Monitor existing position
                self.check_and_close_position(position)
            else:
                # No position - could implement entry logic here
                logger.info(f"No open position on {self.symbol}. Waiting for entry signal...")
                
                # Example: Simple random entry (DO NOT USE IN PRODUCTION)
                # This is just for demonstration!
                # import random
                # if random.random() > 0.9:
                #     side = "LONG" if random.random() > 0.5 else "SHORT"
                #     self.open_position(side, 2.50)  # Example XRP price
        
        except MudrexRateLimitError:
            logger.warning("Rate limited, waiting...")
            time.sleep(5)
        except MudrexAPIError as e:
            logger.error(f"API error: {e}")
    
    def run(self, interval: int = 10) -> None:
        """
        Run the bot continuously.
        
        Args:
            interval: Seconds between checks
        """
        logger.info(f"Starting bot for {self.symbol}...")
        self._running = True
        
        self.setup()
        
        while self._running:
            try:
                self.run_once()
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Stopping bot...")
                self._running = False
        
        logger.info("Bot stopped.")
    
    def stop(self) -> None:
        """Stop the bot."""
        self._running = False


def main():
    # Get API key from environment
    api_secret = os.environ.get("MUDREX_API_SECRET")
    
    if not api_secret:
        print("Please set MUDREX_API_SECRET environment variable")
        print("Example: export MUDREX_API_SECRET='your-secret-here'")
        return
    
    # Create and run bot - works with ANY symbol!
    # Examples: "BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", etc.
    bot = SimpleTradingBot(
        api_secret=api_secret,
        symbol="BTCUSDT",      # Just use the symbol!
        leverage="5",
        position_size="0.001",
        stop_loss_pct=2.0,
        take_profit_pct=4.0,
    )
    
    # Run once for demo (use bot.run() for continuous)
    bot.setup()
    bot.run_once()
    
    # Example with XRP:
    # xrp_bot = SimpleTradingBot(
    #     api_secret=api_secret,
    #     symbol="XRPUSDT",     # Trade XRP!
    #     leverage="5",
    #     position_size="100",   # 100 XRP
    #     stop_loss_pct=2.0,
    #     take_profit_pct=4.0,
    # )
    # xrp_bot.run()


if __name__ == "__main__":
    main()
