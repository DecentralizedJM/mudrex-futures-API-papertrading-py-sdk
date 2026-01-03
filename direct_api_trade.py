"""
Direct Mudrex API Trading Script - Fixed Order Size

Now uses larger quantity to meet minimum order value requirement.
"""

import requests
import json
import time

API_SECRET = "e2SYcr7wmpipC6N977QIcc64VaY0FSaz"
BASE_URL = "https://trade.mudrex.com/fapi/v1"

headers = {
    "X-Authentication": API_SECRET,
    "Content-Type": "application/json"
}

def main():
    print("\n" + "=" * 70)
    print("  DIRECT API TRADING TEST - DOGEUSDT (FIXED)")
    print("=" * 70)
    
    symbol = "DOGEUSDT"
    quantity = 50.0  # Increased from 10 to meet minimum value (~$17.50 total)
    leverage = 5
    
    print(f"\n📊 Trade Parameters:")
    print(f"   Symbol: {symbol}")
    print(f"   Quantity: {quantity} DOGE")
    print(f"   Leverage: {leverage}x")
    print(f"   Estimated value: ~$17.50")
    print(f"   Required margin: ~$3.50")
    print(f"   Your balance: $15.79 ✅")
    
    confirm = input(f"\nConfirm trade? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    try:
        # Step 1: Set leverage
        print("\n1️⃣ Setting leverage...")
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
        
        # Step 2: Place market order
        print("\n2️⃣ Placing MARKET BUY order...")
        order_body = {
            "leverage": leverage,
            "quantity": quantity,
            "order_price": 999999,  # High price for market buy
            "order_type": "LONG",
            "trigger_type": "MARKET",
            "reduce_only": False
        }
        
        print(f"\nRequest:")
        print(json.dumps(order_body, indent=2))
        
        resp = requests.post(
            f"{BASE_URL}/futures/{symbol}/order?is_symbol",
            headers=headers,
            json=order_body
        )
        
        print(f"\nResponse status: {resp.status_code}")
        response_data = resp.json()
        print(f"Response:")
        print(json.dumps(response_data, indent=2))
        
        if resp.status_code in [200, 202]:  # 202 = Accepted (async processing)
            print("\n✅ ✅ ✅ ORDER PLACED SUCCESSFULLY! ✅ ✅ ✅")
            print(f"   Order ID: {response_data.get('data', {}).get('order_id', 'N/A')}")
            print(f"   Status: {response_data.get('data', {}).get('status', 'N/A')}")

            
            # Wait for execution
            print("\n3️⃣ Waiting for execution...")
            time.sleep(3)
            
            # Check positions
            print("\n4️⃣ Checking position...")
            pos_resp = requests.get(
                f"{BASE_URL}/futures/positions",
                headers=headers
            )
            
            if pos_resp.status_code == 200:
                positions = pos_resp.json().get('data', [])
                doge_pos = next((p for p in positions if p.get('symbol') == symbol), None)
                
                if doge_pos:
                    print(f"\n✅ Position found!")
                    print(json.dumps(doge_pos, indent=2))
                    
                    pnl = doge_pos.get('unrealized_pnl', 0)
                    print(f"\n💰 Unrealized P&L: ${pnl}")
                    
                    # Ask about closing
                    close = input("\nClose position now? (yes/no): ")
                    if close.lower() == 'yes':
                        print("\n5️⃣ Closing position...")
                        close_body = {
                            "leverage": leverage,
                            "quantity": quantity,
                            "order_price": 1,  # Low price for market sell
                            "order_type": "SHORT",
                            "trigger_type": "MARKET",
                            "reduce_only": True
                        }
                        
                        close_resp = requests.post(
                            f"{BASE_URL}/futures/{symbol}/order?is_symbol",
                            headers=headers,
                            json=close_body
                        )
                        
                        if close_resp.status_code == 200:
                            print("✅ Position closed!")
                            print(json.dumps(close_resp.json(), indent=2))
                            
                            # Check final PnL
                            time.sleep(2)
                            balance_resp = requests.get(
                                f"{BASE_URL}/futures/funds",
                                headers=headers
                            )
                            if balance_resp.status_code == 200:
                                balance = balance_resp.json().get('data', {})
                                print(f"\n💰 Final Balance: ${balance.get('balance', 'N/A')} USDT")
                        else:
                            print(f"⚠️  Close failed: {close_resp.text}")
                else:
                    print("⚠️  Position not found yet (may still be settling)")
        else:
            print(f"\n❌ ORDER FAILED!")
            if 'errors' in response_data:
                for error in response_data['errors']:
                    print(f"   Error: {error.get('text', 'Unknown error')}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("  COMPLETE")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
