"""
Execute DOT LONG Trade Signal

TRADE DETAILS:
- Pair: DOT/USDT
- Side: LONG
- Leverage: 25x
- Notional Value: $5
- Entry: $1.905
- TP1: $2.057
- SL: $1.600
"""

import requests
import json

API_SECRET = "e2SYcr7wmpipC6N977QIcc64VaY0FSaz"
BASE_URL = "https://trade.mudrex.com/fapi/v1"

headers = {
    "X-Authentication": API_SECRET,
    "Content-Type": "application/json"
}

# Trade Parameters
symbol = "DOTUSDT"
leverage = 25
notional_value = 5.0  # $5
entry_price = 1.905
tp_price = 2.057
sl_price = 1.600

# Calculate quantity: $5 / $1.905 = ~2.625 DOT
# DOT quantity_step is 0.1, so we need to round to nearest 0.1
raw_quantity = notional_value / entry_price
quantity_step = 0.1  # DOT's quantity step
quantity = round(raw_quantity / quantity_step) * quantity_step
quantity = round(quantity, 1)  # Round to 1 decimal for 0.1 step

margin_required = notional_value / leverage

print("\n" + "=" * 70)
print("  DOT LONG TRADE EXECUTION")
print("=" * 70)

print(f"\n📊 Trade Setup:")
print(f"   Symbol: {symbol}")
print(f"   Side: LONG")
print(f"   Leverage: {leverage}x")
print(f"   Notional Value: ${notional_value}")
print(f"   Entry Price: ${entry_price}")
print(f"   Quantity: {quantity} DOT")
print(f"   Margin Required: ${margin_required:.2f}")
print(f"\n📈 Targets:")
print(f"   TP1: ${tp_price} (+{((tp_price/entry_price - 1)*100):.1f}%)")
print(f"   SL: ${sl_price} ({((sl_price/entry_price - 1)*100):.1f}%)")

potential_profit = (tp_price - entry_price) * quantity * leverage
potential_loss = (entry_price - sl_price) * quantity * leverage

print(f"\n💰 Risk/Reward:")
print(f"   Potential Profit: ${potential_profit:.2f}")
print(f"   Potential Loss: ${potential_loss:.2f}")
print(f"   R:R Ratio: {abs(potential_profit/potential_loss):.2f}:1")

confirm = input(f"\n⚠️  Execute this trade? (yes/no): ")
if confirm.lower() != 'yes':
    print("❌ Trade cancelled")
    exit()

try:
    # Step 1: Set leverage
    print(f"\n1️⃣ Setting leverage to {leverage}x...")
    leverage_body = {
        "leverage": leverage,
        "margin_type": "ISOLATED"
    }
    
    resp = requests.post(
        f"{BASE_URL}/futures/{symbol}/leverage?is_symbol",
        headers=headers,
        json=leverage_body
    )
    
    if resp.status_code == 200:
        print(f"✅ Leverage set to {leverage}x ISOLATED")
    else:
        print(f"⚠️  Leverage response {resp.status_code}: {resp.text}")
    
    # Step 2: Place market order with SL/TP
    print(f"\n2️⃣ Placing MARKET BUY order with SL/TP...")
    order_body = {
        "leverage": leverage,
        "quantity": quantity,
        "order_price": 999999,  # High price for market buy
        "order_type": "LONG",
        "trigger_type": "MARKET",
        "reduce_only": False,
        "is_stoploss": True,
        "stoploss_price": sl_price,
        "is_takeprofit": True,
        "takeprofit_price": tp_price
    }
    
    print(f"\n📤 Sending order:")
    print(json.dumps(order_body, indent=2))
    
    resp = requests.post(
        f"{BASE_URL}/futures/{symbol}/order?is_symbol",
        headers=headers,
        json=order_body
    )
    
    print(f"\n📥 Response status: {resp.status_code}")
    response_data = resp.json()
    print(json.dumps(response_data, indent=2))
    
    if resp.status_code in [200, 202]:
        print("\n✅ ✅ ✅ TRADE EXECUTED SUCCESSFULLY! ✅ ✅ ✅")
        order_data = response_data.get('data', {})
        print(f"\n📋 Order Details:")
        print(f"   Order ID: {order_data.get('order_id', 'N/A')}")
        print(f"   Status: {order_data.get('status', 'N/A')}")
        print(f"   Entry Price: ${order_data.get('price', 'N/A')}")
        print(f"   Quantity: {order_data.get('quantity', 'N/A')} DOT")
        print(f"\n🎯 Your position is now active with:")
        print(f"   ✅ Stop Loss at ${sl_price}")
        print(f"   ✅ Take Profit at ${tp_price}")
    else:
        print(f"\n❌ TRADE FAILED!")
        if 'errors' in response_data:
            for error in response_data['errors']:
                print(f"   Error: {error.get('text', 'Unknown error')}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("  TRADE EXECUTION COMPLETE")
print("=" * 70 + "\n")
