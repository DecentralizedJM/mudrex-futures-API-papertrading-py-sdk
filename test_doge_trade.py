"""
Test trade with DOGEUSDT - affordable for your balance!
"""

from mudrex import MudrexClient
import time

API_SECRET = "e2SYcr7wmpipC6N977QIcc64VaY0FSaz"

def main():
    print("\n" + "=" * 70)
    print("  MUDREX SDK - DOGE TRADING TEST (Affordable!)")
    print("=" * 70)
    
    client = MudrexClient(api_secret=API_SECRET)
    print("\n✅ Client initialized")
    
    # Check balance
    balance = client.wallet.get_futures_balance()
    print(f"\n💰 Futures Balance: ${balance.balance} USDT")
    
    # Trade DOGE - much more affordable!
    symbol = "DOGEUSDT"
    quantity = "10"  # 10 DOGE (min is 1, costs ~$3.50 total)
    leverage = "5"
   
    print(f"\n📊 Trade Parameters:")
    print(f"   Symbol: {symbol}")
    print(f"   Quantity: {quantity} DOGE")
    print(f"   Leverage: {leverage}x")
    print(f"   Estimated cost: ~$3.50 total, ~$0.70 margin needed")
    print(f"   Your balance: ${balance.balance} ✅ Plenty!")
    
    confirm = input(f"\nConfirm: BUY {quantity} {symbol} with {leverage}x leverage? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("❌ Trade cancelled")
        return
    
    try:
        # Set leverage
        print(f"\n1️⃣ Setting leverage to {leverage}x ISOLATED...")
        client.leverage.set(symbol, leverage=leverage, margin_type="ISOLATED")
        print(f"✅ Leverage set")
        
        # Place market order
        print(f"\n2️⃣ Placing MARKET BUY order...")
        order = client.orders.create_market_order(
            symbol=symbol,
            side="LONG",
            quantity=quantity,
            leverage=leverage
        )
        
        print(f"✅ Order placed!")
        print(f"   Order ID: {order.order_id if hasattr(order, 'order_id') else order.__dict__}")
        
        # Wait and check position
        print(f"\n3️⃣ Waiting for execution...")
        time.sleep(3)
        
        positions = client.positions.list_open()
        doge_pos = next((p for p in positions if p.symbol == symbol), None)
        
        if doge_pos:
            print(f"✅ Position opened!")
            print(f"\n📊 Position Details:")
            pos_data = doge_pos.__dict__
            for key, value in pos_data.items():
                print(f"   {key}: {value}")
            
            # Ask about closing
            close = input("\nDo you want to close this position now? (yes/no): ")
            
            if close.lower() == 'yes':
                print(f"\n   Placing MARKET SELL order to close...")
                close_order = client.orders.create_market_order(
                    symbol=symbol,
                    side="SHORT",
                    quantity=quantity,
                    leverage=leverage,
                    reduce_only=True
                )
                
                print(f"   ✅ Close order placed!")
                time.sleep(3)
                
                # Check final balance
                final_balance = client.wallet.get_futures_balance()
                pnl = float(final_balance.balance) - float(balance.balance)
                print(f"\n   💰 Final Balance: ${final_balance.balance} USDT")
                print(f"   {'📈' if pnl >= 0 else '📉'} PnL: ${pnl:.4f} USDT")
        else:
            print(f"⚠️  Position not found (may still be settling)")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("  TEST COMPLETE")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
