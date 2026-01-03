"""
Simple Manual Trading Script for Mudrex SDK

This script allows you to manually trade with better debugging.
"""

from mudrex import MudrexClient
import json

API_SECRET = "e2SYcr7wmpipC6N977QIcc64VaY0FSaz"

def main():
    print("=" * 70)
    print("  MUDREX MANUAL TRADING SCRIPT")
    print("=" * 70)
    
    # Initialize client
    client = MudrexClient(api_secret=API_SECRET)
    print("✅ Client initialized\n")
    
    # Get all assets
    print("📊 Fetching all assets...")
    assets = client.assets.list_all()
    print(f"✅ Found {len(assets)} assets\n")
    
    # Show first asset in detail to see data structure
    if assets:
        first_asset = assets[0]
        print(f"Sample asset data for {first_asset.symbol}:")
        print(f"  Raw data: {first_asset.__dict__}\n")
    
    # Let's get BTCUSDT which should have data
    print("📊 Getting BTCUSDT details...")
    try:
        btc = client.assets.get("BTCUSDT")
        print(f"BTCUSDT data:")
        print(f"  Symbol: {btc.symbol}")
        print(f"  Raw data: {btc.__dict__}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")
    
    # Check wallet balance
    print("📊 Checking futures balance...")
    try:
        balance = client.wallet.get_futures_balance()
        print(f"Futures Balance:")
        print(f"  Raw data: {balance.__dict__}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")
    
    # List some popular trading pairs with data
    print("📊 Popular trading pairs:")
    popular_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]
    
    for symbol in popular_symbols:
        try:
            asset = client.assets.get(symbol)
            # Access raw dict to see all available fields
            data = asset.__dict__
            print(f"\n{symbol}:")
            print(f"  ID: {data.get('id', 'N/A')}")
            print(f"  Symbol: {data.get('symbol', 'N/A')}")
            
            # Try different field names for price
            price_fields = ['price', 'current_price', 'last_price', 'mark_price']
            for field in price_fields:
                if field in data and data[field]:
                    print(f"  Price ({field}): ${data[field]}")
                    break
            
            # Try different field names for min quantity
            qty_fields = ['min_quantity', 'minimum_quantity', 'min_qty', 'step_size']
            for field in qty_fields:
                if field in data and data[field]:
                    print(f"  Min Qty ({field}): {data[field]}")
                    break
            
            if 'max_leverage' in data:
                print(f"  Max Leverage: {data['max_leverage']}x")
                
        except Exception as e:
            print(f"\n{symbol}: ❌ Error - {e}")
    
    print("\n" + "=" * 70)
    print("  READY FOR MANUAL TRADING")
    print("=" * 70)
    print("""
To place a trade manually, use:

from mudrex import MudrexClient
client = MudrexClient(api_secret="YOUR_SECRET")

# Set leverage first
client.leverage.set("BTCUSDT", leverage="10", margin_type="ISOLATED")

# Place market order
order = client.orders.create_market_order(
    symbol="BTCUSDT",
    side="LONG",  # or "SHORT"
    quantity="0.001",  # Adjust based on min_quantity
    leverage="10"
)

# Check positions
positions = client.positions.list_open()
for p in positions:
    print(f"{p.symbol}: {p.__dict__}")

# Close position
close_order = client.orders.create_market_order(
    symbol="BTCUSDT",
    side="SHORT",  # opposite of entry
    quantity="0.001",
    leverage="10",
    reduce_only=True
)
    """)

if __name__ == "__main__":
    main()
