"""
Debug script to inspect the exact API request being made for order placement.
"""

from mudrex import MudrexClient
from mudrex.models import OrderRequest, OrderType, TriggerType
import json

API_SECRET = "e2SYcr7wmpipC6N977QIcc64VaY0FSaz"

def main():
    print("=" * 70)
    print("  DEBUGGING ORDER PLACEMENT API REQUEST")
    print("=" * 70)
    
    client = MudrexClient(api_secret=API_SECRET)
    print("\n✅ Client initialized\n")
    
    # Build the exact request that would be sent
    symbol = "BTCUSDT"
    quantity = "0.001"
    leverage = "5"
    side = OrderType("LONG")
    
    request = OrderRequest(
        quantity=quantity,
        order_type=side,
        trigger_type=TriggerType.MARKET,
        leverage=leverage,
        order_price=None,
        is_stoploss=False,
        stoploss_price=None,
        is_takeprofit=False,
        takeprofit_price=None,
        reduce_only=False,
    )
    
    print("📊 Order Request Object:")
    print(json.dumps(request.to_dict(), indent=2))
    
    print(f"\n📊 Endpoint that will be called:")
    print(f"   POST /futures/{symbol}/order?is_symbol")
    
    print(f"\n📊 Full URL:")
    print(f"   https://trade.mudrex.com/fapi/v1/futures/{symbol}/order?is_symbol")
    
    # Try to place the order with better error handling
    print("\n⚠️  Attempting to place order...")
    
    try:
        # Access the private method to see the raw response
        response = client.orders._post(
            f"/futures/{symbol}/order",
            request.to_dict(),
            use_symbol=True
        )
        print("\n✅ Success! Raw response:")
        print(json.dumps(response, indent=2))
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("\n� Let's check if the symbol needs to be looked up to asset_id first")
        
        # Try to get the asset to see its ID
        asset = client.assets.get(symbol)
        print(f"\n📊 {symbol} Asset Details:")
        print(f"   Asset ID: {asset.asset_id if hasattr(asset, 'asset_id') else 'N/A'}")
        print(f"   Symbol: {asset.symbol}")
        print(f"   Raw data: {asset.__dict__}")
        
        # Try with asset_id instead
        if hasattr(asset, 'asset_id') and asset.asset_id:
            print(f"\n📊 Trying with asset_id instead of symbol...")
            try:
                response = client.orders._post(
                    f"/futures/{asset.asset_id}/order",
                    request.to_dict(),
                    use_symbol=False  # Using asset_id
                )
                print("\n✅ SUCCESS with asset_id! Raw response:")
                print(json.dumps(response, indent=2))
            except Exception as e2:
                print(f"\n❌ Also failed with asset_id: {e2}")
                
                #  Try to understand what the API expects
                print("\n📊 Let's check the API documentation format...")
                print("   According to Mudrex docs:")
                print("   - Trade by symbol: POST /futures/{symbol}/order?is_symbol")
                print("   - Trade by asset_id: POST /futures/{asset_id}/order")

if __name__ == "__main__":
    main()
