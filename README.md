# Mudrex Futures Paper Trading SDK

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Paper trading SDK for Mudrex Futures.** Practice trading with simulated funds - no real money at risk.

> 🎮 **Works offline too (offline mode)!** No API key required. Just download and start trading with mock prices.

**Built by [DecentralizedJM](https://github.com/DecentralizedJM)**

---

## 🎯 What is Paper Trading?

Paper trading lets you practice trading with **fake money** but **real market prices**. It's like a flight simulator for traders - all the realism, none of the risk.

```python
from mudrex import MudrexClient

# Same SDK, just add mode="paper"
client = MudrexClient(
    api_secret="your-api-secret",  # Still needed for live prices
    mode="paper",                   # ← The magic toggle
    paper_balance="10000",          # Start with $10,000 fake USDT
)

# Now trade normally - no real money involved!
order = client.orders.create_market_order(
    symbol="BTCUSDT",
    side="LONG",
    quantity="0.01",
    leverage="10",
)

# Real prices, simulated execution
positions = client.positions.list_open()
print(f"PnL: ${positions[0].unrealized_pnl}")
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔄 **Same SDK Interface** | Zero code changes when switching between paper and live |
| 📈 **Real Market Prices** | Uses live Mudrex price feeds for accuracy |
| 💰 **Simulated Funds** | Start with any amount of virtual USDT |
| 📊 **Full Order Support** | Market orders, limit orders, LONG/SHORT |
| ⚡ **Leverage Trading** | Up to max leverage with margin calculations |
| 🛡️ **Stop-Loss/Take-Profit** | Background monitoring with auto-triggers |
| 💾 **State Persistence** | SQLite database saves your progress |
| 📉 **PnL Tracking** | Real-time unrealized/realized profit tracking |
| 📜 **Trade History** | Complete log of all trades and actions |
| 📊 **Statistics** | Win rate, total PnL, fees paid, and more |

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/DecentralizedJM/mudrex-futures-papertrading-sdk.git
cd mudrex-futures-papertrading-sdk

# Install
pip install -e .
```

---

## 🔌 Two Modes: Online & Offline

### Mode 1: With API Key (Live Prices)

Uses real-time prices from Mudrex. Best for realistic practice.

```python
from mudrex import MudrexClient

client = MudrexClient(
    api_secret="your-api-secret",  # Needed for live prices
    mode="paper",
    paper_balance="10000",
)

# Real market prices, simulated execution
order = client.orders.create_market_order(
    symbol="BTCUSDT",
    side="LONG",
    quantity="0.01",
    leverage="10",
)
```

### Mode 2: No API Key (Offline / Mock Prices)

**Zero dependencies.** No API key, no internet, no account needed.

```python
from decimal import Decimal
from mudrex.paper import PaperTradingEngine, MockPriceFeedService

# Create mock price feed - YOU control the prices
prices = MockPriceFeedService()
prices.set_price("BTCUSDT", Decimal("100000"))
prices.set_price("ETHUSDT", Decimal("3500"))

# Create engine - no API key needed!
engine = PaperTradingEngine(
    initial_balance=Decimal("10000"),
    price_feed=prices,
)

# Place trades
order = engine.create_market_order(
    symbol="BTCUSDT",
    side="LONG",
    quantity=Decimal("0.1"),
    leverage=10,
)

# Simulate market movement
prices.set_price("BTCUSDT", Decimal("105000"))  # Price goes up 5%

# Check your profit
positions = engine.list_open_positions()
print(f"PnL: ${positions[0].unrealized_pnl}")  # $500 profit!

# Close position
engine.close_position(positions[0].position_id)

# Check final balance
stats = engine.get_statistics()
print(f"Final Balance: ${stats['total_balance']}")
```

### Which Mode Should I Use?

| Use Case | Recommended Mode |
|----------|------------------|
| Learning to trade | Offline (Mock) |
| Testing a strategy idea | Offline (Mock) |
| Backtesting with custom prices | Offline (Mock) |
| Unit testing your bot | Offline (Mock) |
| Realistic practice | Online (API) |
| Pre-production testing | Online (API) |

---

## 🤖 AI & MCP Integration

This SDK works seamlessly with AI coding assistants like **Claude**, **ChatGPT**, and **Cursor** via the Model Context Protocol (MCP) or simple HTTP API.

### 1. Claude Desktop / Cursor (Local MCP)
Connect your AI assistant directly to your local paper trading engine. Ask Claude to "buy 1 BTC" or "check my PnL" directly in your chat!

```bash
# Run the local MCP server (Offline Mode)
python -m mudrex.mcp_server --offline
```

👉 **[Read the Full MCP Setup Guide](docs/MCP_GUIDE.md)**

### 2. ChatGPT / Web Agents (Cloud API)
Deploy the API server to the cloud (e.g., Railway) to let ChatGPT manage your paper trading portfolio.

```bash
# Start the HTTP API server
python -m mudrex.api_server
```

👉 **[Read the Cloud API Guide](docs/MCP_GUIDE.md#2-cloud-api-server-for-chatgpt--web-llms)**

---

## 🚀 Quick Start

### Basic Usage

```python
from mudrex import MudrexClient

# Initialize in paper mode
client = MudrexClient(
    api_secret="your-api-secret",
    mode="paper",
    paper_balance="10000",
)

# Check balance
balance = client.wallet.get_futures_balance()
print(f"Balance: ${balance.balance}")

# Place a trade
order = client.orders.create_market_order(
    symbol="BTCUSDT",
    side="LONG",
    quantity="0.01",
    leverage="10",
    stoploss_price="65000",
    takeprofit_price="72000",
)

# Check position
positions = client.positions.list_open()
for pos in positions:
    print(f"{pos.symbol}: {pos.side} | PnL: ${pos.unrealized_pnl}")

# Get statistics
stats = client.get_paper_statistics()
print(f"Win Rate: {stats['win_rate']}")

# Always close to save state
client.close()
```

### Configuration Options

```python
client = MudrexClient(
    api_secret="...",
    mode="paper",
    
    # Paper trading options
    paper_balance="10000",           # Initial USDT balance
    paper_db_path="./trades.db",     # Custom database path
    paper_sltp_monitor=True,         # Enable SL/TP background monitor
    paper_sltp_interval=5,           # Check SL/TP every 5 seconds
    
    # V2: Funding & Liquidation
    enable_funding=True,             # Enable 8-hour funding payments
    enable_liquidation=True,         # Enable auto-liquidation
)
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MudrexClient                                │
│                        mode="paper"                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Paper API Layer                           │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────┐  │   │
│  │  │ OrdersAPI  │ │PositionsAPI│ │ WalletAPI  │ │LeverageAPI│  │   │
│  │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬─────┘  │   │
│  │        │              │              │              │        │   │
│  │        └──────────────┴──────────────┴──────────────┘        │   │
│  │                           │                                  │   │
│  └───────────────────────────┼──────────────────────────────────┘   │
│                              ▼                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  PaperTradingEngine                          │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │  • Order Matching & Execution                           │ │   │
│  │  │  • Position Netting (same symbol/side = 1 position)     │ │   │
│  │  │  • Margin & Leverage Calculations                       │ │   │
│  │  │  • Fee Deduction (0.05% per trade)                      │ │   │
│  │  │  • PnL Calculations (unrealized & realized)             │ │   │
│  │  │  • Liquidation Warning System                           │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│           ┌──────────────────┼──────────────────┐                   │
│           ▼                  ▼                  ▼                   │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐        │
│  │  PriceFeed      │ │  SL/TP Monitor  │ │  SQLite DB      │        │
│  │  (Live Mudrex)  │ │  (Background)   │ │  (Persistence)  │        │
│  │                 │ │                 │ │                 │        │
│  │ • Real prices   │ │ • Checks every  │ │ • Wallet state  │        │
│  │ • Asset info    │ │   N seconds     │ │ • Positions     │        │
│  │ • 3s cache      │ │ • Auto-triggers │ │ • Trade history │        │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 How It Works

### 1. Order Execution Flow

```
User places order
        │
        ▼
┌───────────────────┐
│ Validate Order    │ ← Check symbol, quantity, margin
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Fetch Live Price  │ ← From Mudrex API (cached 3s)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Calculate Margin  │ ← margin = (qty × price) / leverage
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Check Balance     │ ← available >= margin + fee?
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Execute Trade     │ ← Deduct margin, record fee
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Update Position   │ ← Create new or net with existing
└─────────────────────
```

### 2. Position Netting

The engine maintains **one position per symbol per side**, just like a real exchange:

```python
# Order 1: Buy 0.1 BTC @ $100,000
# Order 2: Buy 0.1 BTC @ $102,000
# ─────────────────────────────────
# Result: 1 position of 0.2 BTC @ $101,000 (averaged)

# Order 3: Sell 0.3 BTC (opposite side)
# ─────────────────────────────────
# Result: Position flips to SHORT 0.1 BTC
```

### 3. Margin Calculation

```
┌─────────────────────────────────────────────────────────────┐
│                    MARGIN FORMULA                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Initial Margin = (Quantity × Entry Price) / Leverage     │
│                                                             │
│   Example:                                                  │
│   • Buy 0.1 BTC @ $100,000 with 10x leverage                │
│   • Margin = (0.1 × 100,000) / 10 = $1,000                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4. PnL Calculation

```
┌─────────────────────────────────────────────────────────────┐
│                    PNL FORMULAS                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   LONG Position:                                            │
│   Unrealized PnL = Quantity × (Current Price - Entry Price) │
│                                                             │
│   SHORT Position:                                           │
│   Unrealized PnL = Quantity × (Entry Price - Current Price) │
│                                                             │
│   ROE% = (Unrealized PnL / Margin) × 100                    │
│                                                             │
│   Example (LONG):                                           │
│   • Entry: 0.1 BTC @ $100,000, Margin: $1,000               │
│   • Price rises to $105,000                                 │
│   • PnL = 0.1 × (105,000 - 100,000) = $500                  │
│   • ROE = (500 / 1,000) × 100 = 50%                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5. Fee Structure

| Fee Type | Rate | Calculation |
|----------|------|-------------|
| Trading Fee | 0.05% | `quantity × price × 0.0005` |

Fees are deducted from balance on:
- Order execution (opening)
- Position close (closing)

### 6. Stop-Loss / Take-Profit

The SL/TP monitor runs in a background thread:

```
┌─────────────────────────────────────────────────────────┐
│                  SL/TP MONITOR                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   Every N seconds:                                      │
│   ┌─────────────────────────────────────────────────┐   │
│   │ 1. Fetch current prices for all open positions │   │
│   │ 2. For each position with SL/TP:               │   │
│   │    • Check if TP hit first (profit priority)   │   │
│   │    • Check if SL hit                           │   │
│   │ 3. Auto-close triggered positions              │   │
│   │ 4. Record in trade history                     │   │
│   └─────────────────────────────────────────────────┘   │
│                                                         │
│   LONG: SL triggers when price ≤ SL price              │
│         TP triggers when price ≥ TP price              │
│                                                         │
│   SHORT: SL triggers when price ≥ SL price             │
│          TP triggers when price ≤ TP price             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Data Models

### PaperWallet

```python
PaperWallet:
    balance: Decimal          # Total balance (including unrealized PnL)
    available: Decimal        # Available for new trades
    locked_margin: Decimal    # Margin locked in positions
    unrealized_pnl: Decimal   # Current floating PnL
    realized_pnl: Decimal     # Closed position profits
    total_fees_paid: Decimal  # Cumulative trading fees
```

### PaperOrder

```python
PaperOrder:
    order_id: str             # Unique ID (paper_ord_xxx)
    symbol: str               # Trading pair (BTCUSDT)
    side: OrderSide           # LONG or SHORT
    order_type: OrderType     # MARKET or LIMIT
    quantity: Decimal         # Order size
    price: Decimal            # Limit price (if applicable)
    filled_price: Decimal     # Execution price
    status: OrderStatus       # PENDING, FILLED, CANCELLED
    leverage: int             # Position leverage
    stoploss_price: Decimal   # Optional SL
    takeprofit_price: Decimal # Optional TP
    fee: Decimal              # Trading fee paid
    created_at: datetime
    filled_at: datetime
```

### PaperPosition

```python
PaperPosition:
    position_id: str          # Unique ID (paper_pos_xxx)
    symbol: str               # Trading pair
    side: PositionSide        # LONG or SHORT
    quantity: Decimal         # Position size
    entry_price: Decimal      # Average entry price
    mark_price: Decimal       # Current market price
    leverage: int             # Position leverage
    margin: Decimal           # Locked margin
    unrealized_pnl: Decimal   # Current floating PnL
    realized_pnl: Decimal     # PnL when closed
    roe_percent: float        # Return on equity %
    stoploss_price: Decimal   # Stop-loss price
    takeprofit_price: Decimal # Take-profit price
    liquidation_price: Decimal # Estimated liquidation
    status: PositionStatus    # OPEN or CLOSED
    created_at: datetime
    closed_at: datetime
```

---

## 🔌 API Reference

### Paper-Specific Methods

```python
# Get trading statistics
stats = client.get_paper_statistics()
# Returns: {
#   'total_balance': '10500.00',
#   'realized_pnl': '500.00',
#   'unrealized_pnl': '0',
#   'total_fees_paid': '12.50',
#   'total_trades': 5,
#   'winning_trades': 3,
#   'losing_trades': 2,
#   'win_rate': '60.0%'
# }

# Get trade history
trades = client.get_paper_trade_history(symbol="BTCUSDT", limit=50)

# Reset to fresh state
client.reset_paper_trading(new_balance="10000")

# Export state (for backup)
state = client.export_paper_state()

# Import state (restore backup)
client.import_paper_state(state)

# Manual save (auto-saves on close)
client.save_paper_state()
```

### Standard SDK Methods (All Work in Paper Mode)

```python
# Orders
client.orders.create_market_order(symbol, side, quantity, leverage, ...)
client.orders.create_limit_order(symbol, side, quantity, price, leverage, ...)
client.orders.list_open()
client.orders.cancel(order_id)

# Positions
client.positions.list_open()
client.positions.close(position_id)
client.positions.update_sltp(position_id, stoploss_price, takeprofit_price)

# Wallet
client.wallet.get_futures_balance()

# Leverage
client.leverage.set(symbol, leverage, margin_type)
client.leverage.get(symbol)

# Assets (uses live API)
client.assets.get(symbol)
client.assets.list_all()
```

---

## 💾 Persistence

### Database Location

Default: `~/.mudrex_paper.db`

Custom: `paper_db_path="./my_trades.db"`

### What's Saved

- Wallet state (balance, PnL, fees)
- All open positions
- All pending orders
- Complete trade history
- Leverage settings

### Auto-Save

State is automatically saved when you call `client.close()`.

```python
# Always close the client!
try:
    # ... trading logic ...
finally:
    client.close()  # Saves state

# Or use context manager
with MudrexClient(mode="paper", ...) as client:
    # ... trading logic ...
# Auto-closes and saves
```

---

## 🆚 Paper vs Live Comparison

| Aspect | Paper Mode | Live Mode |
|--------|------------|-----------|
| Real Orders | ❌ Never | ✅ Yes |
| Real Money | ❌ Simulated | ✅ Real |
| Market Prices | ✅ Live feed | ✅ Live feed |
| Order Execution | Instant (simulated) | Exchange matching |
| Slippage | None (uses last price) | Market dependent |
| Fees | 0.05% simulated | Actual exchange fees |
| Liquidation | Warning only | Actual liquidation |
| State Storage | Local SQLite | Exchange servers |
| API Secret | Needed for prices | Needed for trading |

---

## 🧪 Testing Without API

For unit tests or offline development:

```python
from decimal import Decimal
from mudrex.paper import PaperTradingEngine, MockPriceFeedService

# Create mock prices
prices = MockPriceFeedService()
prices.set_price("BTCUSDT", Decimal("100000"))
prices.set_price("ETHUSDT", Decimal("3500"))

# Create engine
engine = PaperTradingEngine(
    initial_balance=Decimal("10000"),
    price_feed=prices,
)

# Place order
order = engine.create_market_order(
    symbol="BTCUSDT",
    side="LONG",
    quantity=Decimal("0.1"),
    leverage=10,
)

# Simulate price movement
prices.set_price("BTCUSDT", Decimal("105000"))

# Check profit
positions = engine.list_open_positions()
print(f"PnL: ${positions[0].unrealized_pnl}")  # $500
```

---


## 🆕 V2 Features: Funding & Liquidation

### Funding Rate Payments

Funding is exchanged every 8 hours (00:00, 08:00, 16:00 UTC) just like real exchanges:

```python
from mudrex import MudrexClient

client = MudrexClient(
    api_secret="...",
    mode="paper",
    paper_balance="10000",
    enable_funding=True,  # Enable funding payments
)

# Place a position
client.orders.create_market_order(
    symbol="BTCUSDT",
    side="LONG",
    quantity="0.1",
    leverage="10",
)

# Funding is automatically applied every 8 hours:
# - Positive rate: LONG pays SHORT
# - Negative rate: SHORT pays LONG
# - Payment = Position Value × Funding Rate

# Check cumulative funding paid
positions = client.positions.list_open()
print(f"Funding paid: ${positions[0].cumulative_funding}")
```

### Auto-Liquidation

Positions are automatically liquidated when margin is exhausted:

```python
client = MudrexClient(
    api_secret="...",
    mode="paper",
    paper_balance="10000",
    enable_liquidation=True,  # Enable auto-liquidation
)

# Place a high-leverage position
order = client.orders.create_market_order(
    symbol="BTCUSDT",
    side="LONG",
    quantity="0.1",
    leverage="20",  # 20x = ~5% liquidation distance
)

# Check liquidation price
positions = client.positions.list_open()
print(f"Entry: ${positions[0].entry_price}")
print(f"Liq Price: ${positions[0].liquidation_price}")

# If price drops to liquidation price, position is auto-closed
# with total loss of margin + 0.5% liquidation fee
```

### Liquidation Price Formula

```
┌─────────────────────────────────────────────────────────────┐
│                 LIQUIDATION FORMULAS                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   LONG Position:                                            │
│   Liq Price = Entry × (1 - 1/Leverage + MMR)                │
│                                                             │
│   SHORT Position:                                           │
│   Liq Price = Entry × (1 + 1/Leverage - MMR)                │
│                                                             │
│   Where MMR (Maintenance Margin Rate) = 0.5%                │
│                                                             │
│   Example (LONG 10x):                                       │
│   • Entry: $100,000                                         │
│   • Liq = 100,000 × (1 - 0.1 + 0.005) = $90,500             │
│   • Price drops 9.5% → LIQUIDATED                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚠️ Limitations

| Limitation | Description |
|------------|-------------|
| Margin Mode | ISOLATED only (CROSS coming later) |
| Partial Fills | Not supported for market orders |
| Order Book | Not simulated (uses last price) |
| Slippage | Not simulated |
| ~~Funding Rates~~ | ✅ Implemented in V2 |
| ~~Liquidation~~ | ✅ Implemented in V2 |

---

## 📂 Project Structure

```
mudrex-futures-papertrading-sdk/
├── mudrex/
│   ├── __init__.py
│   ├── client.py              # MudrexClient with mode="paper"
│   ├── api/                   # Live API modules
│   └── paper/                 # Paper trading module
│       ├── __init__.py
│       ├── models.py          # Data models
│       ├── exceptions.py      # Custom exceptions
│       ├── engine.py          # Core simulation engine
│       ├── price_feed.py      # Live + mock price feeds
│       ├── sltp_monitor.py    # Background SL/TP monitor
│       ├── persistence.py     # SQLite state storage
│       ├── api.py             # SDK-compatible API wrappers
│       ├── external_data.py   # External market data (V2)
│       ├── funding.py         # Funding rate engine (V2)
│       └── liquidation.py     # Liquidation engine (V2)
├── examples/
│   └── paper_trading.py       # Demo script
├── docs/
│   └── PAPER_TRADING.md       # Detailed documentation
└── README.md
```

---

## 🤝 Contributing

Contributions welcome! Please submit a Pull Request.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## ⚠️ Disclaimer

This SDK is for **educational purposes only**. Paper trading results do not guarantee live trading success. Always:
- Test strategies thoroughly before going live
- Start with small amounts when trading real money
- Use proper risk management
- Never trade more than you can afford to lose

---

Built by [DecentralizedJM](https://github.com/DecentralizedJM) with ❤️
