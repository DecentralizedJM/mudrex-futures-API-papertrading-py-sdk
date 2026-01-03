"""
Debug the exact request body being sent to Mudrex API
"""

from mudrex import MudrexClient
from mudrex.models import OrderRequest, OrderType, TriggerType
import json

API_SECRET = "e2SYcr7wmpipC6N977QIcc64VaY0FSaz"

client = MudrexClient(api_secret=API_SECRET)

symbol = "BTCUSDT"
quantity = "0.001"
leverage = "5"

# Build request exactly as SDK does now
request = OrderRequest(
    quantity=quantity,
    order_type=OrderType("LONG"),
    trigger_type=TriggerType.MARKET,
    leverage=leverage,
    order_price="999999999",  # The placeholder we added
    reduce_only=False,
)

print("📊 Request Dict:")
print(json.dumps(request.to_dict(), indent=2))

print("\n📊 Expected request based on API docs:")
expected = {
    "leverage": 50,
    "quantity": 0.01,
    "order_price": 12445627,
    "order_type": "LONG",
    "trigger_type": "MARKET",
    "is_takeprofit": False,
    "is_stoploss": False,
    "reduce_only": False
}
print(json.dumps(expected, indent=2))

print("\n📊 Differences:")
actual_dict = request.to_dict()
print(f"leverage type: {type(actual_dict.get('leverage'))} vs expected: {type(expected['leverage'])}")
print(f"quantity type: {type(actual_dict.get('quantity'))} vs expected: {type(expected['quantity'])}")
print(f"order_price type: {type(actual_dict.get('order_price'))} vs expected: {type(expected['order_price'])}")
