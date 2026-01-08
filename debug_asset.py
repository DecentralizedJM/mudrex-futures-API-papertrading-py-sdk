
from mudrex import MudrexClient
import json
import os

# Use a dummy secret since we only need public asset info
API_SECRET = "dummy_secret"

def main():
    client = MudrexClient(api_secret=API_SECRET)
    
    symbol = "WLFIUSDT"
    print(f"Fetching asset info for {symbol}...")
    
    try:
        # Access the private method to get raw response
        response = client.assets._get(f"/futures/assets/{symbol}", use_symbol=True)
        print("\nRaw Asset Response:")
        print(json.dumps(response, indent=2))
        
        # Also list all assets to see if it's different there
        print("\nFetching all assets sample...")
        all_assets = client.assets._get("/futures/assets")
        if isinstance(all_assets, dict) and 'data' in all_assets:
            items = all_assets['data']
            if items:
                print("\nSample Asset from list:")
                print(json.dumps(items[0], indent=2))
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
