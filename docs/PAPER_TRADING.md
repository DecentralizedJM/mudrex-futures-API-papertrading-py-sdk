# Paper Trading / Sandbox Mode

> Trade with simulated funds using real market prices. Perfect for strategy testing, learning, and development.

## Quick Start

```python
from mudrex import MudrexClient

# Initialize in paper trading mode
client = MudrexClient(
    api_secret="your-api-secret",  # Still needed for price feeds
    mode="paper",                   # ← The magic toggle
    paper_balance="10000",          # Start with $10,000 USDT
)

# Now use the SDK exactly as you would with real trading!
# All the same methods work, but no real orders are placed.

# Place a market order
order = client.orders.create_market_order(
    symbol="BTCUSDT",
    side="LONG",
    quantity="0.01",
    leverage="10",
    stoploss_price="65000",
    takeprofit_price="72000",
)

# Check positions
positions = client.positions.list_open()

# Check balance
balance = client.wallet.get_futures_balance()

# Close when done
client.close()
```

## Features

### ✅ Simulated Trading Engine
- Market and limit orders with realistic fills
- LONG and SHORT positions with netting
- Leverage and margin calculations (ISOLATED mode)
- Trading fees (0.05% maker/taker)

### ✅ Real Market Prices
- Uses live Mudrex price feeds
- Positions update with real-time mark prices
- Accurate PnL calculations

### ✅ Stop-Loss & Take-Profit
- Set SL/TP on order creation
- Update SL/TP on open positions
- Background monitor for automatic triggers

### ✅ State Persistence
- SQLite database for trade history
- Save and restore trading state
- Multiple profiles supported

### ✅ Same SDK Interface
- Zero code changes when switching modes
- All standard methods work identically
- Seamless transition to live trading

## Configuration Options

```python
client = MudrexClient(
    api_secret="...",
    mode="paper",                     # Enable paper trading
    paper_balance="10000",            # Initial USDT balance (default: 10,000)
    paper_db_path="./my_paper.db",    # Custom database path
    paper_sltp_monitor=True,          # Enable SL/TP background monitor
    paper_sltp_interval=5,            # Check interval in seconds
)
```

## Paper-Specific Methods

In addition to standard SDK methods, paper mode provides:

### Get Trading Statistics
```python
stats = client.get_paper_statistics()
print(stats)
# {
#     'total_balance': '10150.00',
#     'available_balance': '10150.00',
#     'unrealized_pnl': '0',
#     'realized_pnl': '150.00',
#     'total_pnl': '150.00',
#     'total_fees_paid': '2.50',
#     'total_trades': 2,
#     'winning_trades': 1,
#     'losing_trades': 1,
#     'win_rate': '50.00%',
#     'open_positions': 0
# }
```

### Get Trade History
```python
trades = client.get_paper_trade_history(
    symbol="BTCUSDT",  # Optional filter
    limit=50,          # Max records
)
```

### Reset Paper Trading
```python
client.reset_paper_trading(
    new_balance="10000",  # Fresh start
)
```

### Save State Manually
```python
# State is auto-saved on close(), but you can save manually
client.save_paper_state()
```

### Export/Import State
```python
# Export to JSON
state = client.export_paper_state()
with open("backup.json", "w") as f:
    json.dump(state, f)

# Import from JSON
with open("backup.json", "r") as f:
    state = json.load(f)
client.import_paper_state(state)
```

## Order Types Supported

### Market Orders
```python
order = client.orders.create_market_order(
    symbol="BTCUSDT",
    side="LONG",           # or "SHORT"
    quantity="0.01",
    leverage="10",
    stoploss_price="65000",
    takeprofit_price="72000",
)
```

### Limit Orders
```python
order = client.orders.create_limit_order(
    symbol="BTCUSDT",
    side="LONG",
    quantity="0.01",
    price="66000",         # Limit price
    leverage="10",
)
```

## Position Management

### List Open Positions
```python
positions = client.positions.list_open()
for pos in positions:
    print(f"{pos.symbol}: {pos.unrealized_pnl}")
```

### Update SL/TP
```python
client.positions.update_sltp(
    position_id="pos_123",
    stoploss_price="64000",
    takeprofit_price="73000",
)
```

### Close Position
```python
# Close fully
client.positions.close(position_id="pos_123")

# Or close by symbol/side
# (place opposite order)
```

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MudrexClient                         │
│                    mode="paper"                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │  Paper APIs     │    │  PaperTradingEngine         │ │
│  │  (Same interface│───▶│  - Order matching           │ │
│  │   as live)      │    │  - Position netting         │ │
│  └─────────────────┘    │  - Margin calculations      │ │
│                         │  - PnL tracking             │ │
│  ┌─────────────────┐    └───────────┬─────────────────┘ │
│  │  PriceFeed      │                │                   │
│  │  (Live Mudrex)  │◀───────────────┤                   │
│  └─────────────────┘                │                   │
│                                     ▼                   │
│  ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │  SL/TP Monitor  │◀──▶│  SQLite Persistence         │ │
│  │  (Background)   │    │  (Trade history + state)    │ │
│  └─────────────────┘    └─────────────────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Margin & Leverage

- **Margin Mode**: ISOLATED only (V1)
- **Margin Calculation**: `quantity × entry_price / leverage`
- **Available Balance**: `total_balance - locked_margin + unrealized_pnl`

### Position Netting

Same symbol + same side = one position with averaged entry:

```
Order 1: BUY 0.1 BTC @ $65,000
Order 2: BUY 0.1 BTC @ $67,000
─────────────────────────────────
Position: 0.2 BTC @ $66,000 (averaged)
```

Opposite side reduces or flips position:

```
Position: LONG 0.2 BTC
Order: SHORT 0.3 BTC
─────────────────────────────────
Result: SHORT 0.1 BTC (flipped)
```

### Fee Structure

- **Trading Fee**: 0.05% of notional value
- **Calculated as**: `quantity × price × 0.0005`

## Comparison: Paper vs Live

| Feature              | Paper Mode          | Live Mode           |
|----------------------|---------------------|---------------------|
| API Secret           | Required (prices)   | Required (trading)  |
| Real Orders          | ❌ Never             | ✅ Yes               |
| Real Prices          | ✅ Live feeds        | ✅ Live feeds        |
| Margin Deduction     | ✅ Simulated         | ✅ Real              |
| PnL Calculations     | ✅ Accurate          | ✅ Accurate          |
| Fees                 | ✅ Simulated (0.05%) | ✅ Real              |
| SL/TP Triggers       | ✅ Background monitor| ✅ Exchange side     |
| State Persistence    | ✅ SQLite            | Exchange account    |

## Error Handling

Paper mode uses the same exceptions:

```python
from mudrex.paper import (
    InsufficientMarginError,
    InvalidOrderError,
    PositionNotFoundError,
)

try:
    order = client.orders.create_market_order(...)
except InsufficientMarginError as e:
    print(f"Not enough margin: {e}")
except InvalidOrderError as e:
    print(f"Invalid order: {e}")
```

## Testing & Development

### Using Mock Prices (Offline)

For unit tests or offline development:

```python
from mudrex.paper import (
    PaperTradingEngine,
    MockPriceFeedService,
)

# Create mock price feed
prices = MockPriceFeedService()
prices.set_price("BTCUSDT", Decimal("65000"))

# Create engine with mock prices
engine = PaperTradingEngine(
    initial_balance=Decimal("10000"),
    price_feed=prices,
)

# Simulate price movements
prices.set_price("BTCUSDT", Decimal("70000"))
```

### In-Memory Database

For testing without file persistence:

```python
from mudrex.paper import InMemoryPaperDB

db = InMemoryPaperDB()
engine = PaperTradingEngine(
    initial_balance=Decimal("10000"),
    price_feed=prices,
    db=db,
)
```

## Best Practices

1. **Always close the client** to save state:
   ```python
   try:
       # ... trading logic ...
   finally:
       client.close()
   ```

2. **Use consistent leverage** per symbol to match exchange behavior

3. **Monitor SL/TP triggers** in logs for debugging

4. **Reset periodically** when testing new strategies:
   ```python
   client.reset_paper_trading(new_balance="10000")
   ```

5. **Export state** before major changes:
   ```python
   backup = client.export_paper_state()
   ```

## Limitations (V1)

- **ISOLATED margin only** (CROSS coming later)
- **No partial fills** for market orders
- **Limit orders fill immediately** if price is favorable
- **No order book simulation** (uses last price)
- **Liquidation warnings only** (no auto-liquidation)
- **Single account** (no sub-accounts)

## FAQ

**Q: Do I need a real API secret?**
A: Yes, for fetching live prices. Use `MockPriceFeedService` for offline testing.

**Q: Will paper mode ever place real orders?**
A: No. Paper mode never calls order placement endpoints.

**Q: Where is my data stored?**
A: SQLite database at `~/.mudrex_paper.db` (configurable).

**Q: Can I switch between paper and live?**
A: Yes, just change `mode="live"` (or remove the parameter).

**Q: Is the PnL calculation accurate?**
A: Yes, it uses the same formulas as the exchange with real prices.
