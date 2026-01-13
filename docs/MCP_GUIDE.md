# 🤖 Mudrex AI & MCP Integration Guide

This SDK provides two powerful ways to integrate Mudrex Paper Trading with AI assistants like Claude, ChatGPT, and Cursor.

| Method | Best For | Technical Details |
| :--- | :--- | :--- |
| **Local MCP Server** | Desktop Apps (Claude Desktop, Cursor) | Runs locally on your machine via stdio. |
| **Cloud API Server** | Web Apps (ChatGPT, any LLM) | Runs on Railway/Cloud, exposed via HTTP. |

---

## 1. Local MCP Server (for Claude Desktop & Cursor)

The Model Context Protocol (MCP) allows AI coding assistants to directly "talk" to this SDK. This means you can ask Claude to "buy 1 BTC" and it will actually execute the function in your local environment!

### Prerequisites
- Python 3.8+ installed
- `mcp` package installed: `pip install mcp`

### Installation

1. Clone this repo and install dependencies:
   ```bash
   git clone https://github.com/DecentralizedJM/mudrex-futures-papertrading-sdk.git
   cd mudrex-futures-papertrading-sdk
   pip install -e .
   pip install mcp
   ```

2. Test the server command:
   ```bash
   # Offline mode (mock prices)
   python -m mudrex.mcp_server --offline
   ```
   *You should see no output (it waits for JSON-RPC).* Use `Ctrl+C` to exit.

### Configuration for Claude Desktop

1. Open your Claude Desktop config file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add the Mudrex server entry:

   ```json
   {
     "mcpServers": {
       "mudrex-paper": {
         "command": "python",
         "args": [
           "-u",
           "-m",
           "mudrex.mcp_server",
           "--offline",
           "--balance", "50000"
         ],
         "cwd": "/ABSOLUTE/PATH/TO/mudrex-futures-papertrading-sdk",
         "env": {
            "PYTHONPATH": "/ABSOLUTE/PATH/TO/mudrex-futures-papertrading-sdk"
         }
       }
     }
   }
   ```
   *Note: Replace `/ABSOLUTE/PATH/TO/...` with the actual full path to the repository on your machine.*

3. Restart Claude Desktop. You should see a 🔌 icon indicating the tool is connected.

### Example Prompts
- "What is the current price of BTC?"
- "Buy 0.5 BTC at market price."
- "Show me my open positions."
- "Close my ETH position."
- "What is my PnL?"

---

## 2. Cloud API Server (for ChatGPT & Web LLMs)

If you want to use the trading engine with ChatGPT (via Custom GPTs) or any other web-based agent, use the HTTP API Server.

### Deployment (Railway)

1. Fork/Clone this repository.
2. Deploy to [Railway.app](https://railway.app/).
   - Railway will auto-detect the `Procfile` and `Dockerfile`.
   - No special usage of `ngrok` is needed!
3. Copy your public domain (e.g., `https://web-production-xyz.up.railway.app`).

### Connecting to ChatGPT

1. Go to **Explore GPTs** -> **Create**.
2. Go to **Configure** -> **Actions** -> **Create new action**.
3. Select **Import from URL**.
4. Paste your Railway URL followed by `/openapi.json`:
   ```
   https://YOUR-RAILWAY-APP.app/openapi.json
   ```
5. ChatGPT will import all endpoints (`/orders`, `/positions`, etc.).

### Usage
Now you can talk to your Custom GPT:
- "Check my wallet balance."
- "Start a trading session."
- "Short ETH with 5x leverage."

### Advanced: Railway Variables & Direct Upload

#### 1. Environment Variables (Live Prices)
By default, the server runs in **Offline Mode** (mock prices). To use **Live Mudrex Prices**:

1. Go to your Railway Project Dashboard.
2. Click on the **Variables** tab.
3. Add a new variable:
   - **Name**: `MUDREX_API_SECRET`
   - **Value**: `your_real_api_secret_here`
4. Railway will automatically redeploy. The server logs will show `Created session ... [ONLINE (Live Prices)]`.

#### 2. Direct Upload (No Git)
If you want to deploy without pushing to GitHub/GitLab, use the [Railway CLI](https://docs.railway.app/guides/cli):

1. **Install CLI**:
   ```bash
   brew install railway
   ```
2. **Login & Init**:
   ```bash
   railway login
   railway init
   ```
3. **Deploy from Local Folder**:
   ```bash
   railway up
   ```
   *This uploads your current folder directly to Railway builds.*

---

## 3. Comparison

| Feature | Local MCP | Cloud API |
| :--- | :--- | :--- |
| **Setup** | Edit JSON config file | Deploy to Cloud |
| **Latency** | Instant (Local) | Network dependent |
| **Privacy** | Data stays on machine | Data on cloud server |
| **Multi-user** | Single user (You) | Multi-user support (via sessions) |
| **Tools** | Claude Desktop, Cursor | ChatGPT, Web Apps |
