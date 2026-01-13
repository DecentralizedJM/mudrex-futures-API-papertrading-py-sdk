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

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Mudrex Paper Trading imports
from mudrex.paper import (
    PaperTradingEngine,
    MockPriceFeedService,
)
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
        
        # Create mock price feed with default prices
        self.price_feed = MockPriceFeedService()
        self._set_default_prices()
        
        # Create paper trading engine
        self.engine = PaperTradingEngine(
            initial_balance=initial_balance,
            price_feed=self.price_feed,
        )
        
        logger.info(f"Created session {session_id} with balance ${initial_balance}")
    
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


def get_or_create_session(session_id: Optional[str] = None, balance: str = "10000") -> UserSession:
    """Get existing session or create new one."""
    if session_id and session_id in sessions:
        session = sessions[session_id]
        session.touch()
        return session
    
    # Create new session
    new_id = session_id or f"session_{uuid.uuid4().hex[:12]}"
    session = UserSession(new_id, Decimal(balance))
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
    position_id: str
    stoploss: Optional[str] = None
    takeprofit: Optional[str] = None


class SetPriceRequest(BaseModel):
    symbol: str
    price: str


class ResetAccountRequest(BaseModel):
    balance: str = "10000"


class CreateSessionRequest(BaseModel):
    balance: str = "10000"


# ============================================================================
# FastAPI App
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 Mudrex Paper Trading API Server starting...")
    logger.info("📝 API docs available at /docs")
    logger.info("💡 Tip: Run 'ngrok http 8000' for public access")
    yield
    logger.info("👋 Server shutting down...")


app = FastAPI(
    title="Mudrex Paper Trading API",
    description="""
# 🎮 Paper Trading API for LLMs

Practice crypto trading with simulated funds. Works with ChatGPT, Claude, or any LLM.

## How to Use

1. **Create a session** - `POST /session` → get a `session_id`
2. **Trade** - Use the session_id in `X-Session-ID` header
3. **Check positions** - `GET /positions`
4. **Close trades** - `POST /positions/{id}/close`

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


# ============================================================================
# Helper Functions
# ============================================================================

def format_decimal(value: Decimal) -> str:
    """Format Decimal for JSON response."""
    return f"{value:.8f}".rstrip('0').rstrip('.')


def get_session(x_session_id: Optional[str] = Header(default=None)) -> UserSession:
    """Dependency to get user session from header."""
    if not x_session_id:
        # Create a default session for simple testing
        return get_or_create_session("default")
    
    if x_session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session not found: {x_session_id}")
    
    session = sessions[x_session_id]
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


# ============================================================================
# Session Management
# ============================================================================

@app.post("/session", tags=["Session"])
async def create_session(request: CreateSessionRequest = None):
    """
    Create a new paper trading session.
    
    Returns a session_id to use in subsequent requests via X-Session-ID header.
    """
    balance = request.balance if request else "10000"
    session = get_or_create_session(balance=balance)
    
    return {
        "session_id": session.session_id,
        "balance": format_decimal(session.engine.get_wallet().balance),
        "created_at": session.created_at.isoformat(),
        "message": f"Session created! Use X-Session-ID: {session.session_id} header for all requests.",
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
