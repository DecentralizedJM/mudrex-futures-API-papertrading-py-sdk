"""
Mudrex SDK - Live Trading Script

Places a small test trade to verify the SDK works end-to-end.
"""

from mudrex import MudrexClient
import time

API_SECRET = "e2SYcr7wmpipC6N977QIcc64VaY0FSaz"

def main():
    print("\n" + "=" * 70)
    print("  MUDREX SDK - LIVE TRADING TEST")
    print("=" * 70)
    
    # Initialize
    client = MudrexClient(api_secret=API_SECRET)
    print("\n✅ Client initialized")
    
    # Check balance
    balance = client.wallet.get_futures_balance()
    print(f"\n💰 Futures Balance: ${balance.balance} USDT")
    
    # Trading parameters
    symbol = "BTCUSDT"
    quantity = "0.001"  # Using quantity_step from API
    leverage = "5"  # Moderate leverage for safety
    
    print(f"\n📊 Trade Parameters:")
    print(f"   Symbol: {symbol}")
    print(f"   Quantity: {quantity} BTC")
    print(f"   Leverage: {leverage}x")
    print(f"   Margin Type: ISOLATED")
    
    # Confirm
    print(f"\n⚠️  This will place a REAL trade with REAL money!")
    confirm = input(f"Confirm: BUY {quantity} {symbol} with {leverage}x leverage? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("❌ Trade cancelled")
        return
    
    try:
        # Step 1: Set leverage
        print(f"\n1️⃣ Setting leverage to {leverage}x ISOLATED...")
        client.leverage.set(symbol, leverage=leverage, margin_type="ISOLATED")
        print(f"✅ Leverage set")
        
        # Step 2: Place market order
        print(f"\n2️⃣ Placing MARKET BUY order...")
        order = client.orders.create_market_order(
            symbol=symbol,
            side="LONG",
            quantity=quantity,
            leverage=leverage
        )
        
        print(f"✅ Order placed!")
        print(f"   Order ID: {order.order_id if hasattr(order, 'order_id') else 'N/A'}")
        
        # Step 3: Wait and check position
        print(f"\n3️⃣ Waiting for execution...")
        time.sleep(3)
        
        positions = client.positions.list_open()
        btc_pos = next((p for p in positions if p.symbol == symbol), None)
        
        if btc_pos:
            print(f"✅ Position opened!")
            print(f"\n📊 Position Details:")
            pos_data = btc_pos.__dict__
            print(f"   Symbol: {pos_data.get('symbol', 'N/A')}")
            print(f"   Quantity: {pos_data.get('quantity', 'N/A')}")
            print(f"   Entry Price: ${pos_data.get('entry_price', 'N/A')}")
            print(f"   Leverage: {pos_data.get('leverage', 'N/A')}x")
            print(f"   Margin Used: ${pos_data.get('margin', 'N/A')}")
            print(f"   Unrealized PnL: ${pos_data.get('unrealized_pnl', 'N/A')}")
            
            # Ask about closing
            print(f"\n4️⃣ Position Management:")
            close = input("Do you want to close this position now? (yes/no): ")
            
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
                
                # Verify closed
                positions_after = client.positions.list_open()
                btc_after = next((p for p in positions_after if p.symbol == symbol), None)
                
                if not btc_after:
                    print(f"   ✅ Position CLOSED successfully!")
                    
                    # Check final balance
                    final_balance = client.wallet.get_futures_balance()
                    pnl = float(final_balance.balance) - float(balance.balance)
                    print(f"\n   💰 Final Balance: ${final_balance.balance} USDT")
                    print(f"   {'📈' if pnl >= 0 else '📉'} PnL: ${pnl:.4f} USDT")
                else:
                    print(f"   ℹ️  Position still open (settling...)")
            else:
                print(f"\n   ℹ️  Position remains OPEN. Close manually in Mudrex app.")
        else:
            print(f"⚠️  Position not found (may still be settling)")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("  TRADING TEST COMPLETE")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
