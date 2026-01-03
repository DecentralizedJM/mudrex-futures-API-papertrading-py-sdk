"""
Execute DOT LONG Trade - Simplified (No SL/TP in initial order)

Will place order first, then manage SL/TP manually or via separate orders.
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
notional_value = 5.0
entry_price = 1.905
tp_price = 2.057
sl_price = 1.600

# Calculate quantity with proper step
raw_quantity = notional_value / entry_price
quantity_step = 0.1
quantity = round(raw_quantity / quantity_step) * quantity_step
quantity = round(quantity, 1)

margin_required = notional_value / leverage

print("\n" + "=" * 70)
print("  DOT LONG TRADE EXECUTION (SIMPLIFIED)")
print("=" * 70)

print(f"\n📊 Trade Setup:")
print(f"   Symbol: {symbol}")
print(f"   Leverage: {leverage}x")
print(f"   Quantity: {quantity} DOT")
print(f"   Margin: ${margin_required:.2f}")
print(f"\n📋 Note: SL/TP will need to be managed manually or via separate orders")
print(f"   Target TP: ${tp_price}")
print(f"   Target SL: ${sl_price}")

confirm = input(f"\n⚠️  Execute this trade? (yes/no): ")
if confirm.lower() != 'yes':
    print("❌ Cancelled")
    exit()

try:
    # Set leverage
    print(f"\n1️⃣ Setting leverage...")
    resp = requests.post(
        f"{BASE_URL}/futures/{symbol}/leverage?is_symbol",
        headers=headers,
        json={"leverage": leverage, "margin_type": "ISOLATED"}
    )
    print(f"✅ Leverage set to {leverage}x")
    
    # Place simple market order (no SL/TP)
    print(f"\n2️⃣ Placing MARKET BUY order...")
    order_body = {
        "leverage": leverage,
        "quantity": quantity,
        "order_price": 999999,
        "order_type": "LONG",
        "trigger_type": "MARKET",
        "reduce_only": False
    }
    
    print(json.dumps(order_body, indent=2))
    
    resp = requests.post(
        f"{BASE_URL}/futures/{symbol}/order?is_symbol",
        headers=headers,
        json=order_body
    )
    
    print(f"\nResponse status: {resp.status_code}")
    response_data = resp.json()
    print(json.dumps(response_data, indent=2))
    
    if resp.status_code in [200, 202]:
        print("\n✅ ✅ ✅ TRADE EXECUTED! ✅ ✅ ✅")
        order_data = response_data.get('data', {})
        print(f"\n   Order ID: {order_data.get('order_id')}")
        print(f"   Entry: ${order_data.get('price')}")
        print(f"   Quantity: {order_data.get('quantity')} DOT")
        print(f"\n⚠️  IMPORTANT: Set your SL/TP manually in Mudrex app:")
        print(f"   TP: ${tp_price}")
        print(f"   SL: ${sl_price}")
    else:
        print(f"\n❌ FAILED!")
        for error in response_data.get('errors', []):
            print(f"   {error.get('text')}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
