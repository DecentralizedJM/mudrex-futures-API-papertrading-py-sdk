# Mudrex Futures API Trading SDK (Python)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/github/stars/DecentralizedJM/mudrex-trading-sdk?style=social)](https://github.com/DecentralizedJM/mudrex-trading-sdk)

**Python SDK for [Mudrex Futures Trading API](https://docs.trade.mudrex.com/docs/overview)** - Trade crypto futures programmatically with ease.

**Built and maintained by [DecentralizedJM](https://github.com/DecentralizedJM)**

> 📦 **Other Languages:** [Go](https://github.com/DecentralizedJM/mudrex-go-sdk) | [Java](https://github.com/DecentralizedJM/mudrex-java-sdk) | [.NET](https://github.com/DecentralizedJM/mudrex-dotnet-sdk) | [Node.js](https://github.com/DecentralizedJM/mudrex-nodejs-sdk) | [SDK Registry](https://github.com/DecentralizedJM/mudrex-sdk-registry)

## 🚀 Features

- **Symbol-First Trading** - Use symbols like "BTCUSDT", "XRPUSDT" directly (no asset IDs needed!)
- **500+ Trading Pairs** - Access ALL available assets automatically
- **Full API Coverage** - Wallet, orders, positions, leverage, assets, and fees
- **Type Hints** - Dataclass models for all API responses
- **Error Handling** - Typed exceptions for authentication, rate limits, and validation errors
- **Rate Limit Aware** - Respects API limits (2/s, 50/min, 1000/hr, 10000/day)

## 📦 Installation

### Install from GitHub (Recommended)
```bash
pip install git+https://github.com/DecentralizedJM/mudrex-trading-sdk.git
```

### Or clone and install locally
```bash
git clone https://github.com/DecentralizedJM/mudrex-trading-sdk.git
cd mudrex-trading-sdk
pip install -e .
```

## ⚡ Quick Start

```python
from mudrex import MudrexClient

# Initialize the client
client = MudrexClient(api_secret="your-api-secret")

# Check your balance
balance = client.wallet.get_spot_balance()
print(f"Available: ${balance.available}")

# List ALL tradable assets (500+ pairs!)
assets = client.assets.list_all()
print(f"Found {len(assets)} tradable assets!")

# Get any asset by symbol - no asset ID needed!
btc = client.assets.get("BTCUSDT")
xrp = client.assets.get("XRPUSDT")
sol = client.assets.get("SOLUSDT")

# Set leverage using symbol
client.leverage.set("BTCUSDT", leverage="10", margin_type="ISOLATED")

# Place an order using symbol
order = client.orders.create_market_order(
    symbol="BTCUSDT",      # Just use the symbol!
    side="LONG",
    quantity="0.001",
    leverage="10",
    stoploss_price="95000",
    takeprofit_price="110000"
)
print(f"Order placed: {order.order_id}")

# Monitor positions
for position in client.positions.list_open():
    print(f"{position.symbol}: {position.unrealized_pnl} PnL")
```

## 💡 Symbol-First Trading

This SDK uses **trading symbols** directly - no need to look up internal asset IDs!

```python
# ✅ Just use the symbol - it works everywhere!
client.assets.get("XRPUSDT")
client.leverage.set("XRPUSDT", leverage="10")
client.orders.create_market_order(symbol="XRPUSDT", side="LONG", quantity="100", leverage="5")

# The SDK automatically handles the API's is_symbol parameter for you
```

## 📊 Get ALL Assets (500+ Pairs)

```python
# Automatically fetches ALL pages - no pagination limits!
assets = client.assets.list_all()
print(f"Total available: {len(assets)} trading pairs")

# Search for specific assets
btc_pairs = client.assets.search("BTC")      # All BTC pairs
meme_coins = client.assets.search("DOGE")    # Find DOGE

# Check if a symbol exists
if client.assets.exists("XRPUSDT"):
    print("XRP is tradable!")
```

## 📚 Documentation

### API Modules

| Module | Description |
|--------|-------------|
| `client.wallet` | Spot & futures wallet balances, fund transfers |
| `client.assets` | Discover ALL 500+ tradable instruments |
| `client.leverage` | Get/set leverage and margin type |
| `client.orders` | Create, view, cancel, and amend orders |
| `client.positions` | Manage positions, set SL/TP, close/reverse |
| `client.fees` | View trading fee history |

### API Endpoints Reference

| Endpoint | Method | SDK Method |
|----------|--------|------------|
| `/wallet/funds` | POST | `client.wallet.get_spot_balance()` |
| `/futures/funds` | GET | `client.wallet.get_futures_balance()` |
| `/wallet/transfer` | POST | `client.wallet.transfer_to_futures()` |
| `/futures` | GET | `client.assets.list_all()` |
| `/futures/{symbol}?is_symbol` | GET | `client.assets.get(symbol)` |
| `/futures/{symbol}/leverage?is_symbol` | GET/POST | `client.leverage.get(symbol)` / `set(symbol, ...)` |
| `/futures/{symbol}/order?is_symbol` | POST | `client.orders.create_*_order(symbol=...)` |
| `/futures/orders` | GET | `client.orders.list_open()` |
| `/futures/positions` | GET | `client.positions.list_open()` |

📖 [Full API Documentation](https://docs.trade.mudrex.com/docs/overview)

### Complete Trading Workflow

```python
from mudrex import MudrexClient

client = MudrexClient(api_secret="your-secret")

# 1️⃣ Check balance
spot = client.wallet.get_spot_balance()
futures = client.wallet.get_futures_balance()
print(f"Spot: ${spot.available} | Futures: ${futures.balance}")

# 2️⃣ Transfer funds to futures (if needed)
if float(futures.balance) < 100:
    client.wallet.transfer_to_futures("100")

# 3️⃣ Find an asset to trade (use ANY symbol!)
btc = client.assets.get("BTCUSDT")
xrp = client.assets.get("XRPUSDT")
print(f"XRP: {xrp.min_quantity} min qty, {xrp.max_leverage}x max leverage")

# 4️⃣ Set leverage
client.leverage.set("XRPUSDT", leverage="5", margin_type="ISOLATED")

# 5️⃣ Place order with risk management
order = client.orders.create_market_order(
    symbol="XRPUSDT",
    side="LONG",
    quantity="100",
    leverage="5",
    stoploss_price="2.00",
    takeprofit_price="3.50"
)

# 6️⃣ Monitor position
positions = client.positions.list_open()
for pos in positions:
    print(f"{pos.symbol}: Entry ${pos.entry_price}, PnL: {pos.pnl_percentage:.2f}%")

# 7️⃣ Adjust risk levels
client.positions.set_stoploss(pos.position_id, "2.10")

# 8️⃣ Close when ready
client.positions.close(pos.position_id)
```

### Order Types

```python
# Market Order - Executes immediately at current price
order = client.orders.create_market_order(
    symbol="BTCUSDT",
    side="LONG",       # or "SHORT"
    quantity="0.001",
    leverage="5"
)

# Limit Order - Executes when price reaches target
order = client.orders.create_limit_order(
    symbol="XRPUSDT",
    side="LONG",
    quantity="100",
    price="2.00",      # Buy when XRP drops to $2
    leverage="5"
)

# Order with Stop-Loss & Take-Profit
order = client.orders.create_market_order(
    symbol="ETHUSDT",
    side="LONG",
    quantity="0.1",
    leverage="10",
    stoploss_price="3000",     # Exit if price drops here
    takeprofit_price="4000"    # Exit if price reaches here
)
```

### Position Management

```python
# View all open positions
positions = client.positions.list_open()

# Close a position completely
client.positions.close(position_id)

# Partially close (reduce size)
client.positions.close_partial(position_id, quantity="50")

# Reverse position (LONG → SHORT)
client.positions.reverse(position_id)

# Set stop-loss
client.positions.set_stoploss(position_id, "2.00")

# Set take-profit
client.positions.set_takeprofit(position_id, "3.50")

# Set both
client.positions.set_risk_order(
    position_id,
    stoploss_price="2.00",
    takeprofit_price="3.50"
)
```

### Error Handling

```python
from mudrex import MudrexClient
from mudrex.exceptions import (
    MudrexAPIError,
    MudrexAuthenticationError,
    MudrexRateLimitError,
    MudrexValidationError,
)

try:
    client = MudrexClient(api_secret="your-secret")
    order = client.orders.create_market_order(...)
    
except MudrexAuthenticationError:
    print("Invalid API key - check your credentials")
    
except MudrexRateLimitError as e:
    print(f"Rate limited - retry after {e.retry_after}s")
    
except MudrexValidationError as e:
    print(f"Invalid parameters: {e.message}")
    
except MudrexAPIError as e:
    print(f"API error: {e.message}")
    print(f"Request ID: {e.request_id}")  # For support tickets
```

## 🔑 Getting Your API Key

1. **Complete KYC** - Verify your identity with PAN & Aadhaar
2. **Enable 2FA** - Set up TOTP two-factor authentication
3. **Generate API Key** - Go to Dashboard → API Keys → Generate
4. **Save Secret** - Copy and store securely (shown only once!)

📖 [Detailed Guide](https://docs.trade.mudrex.com/docs/api-key-management)

## ⚠️ Rate Limits

| Window | Limit |
|--------|-------|
| Second | 2 requests |
| Minute | 50 requests |
| Hour | 1000 requests |
| Day | 10000 requests |

The SDK includes automatic rate limiting. For high-frequency use cases, consider:
- Batching operations where possible
- Using webhooks for real-time updates
- Implementing exponential backoff for retries

## 📂 Examples

Check out the [examples/](examples/) folder:

| Example | Description |
|---------|-------------|
| [quickstart.py](examples/quickstart.py) | Basic trading workflow with ALL assets |
| [trading_bot.py](examples/trading_bot.py) | Simple automated trading bot |
| [async_trading.py](examples/async_trading.py) | Async/concurrent operations |
| [error_handling.py](examples/error_handling.py) | Robust error handling patterns |

## 🛠️ Development

```bash
# Clone the repo
git clone https://github.com/DecentralizedJM/mudrex-trading-sdk.git
cd mudrex-trading-sdk

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black mudrex/
isort mudrex/

# Type checking
mypy mudrex/
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

##  Contributors

- [@DecentralizedJM](https://github.com/DecentralizedJM) - Creator & Maintainer

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Links

- [Mudrex Trading API Docs](https://docs.trade.mudrex.com/docs/overview)
- [SDK Registry (All Languages)](https://github.com/DecentralizedJM/mudrex-sdk-registry)
- [Mudrex Platform](https://mudrex.com)

## ⚠️ Disclaimer

**This is an UNOFFICIAL SDK.** This SDK is for educational and informational purposes. Cryptocurrency trading involves significant risk. Always:
- Start with small amounts
- Use proper risk management (stop-losses)
- Never trade more than you can afford to lose
- Test thoroughly in a safe environment first

---

Built and maintained by [DecentralizedJM](https://github.com/DecentralizedJM) with ❤️
