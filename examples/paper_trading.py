#!/usr/bin/env python3
"""
Paper Trading Example
=====================

Demonstrates how to use Mudrex SDK in paper trading mode.
No real orders are placed - uses simulated funds with real market prices.

Features demonstrated:
- Initializing paper trading mode
- Placing market and limit orders
- Setting stop-loss and take-profit
- Checking positions and PnL
- Viewing trade history
- State persistence

Usage:
    python examples/paper_trading.py

Note:
    You still need a valid API secret for fetching real-time prices.
"""

import os
import sys
import time
import logging

# Add parent directory to path for development
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mudrex import MudrexClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress debug logs from urllib3
logging.getLogger('urllib3').setLevel(logging.WARNING)


def main():
    """Main paper trading demo."""
    print("=" * 70)
    print("  MUDREX PAPER TRADING DEMO")
    print("=" * 70)
    
    # Get API secret from environment or use placeholder for demo
    api_secret = os.environ.get("MUDREX_API_SECRET")
    
    if not api_secret:
        print("\n⚠️  No MUDREX_API_SECRET environment variable found.")
        print("   Set it with: export MUDREX_API_SECRET='your-api-secret'")
        print("\n   Using mock prices for demo (offline mode)...")
        demo_with_mock_prices()
        return
    
    # Initialize client in paper mode
    print("\n🎮 Initializing paper trading client...")
    
    client = MudrexClient(
        api_secret=api_secret,
        mode="paper",
        paper_balance="10000",  # Start with $10,000
        paper_sltp_monitor=True,  # Enable SL/TP monitoring
        paper_sltp_interval=5,  # Check every 5 seconds
    )
    
    print(f"   {client}")
    print(f"   Starting balance: $10,000")
    
    try:
        demo_trading_workflow(client)
    finally:
        # Cleanup
        client.close()
        print("\n✅ Paper trading session ended")


def demo_trading_workflow(client: MudrexClient):
    """Demonstrate a complete trading workflow."""
    
    # =========================================================================
    # 1. Check initial balance
    # =========================================================================
    print("\n" + "=" * 50)
    print("1️⃣ CHECKING BALANCE")
    print("=" * 50)
    
    balance = client.wallet.get_futures_balance()
    print(f"   Balance: ${balance.balance}")
    print(f"   Available: ${balance.available}")
    print(f"   Locked: ${balance.locked}")
    
    # =========================================================================
    # 2. Get asset info and current price
    # =========================================================================
    print("\n" + "=" * 50)
    print("2️⃣ FETCHING ASSET INFO")
    print("=" * 50)
    
    symbol = "BTCUSDT"
    
    try:
        asset = client.assets.get(symbol)
        print(f"   Symbol: {asset.symbol}")
        print(f"   Price: ${asset.price}")
        print(f"   Min Quantity: {asset.min_quantity}")
        print(f"   Max Leverage: {asset.max_leverage}x")
    except Exception as e:
        print(f"   ⚠️ Could not fetch asset: {e}")
        return
    
    # =========================================================================
    # 3. Set leverage
    # =========================================================================
    print("\n" + "=" * 50)
    print("3️⃣ SETTING LEVERAGE")
    print("=" * 50)
    
    leverage = "10"
    client.leverage.set(symbol, leverage=leverage, margin_type="ISOLATED")
    print(f"   Set {symbol} leverage to {leverage}x")
    
    # =========================================================================
    # 4. Place a market order with SL/TP
    # =========================================================================
    print("\n" + "=" * 50)
    print("4️⃣ PLACING MARKET ORDER")
    print("=" * 50)
    
    # Calculate reasonable SL/TP based on current price
    current_price = float(asset.price)
    quantity = "0.01"
    
    # For a LONG: SL below entry, TP above entry
    stoploss_price = str(round(current_price * 0.97, 2))  # -3%
    takeprofit_price = str(round(current_price * 1.05, 2))  # +5%
    
    print(f"   Symbol: {symbol}")
    print(f"   Side: LONG")
    print(f"   Quantity: {quantity}")
    print(f"   Leverage: {leverage}x")
    print(f"   Stop Loss: ${stoploss_price} (-3%)")
    print(f"   Take Profit: ${takeprofit_price} (+5%)")
    
    order = client.orders.create_market_order(
        symbol=symbol,
        side="LONG",
        quantity=quantity,
        leverage=leverage,
        stoploss_price=stoploss_price,
        takeprofit_price=takeprofit_price,
    )
    
    print(f"\n   ✅ Order placed!")
    print(f"   Order ID: {order.order_id}")
    print(f"   Status: {order.status}")
    print(f"   Filled at: ${order.price}")
    
    # =========================================================================
    # 5. Check positions
    # =========================================================================
    print("\n" + "=" * 50)
    print("5️⃣ CHECKING POSITIONS")
    print("=" * 50)
    
    positions = client.positions.list_open()
    
    if positions:
        for pos in positions:
            print(f"\n   📊 {pos.symbol} {pos.side.value}")
            print(f"      Quantity: {pos.quantity}")
            print(f"      Entry: ${pos.entry_price}")
            print(f"      Mark Price: ${pos.mark_price}")
            print(f"      Leverage: {pos.leverage}x")
            print(f"      Margin: ${pos.margin}")
            print(f"      Unrealized PnL: ${pos.unrealized_pnl}")
            if pos.stoploss_price:
                print(f"      Stop Loss: ${pos.stoploss_price}")
            if pos.takeprofit_price:
                print(f"      Take Profit: ${pos.takeprofit_price}")
    else:
        print("   No open positions")
    
    # =========================================================================
    # 6. Check updated balance
    # =========================================================================
    print("\n" + "=" * 50)
    print("6️⃣ UPDATED BALANCE")
    print("=" * 50)
    
    balance = client.wallet.get_futures_balance()
    print(f"   Balance: ${balance.balance}")
    print(f"   Available: ${balance.available}")
    print(f"   Locked (margin): ${balance.locked}")
    print(f"   Unrealized PnL: ${balance.unrealized_pnl}")
    
    # =========================================================================
    # 7. Wait a moment and check PnL changes
    # =========================================================================
    print("\n" + "=" * 50)
    print("7️⃣ MONITORING PnL (5 seconds)")
    print("=" * 50)
    
    for i in range(5):
        time.sleep(1)
        positions = client.positions.list_open()
        if positions:
            pos = positions[0]
            print(f"   [{i+1}s] PnL: ${pos.unrealized_pnl}")
    
    # =========================================================================
    # 8. Close position
    # =========================================================================
    print("\n" + "=" * 50)
    print("8️⃣ CLOSING POSITION")
    print("=" * 50)
    
    if positions:
        pos = positions[0]
        print(f"   Closing position {pos.position_id}...")
        
        success = client.positions.close(pos.position_id)
        
        if success:
            print("   ✅ Position closed!")
    
    # =========================================================================
    # 9. Final balance and statistics
    # =========================================================================
    print("\n" + "=" * 50)
    print("9️⃣ FINAL STATISTICS")
    print("=" * 50)
    
    balance = client.wallet.get_futures_balance()
    print(f"   Final Balance: ${balance.balance}")
    print(f"   Available: ${balance.available}")
    
    stats = client.get_paper_statistics()
    print(f"\n   📈 Trading Statistics:")
    print(f"      Total PnL: ${stats['total_pnl']}")
    print(f"      Realized PnL: ${stats['realized_pnl']}")
    print(f"      Total Fees: ${stats['total_fees_paid']}")
    print(f"      Total Trades: {stats['total_trades']}")
    print(f"      Win Rate: {stats['win_rate']}")
    
    # =========================================================================
    # 10. Trade history
    # =========================================================================
    print("\n" + "=" * 50)
    print("🔟 TRADE HISTORY")
    print("=" * 50)
    
    trades = client.get_paper_trade_history(limit=10)
    
    for trade in trades:
        print(f"\n   {trade['action']} {trade['symbol']}")
        print(f"      Quantity: {trade['quantity']} @ ${trade['price']}")
        print(f"      Fee: ${trade['fee']}")
        if trade.get('pnl'):
            print(f"      PnL: ${trade['pnl']} ({trade['pnl_percent']}%)")


def demo_with_mock_prices():
    """Demo using mock prices (for offline testing)."""
    from decimal import Decimal
    from mudrex.paper import (
        PaperTradingEngine,
        MockPriceFeedService,
        SLTPMonitor,
    )
    
    print("\n🎮 Running with mock prices...")
    
    # Create mock price feed
    price_feed = MockPriceFeedService()
    
    # Create engine
    engine = PaperTradingEngine(
        initial_balance=Decimal("10000"),
        price_feed=price_feed,
    )
    
    print(f"   Initial balance: $10,000")
    print(f"   BTC mock price: ${price_feed.get_price('BTCUSDT')}")
    
    # Place an order
    print("\n📝 Placing LONG order...")
    order = engine.create_market_order(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.1"),
        leverage=10,
        stoploss_price=Decimal("95000"),
        takeprofit_price=Decimal("110000"),
    )
    
    print(f"   Order ID: {order.order_id}")
    print(f"   Filled at: ${order.filled_price}")
    
    # Check position
    print("\n📊 Position:")
    positions = engine.list_open_positions()
    for pos in positions:
        print(f"   {pos.symbol}: {pos.side} {pos.quantity}")
        print(f"   Entry: ${pos.entry_price}")
        print(f"   Margin: ${pos.margin}")
    
    # Simulate price movement
    print("\n📈 Simulating price increase to $105,000...")
    price_feed.set_price("BTCUSDT", Decimal("105000"))
    
    # Check updated PnL
    positions = engine.list_open_positions()
    for pos in positions:
        print(f"   Unrealized PnL: ${pos.unrealized_pnl}")
        print(f"   ROE: {pos.roe_percent:.2f}%")
    
    # Close position
    print("\n🔒 Closing position...")
    engine.close_position(positions[0].position_id)
    
    # Final stats
    print("\n📊 Final Statistics:")
    stats = engine.get_statistics()
    print(f"   Balance: ${stats['total_balance']}")
    print(f"   Realized PnL: ${stats['realized_pnl']}")
    print(f"   Fees Paid: ${stats['total_fees_paid']}")
    
    print("\n✅ Mock demo completed!")


if __name__ == "__main__":
    main()
