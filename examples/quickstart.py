"""
Quickstart Example
==================

This example walks you through the basic trading workflow:
1. Check wallet balance
2. Discover ALL available assets (500+)
3. Transfer funds to futures
4. Set leverage
5. Place an order
6. Monitor position
7. Close position

Prerequisites:
- pip install git+https://github.com/DecentralizedJM/mudrex-trading-sdk.git
- Get your API key from Mudrex dashboard
"""

from mudrex import MudrexClient


def main():
    # =========================================================================
    # Step 1: Initialize the client
    # =========================================================================
    # Replace with your actual API secret from Mudrex dashboard
    API_SECRET = "your-api-secret-here"
    
    client = MudrexClient(api_secret=API_SECRET)
    print("✓ Connected to Mudrex API")
    
    
    # =========================================================================
    # Step 2: Check wallet balances
    # =========================================================================
    spot_balance = client.wallet.get_spot_balance()
    print(f"\n💰 Spot Wallet:")
    print(f"   Total: ${spot_balance.total}")
    print(f"   Available: ${spot_balance.available}")
    
    futures_balance = client.wallet.get_futures_balance()
    print(f"\n💰 Futures Wallet:")
    print(f"   Balance: ${futures_balance.balance}")
    print(f"   Available for transfer: ${futures_balance.available_transfer}")
    
    
    # =========================================================================
    # Step 3: Discover ALL tradable assets (500+ pairs!)
    # =========================================================================
    print("\n📊 Fetching ALL tradable assets...")
    assets = client.assets.list_all()  # Gets ALL assets, no pagination limits!
    print(f"   Found {len(assets)} tradable assets!")
    
    # Show first 10 as sample
    print("\n   Sample assets:")
    for asset in assets[:10]:
        print(f"   - {asset.symbol}: leverage {asset.min_leverage}x-{asset.max_leverage}x")
    
    print(f"\n   ... and {len(assets) - 10} more!")
    
    
    # =========================================================================
    # Step 4: Get specific asset details using SYMBOL (recommended)
    # =========================================================================
    # Just use the symbol directly - no need for asset IDs!
    btc = client.assets.get("BTCUSDT")
    print(f"\n📈 {btc.symbol} Details:")
    print(f"   Min quantity: {btc.min_quantity}")
    print(f"   Max leverage: {btc.max_leverage}x")
    print(f"   Maker fee: {btc.maker_fee}%")
    print(f"   Taker fee: {btc.taker_fee}%")
    
    # Works with ANY symbol!
    xrp = client.assets.get("XRPUSDT")
    print(f"\n📈 {xrp.symbol} Details:")
    print(f"   Min quantity: {xrp.min_quantity}")
    print(f"   Max leverage: {xrp.max_leverage}x")
    
    
    # =========================================================================
    # Step 5: Transfer funds to futures (if needed)
    # =========================================================================
    # Uncomment to transfer funds:
    # result = client.wallet.transfer_to_futures("100")
    # print(f"\n📤 Transferred ${result.amount} to futures wallet")
    
    
    # =========================================================================
    # Step 6: Set leverage using SYMBOL
    # =========================================================================
    leverage = client.leverage.set(
        symbol="BTCUSDT",  # Use symbol directly!
        leverage="5",
        margin_type="ISOLATED"
    )
    print(f"\n⚡ Set leverage to {leverage.leverage}x ({leverage.margin_type.value})")
    
    
    # =========================================================================
    # Step 7: Place a market order using SYMBOL
    # =========================================================================
    # CAUTION: This places a real order! Comment out for testing.
    """
    order = client.orders.create_market_order(
        symbol="BTCUSDT",  # Use symbol directly!
        side="LONG",
        quantity="0.001",
        leverage="5",
        stoploss_price="95000",
        takeprofit_price="110000"
    )
    print(f"\n✅ Order placed!")
    print(f"   Order ID: {order.order_id}")
    print(f"   Type: {order.order_type.value}")
    print(f"   Status: {order.status.value}")
    
    # Trade XRP example
    xrp_order = client.orders.create_market_order(
        symbol="XRPUSDT",  # Works with any symbol!
        side="LONG",
        quantity="100",
        leverage="5"
    )
    print(f"   XRP Order ID: {xrp_order.order_id}")
    """
    
    
    # =========================================================================
    # Step 8: Monitor positions
    # =========================================================================
    positions = client.positions.list_open()
    print(f"\n📊 Open Positions: {len(positions)}")
    
    for pos in positions:
        print(f"\n   {pos.symbol}:")
        print(f"   Side: {pos.side.value}")
        print(f"   Quantity: {pos.quantity}")
        print(f"   Entry: ${pos.entry_price}")
        print(f"   Current: ${pos.mark_price}")
        print(f"   PnL: ${pos.unrealized_pnl} ({pos.pnl_percentage:.2f}%)")
    
    
    # =========================================================================
    # Step 9: Close position (when ready)
    # =========================================================================
    # Uncomment to close:
    # if positions:
    #     client.positions.close(positions[0].position_id)
    #     print(f"\n✅ Closed position {positions[0].symbol}")
    
    
    print("\n✨ Done! Check out more examples in the examples/ folder.")
    print("\n💡 Tips:")
    print("   - Use symbols like 'BTCUSDT', 'XRPUSDT', 'ETHUSDT' directly")
    print("   - list_all() fetches ALL 500+ assets automatically")
    print("   - No need to worry about pagination or asset IDs!")


if __name__ == "__main__":
    main()
