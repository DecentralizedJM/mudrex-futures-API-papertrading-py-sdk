# MCP Server for Mudrex Paper Trading

This guide explains how to set up and use the MCP (Model Context Protocol) server for paper trading with AI assistants like Claude.

## What is MCP?

MCP (Model Context Protocol) is a protocol that allows AI assistants to call tools and functions you define. With the Mudrex Paper Trading MCP server, you can:

- **Trade with natural language**: "Buy 0.1 BTC with 10x leverage"
- **Check positions**: "What's my PnL?"
- **Manage risk**: "Set a stop loss at $90,000"
- **Analyze performance**: "What's my win rate?"

## Installation

### 1. Install MCP SDK

```bash
pip install mcp
```

### 2. Install the Paper Trading SDK

```bash
pip install git+https://github.com/DecentralizedJM/mudrex-futures-papertrading-sdk.git
```

## Running the Server

### Offline Mode (No API Key)

Perfect for testing and learning:

```bash
python -m mudrex.mcp_server --offline --balance 10000
```

### Online Mode (Live Prices)

Uses real-time prices from Mudrex:

```bash
python -m mudrex.mcp_server --api-secret YOUR_API_SECRET --balance 10000
```

### With Persistence

Save your trades to a database:

```bash
python -m mudrex.mcp_server --offline --balance 10000 --db-path ./my_trades.db
```

## Configuring Claude Desktop

Add to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mudrex-paper": {
      "command": "python",
      "args": ["-m", "mudrex.mcp_server", "--offline", "--balance", "10000"]
    }
  }
}
```

For online mode with API key:

```json
{
  "mcpServers": {
    "mudrex-paper": {
      "command": "python",
      "args": [
        "-m", "mudrex.mcp_server",
        "--api-secret", "YOUR_API_SECRET",
        "--balance", "10000"
      ]
    }
  }
}
```

## Available Tools

| Tool | Description | Example |
|------|-------------|---------|
| `get_balance` | Check wallet balance | "What's my balance?" |
| `get_price` | Get current price | "What's the BTC price?" |
| `place_market_order` | Open position | "Long 0.1 BTC at 10x" |
| `place_limit_order` | Limit order | "Buy 0.1 BTC at $90,000" |
| `list_positions` | View positions | "Show my positions" |
| `close_position` | Close position | "Close my BTC position" |
| `close_all_positions` | Close all | "Close everything" |
| `update_sltp` | Set SL/TP | "Set stop loss at $90k" |
| `get_statistics` | Trading stats | "What's my win rate?" |
| `get_trade_history` | Past trades | "Show my last 10 trades" |
| `reset_account` | Reset account | "Reset to $50,000" |
| `set_mock_price` | Set price (offline) | "Set BTC to $100,000" |
| `get_funding_info` | Funding rates | "What's BTC funding?" |

## Example Conversations

### Opening a Position

**You**: "I want to go long on Bitcoin with 0.05 BTC and 20x leverage"

**Claude**: ✅ Opened LONG position: 0.05 BTC @ $95,000 with 20x leverage. Your margin used is $237.50.

---

### Checking PnL

**You**: "How are my positions doing?"

**Claude**: You have 1 open position:
- **BTCUSDT LONG**: 0.05 BTC @ $95,000
- Current price: $97,500
- Unrealized PnL: **+$125.00** (+52.6% ROE)

---

### Setting Stop Loss

**You**: "Set a stop loss at $93,000 and take profit at $100,000"

**Claude**: ✅ Updated your BTCUSDT position:
- Stop Loss: $93,000
- Take Profit: $100,000

---

### Simulating Price Movement (Offline Mode)

**You**: "Set Bitcoin price to $100,000"

**Claude**: ✅ Set BTCUSDT price to $100,000

**You**: "What's my profit now?"

**Claude**: Your BTCUSDT position:
- Entry: $95,000 → Current: $100,000
- Unrealized PnL: **+$250.00** (+105.3% ROE)

---

### Getting Statistics

**You**: "How am I doing overall?"

**Claude**: 📊 **Trading Statistics**:
- Total Balance: $10,250.00
- Total Trades: 5
- Winning Trades: 4
- Losing Trades: 1
- Win Rate: 80%
- Total Realized PnL: +$250.00
- Total Fees Paid: $12.50

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude / Cursor / AI                     │
└─────────────────────────────┬───────────────────────────────┘
                              │ MCP Protocol (stdio)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server                               │
│                  mudrex/mcp_server.py                       │
│                                                             │
│  Tools:                                                     │
│  • get_balance      • list_positions    • get_statistics    │
│  • get_price        • close_position    • get_trade_history │
│  • place_market_order • update_sltp     • reset_account     │
│  • place_limit_order  • close_all       • set_mock_price    │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 PaperTradingEngine                          │
│                                                             │
│  • Order execution    • PnL calculation                     │
│  • Position tracking  • Margin management                   │
│  • SL/TP monitoring   • Statistics                          │
└─────────────────────────────┬───────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│    MockPriceFeedService │     │    PriceFeedService     │
│      (Offline Mode)     │     │    (Live Mudrex API)    │
│                         │     │                         │
│  You control prices     │     │  Real market prices     │
└─────────────────────────┘     └─────────────────────────┘
```

## Troubleshooting

### "MCP SDK not installed"

```bash
pip install mcp
```

### "API secret required for online mode"

Either use `--offline` flag or provide `--api-secret`:

```bash
# Offline
python -m mudrex.mcp_server --offline

# Online
python -m mudrex.mcp_server --api-secret YOUR_SECRET
```

### Claude doesn't see the tools

1. Restart Claude Desktop after updating config
2. Check the config file path is correct
3. Verify Python is in your PATH

### Server crashes on startup

Check the logs for errors. Common issues:
- Missing dependencies: `pip install mcp`
- Invalid API key format
- Python version < 3.8

## Security Notes

⚠️ **Important**:

1. **Never share your API secret** in config files you commit to git
2. Use environment variables for production:
   ```json
   {
     "mcpServers": {
       "mudrex-paper": {
         "command": "python",
         "args": ["-m", "mudrex.mcp_server", "--api-secret"],
         "env": {
           "MUDREX_API_SECRET": "your-secret-here"
         }
       }
     }
   }
   ```
3. The paper trading server **cannot** place real trades - it only reads prices
4. Your trades are stored locally in SQLite (or in-memory if no db-path)

## Contributing

Found a bug or want to add a feature? PRs welcome!

https://github.com/DecentralizedJM/mudrex-futures-papertrading-sdk
