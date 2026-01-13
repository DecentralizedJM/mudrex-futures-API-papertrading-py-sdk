# 🚀 Quick Start: Get Your Paper Trading Endpoint

Get a public endpoint in **5 minutes** to use with ChatGPT, Claude, or any AI tool!

## Option 1: Railway (Recommended - Free Tier Available)

### Step 1: Deploy to Railway

1. **Fork this repository** on GitHub
   - Click "Fork" at: https://github.com/DecentralizedJM/mudrex-futures-API-papertrading-py-sdk

2. **Go to Railway.app**
   - Visit: https://railway.app
   - Sign up with GitHub (free tier available)

3. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your forked repository
   - Railway auto-detects the `Dockerfile` and `Procfile`

4. **Get Your Public URL**
   - Railway automatically deploys
   - Click on your service → "Settings" → "Domains"
   - Copy your public URL: `https://YOUR-APP.up.railway.app`

### Step 2: Use with ChatGPT

1. **Go to ChatGPT Custom GPTs**
   - Visit: https://chat.openai.com/gpts
   - Click "Create" → "Configure"

2. **Add Action**
   - Go to "Actions" tab
   - Click "Create new action"
   - Select "Import from URL"
   - Paste: `https://YOUR-APP.up.railway.app/openapi.json`
   - Click "Import"

3. **Start Trading!**
   - Now you can say: "Check my balance", "Buy 0.1 BTC", etc.

### Step 3: (Optional) Enable Live Prices

1. In Railway dashboard → Your service → "Variables"
2. Add variable:
   - **Name**: `MUDREX_API_SECRET`
   - **Value**: `your-api-secret-here`
3. Railway redeploys automatically

---

## Option 2: Render (Alternative - Free Tier)

1. **Fork the repository** on GitHub

2. **Go to Render.com**
   - Visit: https://render.com
   - Sign up (free tier available)

3. **Create New Web Service**
   - Click "New" → "Web Service"
   - Connect your GitHub repo
   - Settings:
     - **Name**: `mudrex-paper-trading`
     - **Environment**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt && pip install -e .`
     - **Start Command**: `python -m mudrex.api_server`
   - Click "Create Web Service"

4. **Get Your URL**
   - Render provides: `https://YOUR-APP.onrender.com`
   - Use this URL with ChatGPT (same as Railway steps above)

---

## Option 3: Fly.io (Alternative)

1. **Install Fly CLI**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login & Launch**
   ```bash
   fly auth login
   fly launch
   ```

3. **Get Your URL**
   - Fly provides: `https://YOUR-APP.fly.dev`
   - Use with ChatGPT (same as Railway steps)

---

## Option 4: Local Development with ngrok (Testing)

For quick testing without deploying:

1. **Start the server locally**
   ```bash
   python -m mudrex.api_server
   ```

2. **Expose with ngrok** (in another terminal)
   ```bash
   ngrok http 8000
   ```

3. **Copy the ngrok URL**
   - Example: `https://abc123.ngrok.io`
   - Use this URL with ChatGPT (same as Railway steps)

**Note**: ngrok free tier has limitations. Use Railway/Render for production.

---

## Your Endpoint URLs

Once deployed, you'll have these endpoints:

| Endpoint | URL | Purpose |
|----------|-----|---------|
| **API Docs** | `https://YOUR-APP.up.railway.app/docs` | Interactive API documentation |
| **OpenAPI Spec** | `https://YOUR-APP.up.railway.app/openapi.json` | **Use this for ChatGPT** |
| **Health Check** | `https://YOUR-APP.up.railway.app/health` | Check if server is running |
| **Root** | `https://YOUR-APP.up.railway.app/` | API info |

---

## Quick Test

After deployment, test your endpoint:

```bash
curl https://YOUR-APP.up.railway.app/health
```

Should return:
```json
{"status": "healthy", "timestamp": "..."}
```

---

## Troubleshooting

### "Service not found" or 404
- Wait 2-3 minutes for deployment to complete
- Check Railway/Render logs for errors

### "Connection refused"
- Make sure the service is running (check dashboard)
- Verify the URL is correct

### ChatGPT can't import OpenAPI
- Make sure you're using `/openapi.json` (not `/docs`)
- Check that the URL is publicly accessible
- Try opening the URL in a browser first

---

## Next Steps

- 📖 [Full MCP Guide](MCP_GUIDE.md) - For Claude Desktop setup
- 📖 [API Documentation](../README.md) - Full API reference
- 💬 [GitHub Issues](https://github.com/DecentralizedJM/mudrex-futures-API-papertrading-py-sdk/issues) - Get help

---

**That's it!** You now have a public endpoint to use with any AI tool. 🎉
