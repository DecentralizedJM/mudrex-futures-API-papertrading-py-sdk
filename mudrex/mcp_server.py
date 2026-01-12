#!/usr/bin/env python3
"""
Mudrex Paper Trading MCP Server

An MCP (Model Context Protocol) server that exposes paper trading
functionality to AI assistants like Claude, Cursor, etc.

Usage:
    # Online mode (real prices from Mudrex)
    python -m mudrex.mcp_server --api-secret YOUR_SECRET

    # Offline mode (mock prices, no API needed)
    python -m mudrex.mcp_server --offline --balance 10000

    # With custom database path
    python -m mudrex.mcp_server --offline --db-path ./my_trades.db
"""

import argparse
import asyncio
import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("ERROR: MCP SDK not installed. Run: pip install mcp")
    exit(1)

# Mudrex Paper Trading imports
from mudrex.paper import (
    PaperTradingEngine,
    MockPriceFeedService,
    PriceFeedService,
)
from mudrex.paper.models import OrderSide
from mudrex.paper.exceptions import (
    InsufficientBalanceError,
    InvalidOrderError,
    PositionNotFoundError,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mudrex-mcp")

# Global state
engine: Optional[PaperTradingEngine] = None
price_feed: Optional[Any] = None
is_offline: bool = False


def init_engine(
    offline: bool = False,
    api_secret: Optional[str] = None,
    initial_balance: str = "10000",
    db_path: Optional[str] = None,
) -> PaperTradingEngine:
    """Initialize the paper trading engine."""
    global engine, price_feed, is_offline
    
    is_offline = offline
    balance = Decimal(initial_balance)
    
    if offline:
        # Offline mode - use mock prices
        price_feed = MockPriceFeedService()
        # Set some default prices
        price_feed.set_price("BTCUSDT", Decimal("95000"))
        price_feed.set_price("ETHUSDT", Decimal("3500"))
        price_feed.set_price("SOLUSDT", Decimal("150"))
        price_feed.set_price("BNBUSDT", Decimal("600"))
        logger.info("Initialized in OFFLINE mode with mock prices")
    else:
        # Online mode - use live Mudrex prices
        if not api_secret:
            raise ValueError("API secret required for online mode")
        
        # Import here to avoid dependency issues in offline mode
        from mudrex.api.assets import AssetsAPI
        from mudrex import MudrexClient
        
        # Create a minimal client just for price feed
        class MinimalClient:
            def __init__(self, secret):
                self.api_secret = secret
                self.base_url = "https://trade.mudrex.com/fapi/v1"
        
        client = MinimalClient(api_secret)
        assets_api = AssetsAPI(client)
        price_feed = PriceFeedService(assets_api)
        logger.info("Initialized in ONLINE mode with live Mudrex prices")
    
    engine = PaperTradingEngine(
        initial_balance=balance,
        price_feed=price_feed,
        db_path=db_path,
    )
    
    logger.info(f"Paper trading engine ready. Balance: ${balance}")
    return engine


def format_decimal(value: Decimal) -> str:
    """Format Decimal for display."""
    return f"{value:.8f}".rstrip('0').rstrip('.')


# ============================================================================
# MCP Tool Handlers
# ============================================================================

async def handle_get_balance() -> dict:
    """Get current paper wallet balance."""
    if not engine:
        return {"error": "Engine not initialized"}
    
    wallet = engine.get_wallet()
    return {
        "balance": format_decimal(wallet.balance),
        "available": format_decimal(wallet.available_balance),
        "locked_margin": format_decimal(wallet.locked_margin),
        "unrealized_pnl": format_decimal(wallet.unrealized_pnl),
        "currency": "USDT",
    }


async def handle_get_price(symbol: str) -> dict:
    """Get current price for a symbol."""
    if not engine:
        return {"error": "Engine not initialized"}
    
    try:
        price = engine.price_feed.get_price(symbol.upper())
        return {
            "symbol": symbol.upper(),
            "price": format_decimal(price),
            "source": "mock" if is_offline else "live",
        }
    except Exception as e:
        return {"error": str(e)}


async def handle_place_market_order(
    symbol: str,
    side: str,
    quantity: str,
    leverage: int = 10,
    stoploss: Optional[str] = None,
    takeprofit: Optional[str] = None,
) -> dict:
    """Place a market order."""
    if not engine:
        return {"error": "Engine not initialized"}
    
    try:
        # Parse inputs
        sym = symbol.upper()
        order_side = OrderSide.LONG if side.upper() in ["LONG", "BUY"] else OrderSide.SHORT
        qty = Decimal(quantity)
        sl = Decimal(stoploss) if stoploss else None
        tp = Decimal(takeprofit) if takeprofit else None
        
        # Place order
        order = engine.create_market_order(
            symbol=sym,
            side=order_side,
            quantity=qty,
            leverage=leverage,
            stoploss_price=sl,
            takeprofit_price=tp,
        )
        
        return {
            "success": True,
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": format_decimal(order.quantity),
            "price": format_decimal(order.price) if order.price else None,
            "status": order.status.value,
            "leverage": leverage,
            "message": f"Opened {order.side.value} position: {qty} {sym} @ ${order.price}",
        }
        
    except InsufficientBalanceError as e:
        return {"success": False, "error": f"Insufficient balance: {e}"}
    except InvalidOrderError as e:
        return {"success": False, "error": f"Invalid order: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_place_limit_order(
    symbol: str,
    side: str,
    quantity: str,
    price: str,
    leverage: int = 10,
    stoploss: Optional[str] = None,
    takeprofit: Optional[str] = None,
) -> dict:
    """Place a limit order."""
    if not engine:
        return {"error": "Engine not initialized"}
    
    try:
        sym = symbol.upper()
        order_side = OrderSide.LONG if side.upper() in ["LONG", "BUY"] else OrderSide.SHORT
        qty = Decimal(quantity)
        limit_price = Decimal(price)
        sl = Decimal(stoploss) if stoploss else None
        tp = Decimal(takeprofit) if takeprofit else None
        
        order = engine.create_limit_order(
            symbol=sym,
            side=order_side,
            quantity=qty,
            price=limit_price,
            leverage=leverage,
            stoploss_price=sl,
            takeprofit_price=tp,
        )
        
        return {
            "success": True,
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": format_decimal(order.quantity),
            "limit_price": format_decimal(limit_price),
            "status": order.status.value,
            "message": f"Limit order placed: {order.side.value} {qty} {sym} @ ${limit_price}",
        }
        
    except InsufficientBalanceError as e:
        return {"success": False, "error": f"Insufficient balance: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_list_positions() -> dict:
    """List all open positions."""
    if not engine:
        return {"error": "Engine not initialized"}
    
    positions = engine.list_open_positions()
    
    if not positions:
        return {"positions": [], "message": "No open positions"}
    
    result = []
    for pos in positions:
        result.append({
            "position_id": pos.position_id,
            "symbol": pos.symbol,
            "side": pos.side.value,
            "quantity": format_decimal(pos.quantity),
            "entry_price": format_decimal(pos.entry_price),
            "current_price": format_decimal(pos.current_price) if pos.current_price else None,
            "unrealized_pnl": format_decimal(pos.unrealized_pnl),
            "roe_percent": f"{pos.roe_percent:.2f}%",
            "leverage": pos.leverage,
            "margin": format_decimal(pos.margin),
            "liquidation_price": format_decimal(pos.liquidation_price) if pos.liquidation_price else None,
            "stoploss": format_decimal(pos.stoploss_price) if pos.stoploss_price else None,
            "takeprofit": format_decimal(pos.takeprofit_price) if pos.takeprofit_price else None,
        })
    
    total_pnl = sum(Decimal(p["unrealized_pnl"]) for p in result)
    
    return {
        "positions": result,
        "count": len(result),
        "total_unrealized_pnl": format_decimal(total_pnl),
    }


async def handle_close_position(position_id: str) -> dict:
    """Close a specific position."""
    if not engine:
        return {"error": "Engine not initialized"}
    
    try:
        trade = engine.close_position(position_id)
        
        return {
            "success": True,
            "position_id": position_id,
            "realized_pnl": format_decimal(trade.realized_pnl),
            "close_price": format_decimal(trade.exit_price),
            "message": f"Position closed. Realized PnL: ${trade.realized_pnl}",
        }
        
    except PositionNotFoundError:
        return {"success": False, "error": f"Position not found: {position_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_close_all_positions() -> dict:
    """Close all open positions."""
    if not engine:
        return {"error": "Engine not initialized"}
    
    positions = engine.list_open_positions()
    
    if not positions:
        return {"success": True, "closed": 0, "message": "No positions to close"}
    
    closed = []
    total_pnl = Decimal("0")
    
    for pos in positions:
        try:
            trade = engine.close_position(pos.position_id)
            closed.append({
                "symbol": pos.symbol,
                "side": pos.side.value,
                "pnl": format_decimal(trade.realized_pnl),
            })
            total_pnl += trade.realized_pnl
        except Exception as e:
            closed.append({
                "symbol": pos.symbol,
                "error": str(e),
            })
    
    return {
        "success": True,
        "closed": len(closed),
        "total_realized_pnl": format_decimal(total_pnl),
        "details": closed,
        "message": f"Closed {len(closed)} positions. Total PnL: ${total_pnl}",
    }


async def handle_update_sltp(
    position_id: str,
    stoploss: Optional[str] = None,
    takeprofit: Optional[str] = None,
) -> dict:
    """Update stop-loss and/or take-profit for a position."""
    if not engine:
        return {"error": "Engine not initialized"}
    
    try:
        sl = Decimal(stoploss) if stoploss else None
        tp = Decimal(takeprofit) if takeprofit else None
        
        engine.update_position_sltp(
            position_id=position_id,
            stoploss_price=sl,
            takeprofit_price=tp,
        )
        
        return {
            "success": True,
            "position_id": position_id,
            "stoploss": stoploss,
            "takeprofit": takeprofit,
            "message": f"Updated SL/TP for position {position_id}",
        }
        
    except PositionNotFoundError:
        return {"success": False, "error": f"Position not found: {position_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_get_statistics() -> dict:
    """Get trading statistics."""
    if not engine:
        return {"error": "Engine not initialized"}
    
    stats = engine.get_statistics()
    return stats


async def handle_get_trade_history(limit: int = 20) -> dict:
    """Get recent trade history."""
    if not engine:
        return {"error": "Engine not initialized"}
    
    history = engine.get_trade_history()
    
    # Limit results
    history = history[-limit:] if len(history) > limit else history
    
    trades = []
    for trade in history:
        trades.append({
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "side": trade.side.value,
            "quantity": format_decimal(trade.quantity),
            "entry_price": format_decimal(trade.entry_price),
            "exit_price": format_decimal(trade.exit_price) if trade.exit_price else None,
            "realized_pnl": format_decimal(trade.realized_pnl) if trade.realized_pnl else None,
            "status": trade.status,
            "timestamp": trade.timestamp.isoformat() if trade.timestamp else None,
        })
    
    return {
        "trades": trades,
        "count": len(trades),
    }


async def handle_reset_account(new_balance: str = "10000") -> dict:
    """Reset paper trading account to fresh state."""
    if not engine:
        return {"error": "Engine not initialized"}
    
    try:
        balance = Decimal(new_balance)
        engine.reset(new_balance=balance)
        
        return {
            "success": True,
            "new_balance": format_decimal(balance),
            "message": f"Account reset to ${balance}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_set_mock_price(symbol: str, price: str) -> dict:
    """Set mock price for a symbol (offline mode only)."""
    if not is_offline:
        return {"error": "set_mock_price only available in offline mode"}
    
    if not price_feed or not isinstance(price_feed, MockPriceFeedService):
        return {"error": "Mock price feed not available"}
    
    try:
        sym = symbol.upper()
        p = Decimal(price)
        price_feed.set_price(sym, p)
        
        return {
            "success": True,
            "symbol": sym,
            "price": format_decimal(p),
            "message": f"Set {sym} price to ${p}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_get_funding_info(symbol: str) -> dict:
    """Get funding rate information for a symbol."""
    if is_offline:
        return {
            "symbol": symbol.upper(),
            "funding_rate": "0.0001",
            "funding_rate_percent": "0.01%",
            "next_funding_time": "N/A (offline mode)",
            "note": "Funding rates not available in offline mode",
        }
    
    try:
        from mudrex.paper.external_data import ExternalDataService
        external = ExternalDataService()
        info = external.get_funding_info(symbol.upper())
        
        return {
            "symbol": info.symbol,
            "funding_rate": format_decimal(info.funding_rate),
            "funding_rate_percent": f"{info.funding_rate * 100:.4f}%",
            "next_funding_time": info.next_funding_time.isoformat(),
            "mark_price": format_decimal(info.mark_price),
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# MCP Server Setup
# ============================================================================

def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("mudrex-paper-trading")
    
    # Define tools
    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="get_balance",
                description="Get current paper wallet balance including available balance, locked margin, and unrealized PnL",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="get_price",
                description="Get current price for a trading symbol (e.g., BTCUSDT, ETHUSDT)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Trading pair symbol (e.g., BTCUSDT)",
                        },
                    },
                    "required": ["symbol"],
                },
            ),
            Tool(
                name="place_market_order",
                description="Place a market order to open a LONG or SHORT position. Use LONG to profit from price increase, SHORT to profit from price decrease.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Trading pair (e.g., BTCUSDT)",
                        },
                        "side": {
                            "type": "string",
                            "enum": ["LONG", "SHORT"],
                            "description": "LONG (buy) or SHORT (sell)",
                        },
                        "quantity": {
                            "type": "string",
                            "description": "Amount to trade (e.g., '0.01' for 0.01 BTC)",
                        },
                        "leverage": {
                            "type": "integer",
                            "description": "Leverage multiplier (default: 10)",
                            "default": 10,
                        },
                        "stoploss": {
                            "type": "string",
                            "description": "Stop-loss price (optional)",
                        },
                        "takeprofit": {
                            "type": "string",
                            "description": "Take-profit price (optional)",
                        },
                    },
                    "required": ["symbol", "side", "quantity"],
                },
            ),
            Tool(
                name="place_limit_order",
                description="Place a limit order at a specific price",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Trading pair (e.g., BTCUSDT)",
                        },
                        "side": {
                            "type": "string",
                            "enum": ["LONG", "SHORT"],
                            "description": "LONG or SHORT",
                        },
                        "quantity": {
                            "type": "string",
                            "description": "Amount to trade",
                        },
                        "price": {
                            "type": "string",
                            "description": "Limit price",
                        },
                        "leverage": {
                            "type": "integer",
                            "default": 10,
                        },
                        "stoploss": {"type": "string"},
                        "takeprofit": {"type": "string"},
                    },
                    "required": ["symbol", "side", "quantity", "price"],
                },
            ),
            Tool(
                name="list_positions",
                description="List all open positions with current PnL, entry price, and other details",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="close_position",
                description="Close a specific position by its ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "position_id": {
                            "type": "string",
                            "description": "The position ID to close",
                        },
                    },
                    "required": ["position_id"],
                },
            ),
            Tool(
                name="close_all_positions",
                description="Close all open positions at once",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="update_sltp",
                description="Update stop-loss and/or take-profit for an existing position",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "position_id": {
                            "type": "string",
                            "description": "Position ID",
                        },
                        "stoploss": {
                            "type": "string",
                            "description": "New stop-loss price",
                        },
                        "takeprofit": {
                            "type": "string",
                            "description": "New take-profit price",
                        },
                    },
                    "required": ["position_id"],
                },
            ),
            Tool(
                name="get_statistics",
                description="Get trading statistics: total trades, win rate, total PnL, fees paid, etc.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="get_trade_history",
                description="Get recent trade history",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Max trades to return (default: 20)",
                            "default": 20,
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="reset_account",
                description="Reset paper trading account to a fresh state with a new balance",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "new_balance": {
                            "type": "string",
                            "description": "New starting balance (default: 10000)",
                            "default": "10000",
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="set_mock_price",
                description="Set price for a symbol (offline mode only). Use this to simulate price movements.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Trading pair (e.g., BTCUSDT)",
                        },
                        "price": {
                            "type": "string",
                            "description": "New price",
                        },
                    },
                    "required": ["symbol", "price"],
                },
            ),
            Tool(
                name="get_funding_info",
                description="Get funding rate information for a symbol",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Trading pair (e.g., BTCUSDT)",
                        },
                    },
                    "required": ["symbol"],
                },
            ),
        ]
    
    # Handle tool calls
    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        logger.info(f"Tool called: {name} with args: {arguments}")
        
        try:
            if name == "get_balance":
                result = await handle_get_balance()
            elif name == "get_price":
                result = await handle_get_price(arguments["symbol"])
            elif name == "place_market_order":
                result = await handle_place_market_order(
                    symbol=arguments["symbol"],
                    side=arguments["side"],
                    quantity=arguments["quantity"],
                    leverage=arguments.get("leverage", 10),
                    stoploss=arguments.get("stoploss"),
                    takeprofit=arguments.get("takeprofit"),
                )
            elif name == "place_limit_order":
                result = await handle_place_limit_order(
                    symbol=arguments["symbol"],
                    side=arguments["side"],
                    quantity=arguments["quantity"],
                    price=arguments["price"],
                    leverage=arguments.get("leverage", 10),
                    stoploss=arguments.get("stoploss"),
                    takeprofit=arguments.get("takeprofit"),
                )
            elif name == "list_positions":
                result = await handle_list_positions()
            elif name == "close_position":
                result = await handle_close_position(arguments["position_id"])
            elif name == "close_all_positions":
                result = await handle_close_all_positions()
            elif name == "update_sltp":
                result = await handle_update_sltp(
                    position_id=arguments["position_id"],
                    stoploss=arguments.get("stoploss"),
                    takeprofit=arguments.get("takeprofit"),
                )
            elif name == "get_statistics":
                result = await handle_get_statistics()
            elif name == "get_trade_history":
                result = await handle_get_trade_history(arguments.get("limit", 20))
            elif name == "reset_account":
                result = await handle_reset_account(arguments.get("new_balance", "10000"))
            elif name == "set_mock_price":
                result = await handle_set_mock_price(
                    symbol=arguments["symbol"],
                    price=arguments["price"],
                )
            elif name == "get_funding_info":
                result = await handle_get_funding_info(arguments["symbol"])
            else:
                result = {"error": f"Unknown tool: {name}"}
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            logger.error(f"Error in tool {name}: {e}")
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    return server


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Mudrex Paper Trading MCP Server")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run in offline mode with mock prices (no API key needed)",
    )
    parser.add_argument(
        "--api-secret",
        type=str,
        help="Mudrex API secret (required for online mode)",
    )
    parser.add_argument(
        "--balance",
        type=str,
        default="10000",
        help="Initial paper trading balance (default: 10000)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="Path to SQLite database for persistence",
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.offline and not args.api_secret:
        print("ERROR: Either --offline or --api-secret is required")
        print("  Online mode: python -m mudrex.mcp_server --api-secret YOUR_SECRET")
        print("  Offline mode: python -m mudrex.mcp_server --offline")
        exit(1)
    
    # Initialize engine
    init_engine(
        offline=args.offline,
        api_secret=args.api_secret,
        initial_balance=args.balance,
        db_path=args.db_path,
    )
    
    # Create and run server
    server = create_server()
    
    logger.info("Starting Mudrex Paper Trading MCP Server...")
    logger.info(f"Mode: {'OFFLINE' if args.offline else 'ONLINE'}")
    logger.info(f"Balance: ${args.balance}")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
