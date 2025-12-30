# Mudrex Trading SDK

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/github/stars/DecentralizedJM/mudrex-trading-sdk?style=social)](https://github.com/DecentralizedJM/mudrex-trading-sdk)

**Unofficial official Python SDK for [Mudrex Futures Trading API](https://docs.trade.mudrex.com)** - Trade crypto futures programmatically with ease.

## 🚀 Features

- **Simple & Intuitive** - Pythonic interface that feels natural
- **Type-Safe** - Full type hints and dataclass models
- **Battle-Tested** - Built-in rate limiting, retries, and error handling
- **Well-Documented** - Comprehensive examples and docstrings
- **Production-Ready** - Designed for real trading applications

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

# List tradable assets
assets = client.assets.list_all()
for asset in assets[:5]:
    print(f"{asset.symbol}: up to {asset.max_leverage}x leverage")

# Set leverage before trading
client.leverage.set("BTCUSDT", leverage="10", margin_type="ISOLATED")

# Place a market order
order = client.orders.create_market_order(
    asset_id="BTCUSDT",
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

## 📚 Documentation

### API Modules

| Module | Description |
|--------|-------------|
| `client.wallet` | Spot & futures wallet balances, fund transfers |
| `client.assets` | Discover tradable instruments, get specifications |
| `client.leverage` | Get/set leverage and margin type |
| `client.orders` | Create, view, cancel, and amend orders |
| `client.positions` | Manage positions, set SL/TP, close/reverse |
| `client.fees` | View trading fee history |

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

# 3️⃣ Find an asset to trade
btc = client.assets.get("BTCUSDT")
print(f"BTC: {btc.min_quantity} min qty, {btc.max_leverage}x max leverage")

# 4️⃣ Set leverage
client.leverage.set("BTCUSDT", leverage="5", margin_type="ISOLATED")

# 5️⃣ Place order with risk management
order = client.orders.create_market_order(
    asset_id="BTCUSDT",
    side="LONG",
    quantity="0.001",
    leverage="5",
    stoploss_price="95000",
    takeprofit_price="110000"
)

# 6️⃣ Monitor position
positions = client.positions.list_open()
for pos in positions:
    print(f"{pos.symbol}: Entry ${pos.entry_price}, PnL: {pos.pnl_percentage:.2f}%")

# 7️⃣ Adjust risk levels
client.positions.set_stoploss(pos.position_id, "96000")

# 8️⃣ Close when ready
client.positions.close(pos.position_id)
```

### Order Types

```python
# Market Order - Executes immediately at current price
order = client.orders.create_market_order(
    asset_id="BTCUSDT",
    side="LONG",       # or "SHORT"
    quantity="0.001",
    leverage="5"
)

# Limit Order - Executes when price reaches target
order = client.orders.create_limit_order(
    asset_id="BTCUSDT",
    side="LONG",
    quantity="0.001",
    price="95000",     # Buy when BTC drops to $95k
    leverage="5"
)

# Order with Stop-Loss & Take-Profit
order = client.orders.create_market_order(
    asset_id="BTCUSDT",
    side="LONG",
    quantity="0.001",
    leverage="10",
    stoploss_price="95000",    # Exit if price drops here
    takeprofit_price="110000"  # Exit if price reaches here
)
```

### Position Management

```python
# View all open positions
positions = client.positions.list_open()

# Close a position completely
client.positions.close(position_id)

# Partially close (reduce size)
client.positions.close_partial(position_id, quantity="0.0005")

# Reverse position (LONG → SHORT)
client.positions.reverse(position_id)

# Set stop-loss
client.positions.set_stoploss(position_id, "95000")

# Set take-profit
client.positions.set_takeprofit(position_id, "110000")

# Set both
client.positions.set_risk_order(
    position_id,
    stoploss_price="95000",
    takeprofit_price="110000"
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
| [quickstart.py](examples/quickstart.py) | Basic trading workflow |
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

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Links

- [Mudrex Trading API Docs](https://docs.trade.mudrex.com)
- [API Quick Reference](https://docs.trade.mudrex.com/docs/quick-reference)
- [Mudrex Platform](https://mudrex.com)

## ⚠️ Disclaimer

This SDK is for educational and informational purposes. Cryptocurrency trading involves significant risk. Always:
- Start with small amounts
- Use proper risk management (stop-losses)
- Never trade more than you can afford to lose
- Test thoroughly in a safe environment first

---

Built with ❤️ for the Mudrex community
