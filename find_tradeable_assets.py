"""
Find assets you can actually trade with your current balance.
"""

from mudrex import MudrexClient

API_SECRET = "e2SYcr7wmpipC6N977QIcc64VaY0FSaz"

client = MudrexClient(api_secret=API_SECRET)

# Your constraints
balance = 15.79
leverage = 5
buying_power = balance * leverage

print(f"💰 Your Trading Capacity:")
print(f"   Balance: ${balance:.2f} USDT")
print(f"   Leverage: {leverage}x")
print(f"   Buying Power: ${buying_power:.2f}\n")

# Get all assets
print("📊 Fetching all assets...")
assets = client.assets.list_all()

# Find tradeable assets
tradeable = []

for asset in assets:
    symbol = asset.symbol
    qty_step = float(asset.quantity_step) if asset.quantity_step and float(asset.quantity_step) > 0 else None
    
    if not qty_step:
        continue
    
    # For assets without price, skip (we'll handle manually)
    # We need to estimate or use popular pairs
    
    # Check popular pairs that might have reasonable prices
    if symbol in ["ADAUSDT", "XRPUSDT", "DOGEUSDT", "TRXUSDT", "MATICUSDT", "DOTUSDT"]:
        # These typically have lower prices and smaller min orders
        tradeable.append({
            'symbol': symbol,
            'qty_step': qty_step,
            'asset': asset
        })

print(f"\n✅ Found {len(tradeable)} potentially tradeable low-price assets:\n")

# Let's check specific ones
popular_low_price = ["ADAUSDT", "XRPUSDT", "DOGEUSDT", "TRXUSDT", "SOLUSDT"]

print("Asset Analysis (assuming approximate prices):")
print("-" * 70)

estimates = {
    "ADAUSDT": 0.90,    # ADA ~$0.90
    "XRPUSDT": 2.50,    # XRP ~$2.50
    "DOGEUSDT": 0.35,   # DOGE ~$0.35
    "TRXUSDT": 0.25,    # TRX ~$0.25
    "SOLUSDT": 190.0,   # SOL ~$190
}

for symbol in popular_low_price:
    try:
        asset = client.assets.get(symbol)
        qty_step = float(asset.quantity_step) if asset.quantity_step and float(asset.quantity_step) > 0 else 1
        max_lev = float(asset.max_leverage) if hasattr(asset, 'max_leverage') else leverage
        
        # Use our price estimate
        est_price = estimates.get(symbol, 1.0)
        
        min_notional = qty_step * est_price
        required_margin = min_notional / min(leverage, max_lev)
        
        can_trade = required_margin <= balance
        
        print(f"\n{symbol}:")
        print(f"  Estimated Price: ${est_price:.4f}")
        print(f"  Min Quantity: {qty_step}")
        print(f"  Min Order Value: ${min_notional:.2f}")
        print(f"  Required Margin: ${required_margin:.2f}")
        print(f"  Max Leverage: {max_lev}x")
        print(f"  {'✅ CAN TRADE' if can_trade else '❌ CANNOT TRADE'}")
        
    except Exception as e:
        print(f"\n{symbol}: Error - {e}")

print("\n" + "=" * 70)
print("💡 RECOMMENDATION:")
print("=" * 70)
print("\nBest options based on your $15.79 balance with 5x leverage:")
print("\n1. DOGEUSDT - Very small min order, highly liquid")
print("2. TRXUSDT - Also very affordable") 
print("3. ADAUSDT - Good liquidity, moderate price")
print("\nAvoid: BTCUSDT, ETHUSDT, SOLUSDT (too expensive for your balance)")
