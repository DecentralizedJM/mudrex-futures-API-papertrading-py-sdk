#!/usr/bin/env python3
"""
Mudrex Paper Trading HTTP API Server

A REST API server that exposes paper trading functionality to any LLM or client.
Run with ngrok for public access.

Usage:
    # Start server
    python -m mudrex.api_server
    
    # In another terminal, expose with ngrok
    ngrok http 8000
    
    # Now any LLM can call your public URL!
"""

import os
import uuid
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# Mudrex Paper Trading imports
from mudrex.paper import (
    PaperTradingEngine,
    MockPriceFeedService,
    PriceFeedService,
)

# For Online Mode
try:
    from mudrex.api.assets import AssetsAPI
except ImportError:
    AssetsAPI = None

# Side is just a string: "LONG" or "SHORT"
from mudrex.paper.exceptions import (
    InsufficientMarginError,
    InvalidOrderError,
    PositionNotFoundError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mudrex-api")

# ============================================================================
# Session Management - Each user gets their own paper trading engine
# ============================================================================

class UserSession:
    """Represents a user's paper trading session."""
    
    def __init__(self, session_id: str, initial_balance: Decimal = Decimal("10000")):
        self.session_id = session_id
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = self.created_at
        
        # Check for online mode via Env Var
        self.api_secret = os.environ.get("MUDREX_API_SECRET")
        
        if self.api_secret and AssetsAPI:
            self._init_online_mode()
        else:
            self._init_offline_mode()
        
        # Create paper trading engine
        self.engine = PaperTradingEngine(
            initial_balance=initial_balance,
            price_feed=self.price_feed,
        )
        
        mode = "ONLINE (Live Prices)" if self.api_secret else "OFFLINE (Mock Prices)"
        logger.info(f"Created session {session_id} with balance ${initial_balance} [{mode}]")

    def _init_online_mode(self):
        """Initialize with live Mudrex price feed."""
        # Create a minimal client wrapper for AssetsAPI
        class MinimalClient:
            def __init__(self, secret):
                self.api_secret = secret
                self.base_url = "https://trade.mudrex.com/fapi/v1"
        
        client = MinimalClient(self.api_secret)
        assets_api = AssetsAPI(client)
        self.price_feed = PriceFeedService(assets_api)

    def _init_offline_mode(self):
        """Initialize with mock price feed."""
        self.price_feed = MockPriceFeedService()
        self._set_default_prices()
    
    def _set_default_prices(self):
        """Set default crypto prices."""
        self.price_feed.set_price("BTCUSDT", Decimal("95000"))
        self.price_feed.set_price("ETHUSDT", Decimal("3500"))
        self.price_feed.set_price("SOLUSDT", Decimal("150"))
        self.price_feed.set_price("BNBUSDT", Decimal("600"))
        self.price_feed.set_price("XRPUSDT", Decimal("2.50"))
        self.price_feed.set_price("ADAUSDT", Decimal("1.10"))
        self.price_feed.set_price("DOGEUSDT", Decimal("0.35"))
        self.price_feed.set_price("DOTUSDT", Decimal("18"))
        self.price_feed.set_price("AVAXUSDT", Decimal("85"))
        self.price_feed.set_price("LINKUSDT", Decimal("25"))
    
    def touch(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)


# Global session store
sessions: Dict[str, UserSession] = {}


def get_or_create_session(
    session_id: Optional[str] = None, 
    balance: str = "10000",
    api_token: Optional[str] = None
) -> UserSession:
    """Get existing session or create new one."""
    if session_id and session_id in sessions:
        session = sessions[session_id]
        session.touch()
        return session
    
    # Create new session
    new_id = session_id or f"session_{uuid.uuid4().hex[:12]}"
    session = UserSession(new_id, Decimal(balance))
    
    # If user provided a specific token, override env var check
    if api_token:
        session.api_secret = api_token
        if AssetsAPI:
            session._init_online_mode()
            logger.info(f"Session {new_id} UPGRADED to ONLINE mode via User Token")
            
    sessions[new_id] = session
    return session


# ============================================================================
# Pydantic Models for API
# ============================================================================

class MarketOrderRequest(BaseModel):
    symbol: str = Field(..., description="Trading pair (e.g., BTCUSDT)")
    side: str = Field(..., description="LONG or SHORT")
    quantity: str = Field(..., description="Amount to trade")
    leverage: int = Field(default=10, description="Leverage (1-100)")
    stoploss: Optional[str] = Field(default=None, description="Stop-loss price")
    takeprofit: Optional[str] = Field(default=None, description="Take-profit price")


class LimitOrderRequest(BaseModel):
    symbol: str
    side: str
    quantity: str
    price: str
    leverage: int = 10
    stoploss: Optional[str] = None
    takeprofit: Optional[str] = None


class UpdateSLTPRequest(BaseModel):
    stoploss: Optional[str] = None
    takeprofit: Optional[str] = None


class SetPriceRequest(BaseModel):
    symbol: str
    price: str


class ResetAccountRequest(BaseModel):
    balance: str = "10000"


class CreateSessionRequest(BaseModel):
    initial_balance: str = Field(default="10000", description="Simulated starting balance")
    api_token: Optional[str] = Field(default=None, description="Mudrex API Secret (for live prices)")


# ============================================================================
# FastAPI App
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 Mudrex Paper Trading API Server starting...")
    yield
    logger.info("👋 Server shutting down...")


app = FastAPI(
    title="Mudrex Paper Trading API",
    description="""
# 🎮 Paper Trading API for LLMs

Practice crypto trading with simulated funds. Works with ChatGPT, Claude, or any LLM.

## Features
- **Instant Sessions**: Start trading immediately
- **Live Prices**: (Requires API Secret provided in session creation or env var)
- **Offline Mode**: Works with mock data if no key provided

## How to Use

1. **Create a session** - `POST /session` → get a `session_id`
2. **Trade** - Use the session_id as query parameter: `?session_id=YOUR_SESSION_ID`
3. **Check positions** - `GET /positions?session_id=YOUR_SESSION_ID`
4. **Close trades** - `POST /positions/{id}/close?session_id=YOUR_SESSION_ID`

## Quick Start (ChatGPT Custom GPT)

1. Run this server: `python -m mudrex.api_server`
2. Expose with ngrok: `ngrok http 8000`
3. Add the ngrok URL to ChatGPT Actions
4. Import the OpenAPI spec from `/openapi.json`

## Offline Mode

All prices are simulated. Use `POST /price` to set custom prices.
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom OpenAPI schema to include servers field for ChatGPT
def custom_openapi():
    """Custom OpenAPI schema with servers field."""
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    # Get base URL from environment variables (Railway, Render, etc.)
    server_url = None
    
    # Try Railway first
    railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    if railway_domain:
        server_url = f"https://{railway_domain}"
    
    # Try Render
    if not server_url:
        render_url = os.environ.get("RENDER_EXTERNAL_URL")
        if render_url:
            server_url = render_url
    
    # Try custom BASE_URL
    if not server_url:
        server_url = os.environ.get("BASE_URL")
    
    # Fallback to the known Railway URL
    if not server_url:
        server_url = "https://mudrex-futures-api-papertrading-py-sdk-production.up.railway.app"
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        servers=[{"url": server_url, "description": "Production server"}],
    )
    
    # Add privacy policy URL to info section for ChatGPT
    if "info" in openapi_schema:
        openapi_schema["info"]["x-privacy-policy-url"] = f"{server_url}/privacy"
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ============================================================================
# Helper Functions
# ============================================================================

def format_decimal(value: Decimal) -> str:
    """Format Decimal for JSON response."""
    return f"{value:.8f}".rstrip('0').rstrip('.')


def get_session(
    session_id: Optional[str] = Query(default=None, description="Session ID (optional, creates default if not provided)"),
    x_session_id: Optional[str] = Header(default=None, include_in_schema=False)
) -> UserSession:
    """
    Dependency to get user session from query parameter or header.
    
    ChatGPT-compatible: Uses query parameter `session_id` (header is for backward compatibility).
    """
    # Prefer query parameter (ChatGPT compatible), fallback to header
    sid = session_id or x_session_id
    
    if not sid:
        # Create a default session for simple testing
        return get_or_create_session("default")
    
    if sid not in sessions:
        raise HTTPException(status_code=404, detail=f"Session not found: {sid}")
    
    session = sessions[sid]
    session.touch()
    return session


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", tags=["Info"])
async def root():
    """API root - shows welcome message and links."""
    return {
        "name": "Mudrex Paper Trading API",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "status": "running",
        "active_sessions": len(sessions),
    }


@app.get("/health", tags=["Info"])
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/privacy", tags=["Info"], response_class=HTMLResponse)
async def privacy_policy():
    """
    Privacy Policy for the Paper Trading API.
    
    This endpoint provides the privacy policy required by ChatGPT Custom GPTs.
    Returns the privacy policy as HTML for public access.
    """
    privacy_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Privacy Policy - Mudrex Paper Trading API</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; }
            h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
            h2 { color: #555; margin-top: 30px; }
            ul { margin: 10px 0; }
            .disclaimer { background: #f0f0f0; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0; }
            .last-updated { color: #888; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <h1>Privacy Policy - Mudrex Paper Trading API</h1>
        <p class="last-updated"><strong>Last Updated:</strong> January 13, 2026</p>
        
        <h2>Overview</h2>
        <p>The Mudrex Paper Trading API is a simulation service that allows users to practice cryptocurrency trading with virtual funds. This privacy policy explains how we handle your data when you use this service.</p>
        
        <h2>Data Collection</h2>
        <h3>What We Collect</h3>
        <ul>
            <li><strong>Session Data:</strong> Temporary session identifiers and trading simulation data</li>
            <li><strong>Trading Activity:</strong> Simulated trades, positions, and balances (all virtual)</li>
            <li><strong>API Usage:</strong> Standard server logs for debugging and service improvement</li>
        </ul>
        
        <h3>What We DON'T Collect</h3>
        <ul>
            <li>❌ <strong>No Personal Information:</strong> We do not collect names, emails, addresses, or any personally identifiable information</li>
            <li>❌ <strong>No Real Financial Data:</strong> This is a simulation - no real money, accounts, or financial information is involved</li>
            <li>❌ <strong>No Authentication:</strong> No login credentials or authentication tokens are stored</li>
            <li>❌ <strong>No Persistent Storage:</strong> All session data is stored in memory and cleared when the server restarts</li>
        </ul>
        
        <h2>How We Use Your Data</h2>
        <ul>
            <li><strong>Service Operation:</strong> Session data is used solely to maintain your paper trading simulation state</li>
            <li><strong>No Sharing:</strong> We do not share, sell, or distribute any data to third parties</li>
            <li><strong>No Tracking:</strong> We do not track users across sessions or websites</li>
        </ul>
        
        <h2>Data Storage</h2>
        <ul>
            <li><strong>In-Memory Only:</strong> All session data is stored in server memory (RAM)</li>
            <li><strong>Temporary:</strong> Sessions are automatically cleared when the server restarts or a session is deleted</li>
            <li><strong>No Database:</strong> We do not use persistent databases for user data</li>
            <li><strong>No Backups:</strong> Session data is not backed up or archived</li>
        </ul>
        
        <h2>Data Security</h2>
        <ul>
            <li><strong>Simulation Only:</strong> Since this is a paper trading simulation with no real money, there is no financial risk</li>
            <li><strong>No Sensitive Data:</strong> We do not store sensitive personal or financial information</li>
            <li><strong>Standard Security:</strong> We follow standard web security practices (HTTPS, CORS protection)</li>
        </ul>
        
        <h2>Third-Party Services</h2>
        <p>The service may be hosted on platforms like Railway, Render, or similar cloud providers. We do not share your session data with hosting providers beyond what is necessary for service operation.</p>
        
        <h2>Your Rights</h2>
        <ul>
            <li><strong>Delete Session:</strong> You can delete your session at any time using the API</li>
            <li><strong>No Data Retention:</strong> Since data is not persisted, there is no data to retrieve or delete after session expiration</li>
            <li><strong>Transparency:</strong> All API endpoints and data structures are documented in the OpenAPI specification</li>
        </ul>
        
        <h2>Children's Privacy</h2>
        <p>This service is intended for educational purposes. We do not knowingly collect data from children under 13. Since we do not collect personal information, this is not applicable.</p>
        
        <h2>Changes to This Policy</h2>
        <p>We may update this privacy policy from time to time. The "Last Updated" date at the top indicates when changes were made.</p>
        
        <h2>Contact</h2>
        <p>For questions about this privacy policy, please open an issue on GitHub:<br>
        <a href="https://github.com/DecentralizedJM/mudrex-futures-API-papertrading-py-sdk/issues">https://github.com/DecentralizedJM/mudrex-futures-API-papertrading-py-sdk/issues</a></p>
        
        <div class="disclaimer">
            <h2>Disclaimer</h2>
            <p><strong>This is a paper trading simulation service.</strong></p>
            <ul>
                <li>No real money is involved</li>
                <li>No real trades are executed</li>
                <li>All data is temporary and simulation-only</li>
                <li>This service is for educational and testing purposes only</li>
            </ul>
            
            <p><strong>By using this service, you acknowledge that:</strong></p>
            <ol>
                <li>This is a simulation with no real financial transactions</li>
                <li>All session data is temporary and may be lost at any time</li>
                <li>No personal or financial data is collected or stored</li>
                <li>You use this service at your own discretion</li>
            </ol>
        </div>
    </body>
    </html>
    """
    return privacy_html


# ============================================================================
# Session Management
# ============================================================================

@app.post("/session", tags=["Session"])
async def create_session(request: CreateSessionRequest = None):
    """
    Create a new paper trading session.
    
    Optional: Provide `api_token` to use live prices from your own account.
    Returns a session_id to use in subsequent requests via X-Session-ID header.
    """
    initial_balance = request.initial_balance if request else "10000"
    token = request.api_token if request else None
    
    session = get_or_create_session(balance=initial_balance, api_token=token)
    
    # Check if using Live or Mock
    is_live = isinstance(session.price_feed, PriceFeedService)
    
    return {
        "session_id": session.session_id,
        "balance": format_decimal(session.engine.get_wallet().balance),
        "mode": "ONLINE (Live Prices)" if is_live else "OFFLINE (Mock Prices)",
        "created_at": session.created_at.isoformat(),
        "message": f"Session created! Use ?session_id={session.session_id} query parameter for all requests.",
    }


@app.get("/session", tags=["Session"])
async def get_session_info(session: UserSession = Depends(get_session)):
    """Get current session information."""
    wallet = session.engine.get_wallet()
    positions = session.engine.list_open_positions()
    
    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "last_activity": session.last_activity.isoformat(),
        "balance": format_decimal(wallet.balance),
        "available_balance": format_decimal(wallet.available_balance),
        "open_positions": len(positions),
    }


@app.delete("/session", tags=["Session"])
async def delete_session(session: UserSession = Depends(get_session)):
    """Delete current session."""
    session_id = session.session_id
    if session_id in sessions:
        del sessions[session_id]
    
    return {"message": f"Session {session_id} deleted"}


# ============================================================================
# Balance & Wallet
# ============================================================================

@app.get("/balance", tags=["Wallet"])
async def get_balance(session: UserSession = Depends(get_session)):
    """
    Get current wallet balance.
    
    Returns available balance, locked margin, and unrealized PnL.
    """
    wallet = session.engine.get_wallet()
    
    return {
        "balance": format_decimal(wallet.balance),
        "available": format_decimal(wallet.available),
        "locked_margin": format_decimal(wallet.locked_margin),
        "unrealized_pnl": format_decimal(wallet.unrealized_pnl),
        "currency": "USDT",
    }


# ============================================================================
# Prices
# ============================================================================

@app.get("/price/{symbol}", tags=["Market Data"])
async def get_price(symbol: str, session: UserSession = Depends(get_session)):
    """
    Get current price for a trading symbol.
    
    Examples: BTCUSDT, ETHUSDT, SOLUSDT
    """
    try:
        price = session.price_feed.get_price(symbol.upper())
        return {
            "symbol": symbol.upper(),
            "price": format_decimal(price),
            "source": "simulated",
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Symbol not found: {symbol}")


@app.get("/prices", tags=["Market Data"])
async def get_all_prices(session: UserSession = Depends(get_session)):
    """Get all available prices."""
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", 
               "ADAUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT"]
    
    prices = {}
    for sym in symbols:
        try:
            prices[sym] = format_decimal(session.price_feed.get_price(sym))
        except:
            pass
    
    return {"prices": prices, "source": "simulated"}


@app.post("/price", tags=["Market Data"])
async def set_price(request: SetPriceRequest, session: UserSession = Depends(get_session)):
    """
    Set price for a symbol (simulated mode).
    
    Use this to simulate price movements for testing strategies.
    """
    try:
        symbol = request.symbol.upper()
        price = Decimal(request.price)
        session.price_feed.set_price(symbol, price)
        
        return {
            "symbol": symbol,
            "price": format_decimal(price),
            "message": f"Price set to ${price}",
        }
    except InvalidOperation:
        raise HTTPException(status_code=400, detail="Invalid price format")


# ============================================================================
# Orders
# ============================================================================

@app.post("/orders/market", tags=["Orders"])
async def place_market_order(request: MarketOrderRequest, session: UserSession = Depends(get_session)):
    """
    Place a market order to open a position.
    
    - **LONG**: Profit when price goes UP
    - **SHORT**: Profit when price goes DOWN
    
    Example: Buy 0.01 BTC with 10x leverage
    """
    try:
        symbol = request.symbol.upper()
        side = "LONG" if request.side.upper() in ["LONG", "BUY"] else "SHORT"
        quantity = Decimal(request.quantity)
        leverage = request.leverage
        sl = Decimal(request.stoploss) if request.stoploss else None
        tp = Decimal(request.takeprofit) if request.takeprofit else None
        
        order = session.engine.create_market_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            leverage=leverage,
            stoploss_price=sl,
            takeprofit_price=tp,
        )
        
        # Get the position created
        positions = session.engine.list_open_positions()
        pos = next((p for p in positions if p.symbol == symbol), None)
        
        # Use filled price for market orders
        filled_price = order.filled_price if hasattr(order, 'filled_price') and order.filled_price else order.price
        
        return {
            "success": True,
            "order_id": order.order_id,
            "symbol": symbol,
            "side": side,
            "quantity": format_decimal(quantity),
            "price": format_decimal(filled_price) if filled_price else None,
            "leverage": leverage,
            "margin_used": format_decimal(pos.margin) if pos else None,
            "liquidation_price": format_decimal(pos.liquidation_price) if pos and pos.liquidation_price else None,
            "stoploss": request.stoploss,
            "takeprofit": request.takeprofit,
            "message": f"Opened {side} position: {quantity} {symbol} @ ${format_decimal(filled_price) if filled_price else 'Market'}",
        }
        
    except InsufficientMarginError as e:
        raise HTTPException(status_code=400, detail=f"Insufficient balance: {e}")
    except InvalidOrderError as e:
        raise HTTPException(status_code=400, detail=f"Invalid order: {e}")
    except Exception as e:
        logger.error(f"Order error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orders/limit", tags=["Orders"])
async def place_limit_order(request: LimitOrderRequest, session: UserSession = Depends(get_session)):
    """
    Place a limit order at a specific price.
    
    The order will fill when market price reaches your limit price.
    """
    try:
        symbol = request.symbol.upper()
        side = "LONG" if request.side.upper() in ["LONG", "BUY"] else "SHORT"
        quantity = Decimal(request.quantity)
        price = Decimal(request.price)
        leverage = request.leverage
        sl = Decimal(request.stoploss) if request.stoploss else None
        tp = Decimal(request.takeprofit) if request.takeprofit else None
        
        order = session.engine.create_limit_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            leverage=leverage,
            stoploss_price=sl,
            takeprofit_price=tp,
        )
        
        return {
            "success": True,
            "order_id": order.order_id,
            "symbol": symbol,
            "side": side,
            "quantity": format_decimal(quantity),
            "limit_price": format_decimal(price),
            "status": order.status.value,
            "message": f"Limit order placed: {side} {quantity} {symbol} @ ${price}",
        }
        
    except InsufficientMarginError as e:
        raise HTTPException(status_code=400, detail=f"Insufficient balance: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Positions
# ============================================================================

@app.get("/positions", tags=["Positions"])
async def list_positions(session: UserSession = Depends(get_session)):
    """
    List all open positions.
    
    Shows entry price, current price, unrealized PnL, and ROE%.
    """
    positions = session.engine.list_open_positions()
    
    if not positions:
        return {"positions": [], "count": 0, "total_pnl": "0", "message": "No open positions"}
    
    result = []
    total_pnl = Decimal("0")
    
    for pos in positions:
        pnl = pos.unrealized_pnl
        total_pnl += pnl
        
        # Fetch current price directly from engine's price feed
        try:
            current_price = session.engine.price_feed.get_price(pos.symbol)
        except:
            current_price = pos.entry_price

        result.append({
            "position_id": pos.position_id,
            "symbol": pos.symbol,
            "side": pos.side,
            "quantity": format_decimal(pos.quantity),
            "entry_price": format_decimal(pos.entry_price),
            "current_price": format_decimal(current_price),
            "unrealized_pnl": format_decimal(pnl),
            "roe_percent": f"{pos.roe_percent:.2f}%",
            "leverage": pos.leverage,
            "margin": format_decimal(pos.margin),
            "liquidation_price": format_decimal(pos.liquidation_price) if pos.liquidation_price else None,
            "stoploss": format_decimal(pos.stoploss_price) if pos.stoploss_price else None,
            "takeprofit": format_decimal(pos.takeprofit_price) if pos.takeprofit_price else None,
        })
    
    return {
        "positions": result,
        "count": len(result),
        "total_pnl": format_decimal(total_pnl),
    }


@app.get("/positions/{position_id}", tags=["Positions"])
async def get_position(position_id: str, session: UserSession = Depends(get_session)):
    """Get details of a specific position."""
    positions = session.engine.list_open_positions()
    pos = next((p for p in positions if p.position_id == position_id), None)
    
    if not pos:
        raise HTTPException(status_code=404, detail=f"Position not found: {position_id}")
    
    return {
        "position_id": pos.position_id,
        "symbol": pos.symbol,
        "side": pos.side,
        "quantity": format_decimal(pos.quantity),
        "entry_price": format_decimal(pos.entry_price),
        "current_price": format_decimal(pos.current_price) if pos.current_price else None,
        "unrealized_pnl": format_decimal(pos.unrealized_pnl),
        "roe_percent": f"{pos.roe_percent:.2f}%",
        "leverage": pos.leverage,
        "margin": format_decimal(pos.margin),
        "liquidation_price": format_decimal(pos.liquidation_price) if pos.liquidation_price else None,
    }


@app.post("/positions/{position_id}/close", tags=["Positions"])
async def close_position(position_id: str, session: UserSession = Depends(get_session)):
    """Close a specific position."""
    try:
        trade = session.engine.close_position(position_id)
        
        return {
            "success": True,
            "position_id": position_id,
            "realized_pnl": format_decimal(trade.realized_pnl),
            "close_price": format_decimal(trade.exit_price),
            "message": f"Position closed. Realized PnL: ${trade.realized_pnl}",
        }
        
    except PositionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Position not found: {position_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/positions/close-all", tags=["Positions"])
async def close_all_positions(session: UserSession = Depends(get_session)):
    """Close all open positions."""
    positions = session.engine.list_open_positions()
    
    if not positions:
        return {"success": True, "closed": 0, "message": "No positions to close"}
    
    closed = []
    total_pnl = Decimal("0")
    
    for pos in positions:
        try:
            trade = session.engine.close_position(pos.position_id)
            closed.append({
                "symbol": pos.symbol,
                "side": pos.side,
                "pnl": format_decimal(trade.realized_pnl),
            })
            total_pnl += trade.realized_pnl
        except Exception as e:
            closed.append({"symbol": pos.symbol, "error": str(e)})
    
    return {
        "success": True,
        "closed": len(closed),
        "total_realized_pnl": format_decimal(total_pnl),
        "details": closed,
        "message": f"Closed {len(closed)} positions. Total PnL: ${total_pnl}",
    }


@app.put("/positions/{position_id}/sltp", tags=["Positions"])
async def update_sltp(position_id: str, request: UpdateSLTPRequest, session: UserSession = Depends(get_session)):
    """Update stop-loss and/or take-profit for a position."""
    try:
        sl = Decimal(request.stoploss) if request.stoploss else None
        tp = Decimal(request.takeprofit) if request.takeprofit else None
        
        session.engine.update_position_sltp(
            position_id=position_id,
            stoploss_price=sl,
            takeprofit_price=tp,
        )
        
        return {
            "success": True,
            "position_id": position_id,
            "stoploss": request.stoploss,
            "takeprofit": request.takeprofit,
            "message": "SL/TP updated",
        }
        
    except PositionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Position not found: {position_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Statistics & History
# ============================================================================

@app.get("/statistics", tags=["Analytics"])
async def get_statistics(session: UserSession = Depends(get_session)):
    """
    Get trading statistics.
    
    Includes total trades, win rate, total PnL, etc.
    """
    stats = session.engine.get_statistics()
    return stats


@app.get("/history", tags=["Analytics"])
async def get_trade_history(limit: int = 20, session: UserSession = Depends(get_session)):
    """Get recent trade history."""
    history = session.engine.get_trade_history()
    history = history[-limit:] if len(history) > limit else history
    
    trades = []
    for trade in history:
        trades.append({
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "side": trade.side,
            "quantity": format_decimal(trade.quantity),
            "entry_price": format_decimal(trade.entry_price),
            "exit_price": format_decimal(trade.exit_price) if trade.exit_price else None,
            "realized_pnl": format_decimal(trade.realized_pnl) if trade.realized_pnl else None,
            "status": trade.status,
            "timestamp": trade.timestamp.isoformat() if trade.timestamp else None,
        })
    
    return {"trades": trades, "count": len(trades)}


# ============================================================================
# Account Management
# ============================================================================

@app.post("/reset", tags=["Account"])
async def reset_account(request: ResetAccountRequest = None, session: UserSession = Depends(get_session)):
    """Reset paper trading account to fresh state."""
    balance = request.balance if request else "10000"
    
    try:
        session.engine.reset(Decimal(balance))
        session._set_default_prices()
        
        return {
            "success": True,
            "new_balance": balance,
            "message": f"Account reset to ${balance}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Run the API server."""
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    debug_mode = os.environ.get("MUDREX_DEBUG", "false").lower() == "true"
    
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║           🎮 Mudrex Paper Trading API Server                  ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║   Listening on: http://{host}:{port}                          ║
║   Docs:         http://{host}:{port}/docs                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "mudrex.api_server:app",
        host=host,
        port=port,
        reload=debug_mode,
        log_level="info",
    )


if __name__ == "__main__":
    main()
