"""
Comprehensive Mudrex SDK Endpoint Testing Script

Tests all SDK endpoints and performs sample trading.
"""

from mudrex import MudrexClient
import sys
import time
from datetime import datetime

# API Credentials
API_SECRET = "e2SYcr7wmpipC6N977QIcc64VaY0FSaz"

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_success(message):
    """Print success message."""
    print(f"✅ {message}")

def print_error(message):
    """Print error message."""
    print(f"❌ {message}")

def print_info(message):
    """Print info message."""
    print(f"ℹ️  {message}")

def test_wallet_endpoints(client):
    """Test wallet-related endpoints."""
    print_section("1. WALLET ENDPOINTS")
    
    try:
        # Get spot balance
        print("\n📊 Getting Spot Balance...")
        balance = client.wallet.get_spot_balance()
        print_success(f"Spot Balance: ${balance.available:.2f} USDT")
        print_info(f"  Available: ${balance.available:.2f}")
        print_info(f"  In Orders: ${balance.in_orders:.2f}")
        
        # Get futures balance
        print("\n📊 Getting Futures Balance...")
        futures_balance = client.wallet.get_futures_balance()
        print_success(f"Futures Balance: ${futures_balance.available:.2f} USDT")
        print_info(f"  Available: ${futures_balance.available:.2f}")
        print_info(f"  In Orders: ${futures_balance.in_orders:.2f}")
        print_info(f"  Unrealized PnL: ${futures_balance.unrealized_pnl:.2f}")
        
        return True
    except Exception as e:
        print_error(f"Wallet endpoints failed: {e}")
        return False

def test_assets_endpoints(client):
    """Test assets-related endpoints."""
    print_section("2. ASSETS ENDPOINTS")
    
    try:
        # List all assets (using fixed pagination!)
        print("\n📊 Listing ALL Assets (with pagination fix)...")
        assets = client.assets.list_all()
        print_success(f"Successfully fetched {len(assets)} assets!")
        
        # Show first 10 assets
        print_info("First 10 assets:")
        for i, asset in enumerate(assets[:10], 1):
            print(f"  {i}. {asset.symbol} - ${asset.price if hasattr(asset, 'price') else 'N/A'}")
        
        # Test getting specific asset - ADAUSDT (the one that was failing!)
        print("\n📊 Getting ADAUSDT (Previously Failing Symbol)...")
        ada = client.assets.get("ADAUSDT")
        print_success(f"ADAUSDT Details:")
        print_info(f"  Symbol: {ada.symbol}")
        print_info(f"  Price: ${ada.price if hasattr(ada, 'price') else 'N/A'}")
        print_info(f"  Min Quantity: {ada.min_quantity if hasattr(ada, 'min_quantity') else 'N/A'}")
        print_info(f"  Max Leverage: {ada.max_leverage if hasattr(ada, 'max_leverage') else 'N/A'}x")
        
        # Search for BTC assets
        print("\n📊 Searching for BTC assets...")
        btc_assets = client.assets.search("BTC")
        print_success(f"Found {len(btc_assets)} BTC-related assets")
        for asset in btc_assets[:5]:
            print_info(f"  - {asset.symbol}")
        
        # Check if ADAUSDT exists
        print("\n📊 Checking if ADAUSDT exists...")
        exists = client.assets.exists("ADAUSDT")
        print_success(f"ADAUSDT exists: {exists}")
        
        return True, assets
    except Exception as e:
        print_error(f"Assets endpoints failed: {e}")
        import traceback
        traceback.print_exc()
        return False, []

def test_positions_endpoints(client):
    """Test positions-related endpoints."""
    print_section("3. POSITIONS ENDPOINTS")
    
    try:
        # List open positions
        print("\n📊 Listing Open Positions...")
        open_positions = client.positions.list_open()
        print_success(f"Open positions: {len(open_positions)}")
        
        if open_positions:
            for pos in open_positions:
                print_info(f"  {pos.symbol}: Qty {pos.quantity}, PnL ${pos.unrealized_pnl if hasattr(pos, 'unrealized_pnl') else 'N/A'}")
        else:
            print_info("  No open positions")
        
        # List closed positions
        print("\n📊 Listing Recent Closed Positions...")
        closed_positions = client.positions.list_closed(limit=5)
        print_success(f"Recent closed positions: {len(closed_positions)}")
        
        if closed_positions:
            for pos in closed_positions[:5]:
                print_info(f"  {pos.symbol}: PnL ${pos.realized_pnl if hasattr(pos, 'realized_pnl') else 'N/A'}")
        
        return True
    except Exception as e:
        print_error(f"Positions endpoints failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_orders_endpoints(client):
    """Test orders-related endpoints."""
    print_section("4. ORDERS ENDPOINTS")
    
    try:
        # List open orders
        print("\n📊 Listing Open Orders...")
        open_orders = client.orders.list_open()
        print_success(f"Open orders: {len(open_orders)}")
        
        if open_orders:
            for order in open_orders:
                print_info(f"  {order.symbol}: {order.side} {order.quantity} @ {order.price if hasattr(order, 'price') else 'Market'}")
        else:
            print_info("  No open orders")
        
        return True
    except Exception as e:
        print_error(f"Orders endpoints failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_leverage_endpoints(client):
    """Test leverage-related endpoints."""
    print_section("5. LEVERAGE ENDPOINTS")
    
    try:
        # Get leverage for BTCUSDT
        print("\n📊 Getting Leverage for BTCUSDT...")
        leverage_info = client.leverage.get("BTCUSDT")
        print_success(f"BTCUSDT Leverage:")
        print_info(f"  Current: {leverage_info.leverage if hasattr(leverage_info, 'leverage') else 'N/A'}x")
        print_info(f"  Margin Type: {leverage_info.margin_type if hasattr(leverage_info, 'margin_type') else 'N/A'}")
        
        return True
    except Exception as e:
        print_error(f"Leverage endpoints failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def perform_sample_trade(client, assets):
    """Perform a sample trade (CAREFUL - REAL MONEY!)."""
    print_section("6. SAMPLE TRADING (REAL MONEY - BE CAREFUL!)")
    
    print("\n⚠️  WARNING: This will place a REAL trade with REAL money!")
    print("⚠️  We'll use a very small quantity to minimize risk.")
    
    response = input("\nDo you want to proceed with a sample trade? (yes/no): ")
    if response.lower() != 'yes':
        print_info("Sample trading skipped by user.")
        return False
    
    try:
        # Choose a liquid asset with low price for minimal cost
        # Let's use a small ADAUSDT trade to verify the fix
        symbol = "ADAUSDT"
        
        # Get current price and details
        asset = client.assets.get(symbol)
        current_price = float(asset.price) if hasattr(asset, 'price') else None
        min_qty = float(asset.min_quantity) if hasattr(asset, 'min_quantity') else 1
        
        print_info(f"\nTrading Asset: {symbol}")
        print_info(f"Current Price: ${current_price}")
        print_info(f"Minimum Quantity: {min_qty}")
        
        # Use minimum quantity for safety
        quantity = str(min_qty)
        estimated_cost = current_price * min_qty if current_price else 0
        
        print_info(f"Estimated Cost: ~${estimated_cost:.2f}")
        
        final_confirm = input(f"\nConfirm trade: BUY {quantity} {symbol} (~${estimated_cost:.2f})? (yes/no): ")
        if final_confirm.lower() != 'yes':
            print_info("Trade cancelled by user.")
            return False
        
        # Set leverage to 1x for safety
        print("\n📊 Setting leverage to 1x (safest)...")
        client.leverage.set(symbol, leverage="1", margin_type="ISOLATED")
        print_success("Leverage set to 1x ISOLATED")
        
        # Place market order
        print(f"\n📊 Placing MARKET BUY order for {quantity} {symbol}...")
        order = client.orders.create_market_order(
            symbol=symbol,
            side="LONG",
            quantity=quantity,
            leverage="1"
        )
        
        print_success(f"Order placed successfully!")
        print_info(f"  Order ID: {order.order_id if hasattr(order, 'order_id') else 'N/A'}")
        print_info(f"  Symbol: {symbol}")
        print_info(f"  Side: LONG")
        print_info(f"  Quantity: {quantity}")
        
        # Wait a moment for order to execute
        print("\n⏳ Waiting for order execution...")
        time.sleep(3)
        
        # Check positions
        print("\n📊 Checking open positions...")
        positions = client.positions.list_open()
        ada_position = next((p for p in positions if p.symbol == symbol), None)
        
        if ada_position:
            print_success(f"Position opened successfully!")
            print_info(f"  Symbol: {ada_position.symbol}")
            print_info(f"  Quantity: {ada_position.quantity if hasattr(ada_position, 'quantity') else 'N/A'}")
            print_info(f"  Entry Price: ${ada_position.entry_price if hasattr(ada_position, 'entry_price') else 'N/A'}")
            print_info(f"  Unrealized PnL: ${ada_position.unrealized_pnl if hasattr(ada_position, 'unrealized_pnl') else 'N/A'}")
            
            # Ask if user wants to close position
            close = input("\nDo you want to close this position now? (yes/no): ")
            if close.lower() == 'yes':
                print("\n📊 Closing position...")
                close_order = client.orders.create_market_order(
                    symbol=symbol,
                    side="SHORT",
                    quantity=quantity,
                    leverage="1",
                    reduce_only=True
                )
                print_success("Close order placed!")
                time.sleep(2)
                
                # Check if position is closed
                positions_after = client.positions.list_open()
                ada_after = next((p for p in positions_after if p.symbol == symbol), None)
                
                if not ada_after:
                    print_success("Position closed successfully!")
                else:
                    print_info("Position still open (may need more time to settle)")
        else:
            print_info("Position not found (may still be settling)")
        
        return True
        
    except Exception as e:
        print_error(f"Sample trading failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("\n" + "=" * 70)
    print("  MUDREX SDK - COMPREHENSIVE ENDPOINT TESTING")
    print("=" * 70)
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize client
    print_section("INITIALIZATION")
    print("\n📊 Initializing Mudrex client...")
    
    try:
        client = MudrexClient(api_secret=API_SECRET)
        print_success("Client initialized successfully!")
    except Exception as e:
        print_error(f"Failed to initialize client: {e}")
        sys.exit(1)
    
    # Run tests
    results = {}
    
    results['wallet'] = test_wallet_endpoints(client)
    results['assets'], assets = test_assets_endpoints(client)
    results['positions'] = test_positions_endpoints(client)
    results['orders'] = test_orders_endpoints(client)
    results['leverage'] = test_leverage_endpoints(client)
    
    # Summary
    print_section("TEST SUMMARY")
    print()
    for test_name, result in results.items():
        if isinstance(result, bool):
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name.upper()}: {status}")
    
    # Ask about sample trading
    if results['assets']:
        perform_sample_trade(client, assets)
    
    print("\n" + "=" * 70)
    print("  TESTING COMPLETE")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
