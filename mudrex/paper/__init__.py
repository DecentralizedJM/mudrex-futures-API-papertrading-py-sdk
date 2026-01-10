"""
Mudrex Paper Trading Module
===========================

Simulated futures trading using real Mudrex market prices.
No real orders are placed - perfect for strategy testing and learning.

Quick Start:
    >>> from mudrex import MudrexClient
    >>> 
    >>> # Create a paper trading client
    >>> client = MudrexClient(
    ...     api_secret="your-api-secret",  # Still needed for price feeds
    ...     mode="paper",
    ...     paper_balance="10000"  # Start with $10,000
    ... )
    >>> 
    >>> # Trade exactly like live mode!
    >>> order = client.orders.create_market_order(
    ...     symbol="BTCUSDT",
    ...     side="LONG",
    ...     quantity="0.01",
    ...     leverage="10",
    ...     stoploss_price="95000",
    ...     takeprofit_price="110000"
    ... )
    >>> 
    >>> # Check positions
    >>> for pos in client.positions.list_open():
    ...     print(f"{pos.symbol}: {pos.unrealized_pnl} PnL")

Features:
    - Market and limit orders
    - LONG/SHORT positions with leverage
    - Stop-loss and take-profit auto-execution
    - Realistic margin and fee calculations
    - State persistence across restarts
    - Real-time PnL using live Mudrex prices

For more information, see the paper trading documentation.
"""

# Core engine
from mudrex.paper.engine import PaperTradingEngine

# Data models
from mudrex.paper.models import (
    PaperWallet,
    PaperOrder,
    PaperPosition,
    TradeRecord,
    PaperOrderStatus,
    PaperPositionStatus,
    CloseReason,
)

# Exceptions
from mudrex.paper.exceptions import (
    PaperTradingError,
    InsufficientMarginError,
    InvalidOrderError,
    PositionNotFoundError,
    OrderNotFoundError,
    SymbolNotFoundError,
    PositionAlreadyClosedError,
    OrderAlreadyFilledError,
    LiquidationWarning,
    PriceFetchError,
)

# Price feed
from mudrex.paper.price_feed import (
    PriceFeedService,
    MockPriceFeedService,
)

# Monitoring
from mudrex.paper.sltp_monitor import (
    SLTPMonitor,
    ManualTriggerChecker,
)

# Persistence
from mudrex.paper.persistence import (
    PaperDB,
    InMemoryPaperDB,
)

# API wrappers
from mudrex.paper.api import (
    PaperOrdersAPI,
    PaperPositionsAPI,
    PaperWalletAPI,
    PaperLeverageAPI,
    PaperFeesAPI,
)


__all__ = [
    # Engine
    "PaperTradingEngine",
    
    # Models
    "PaperWallet",
    "PaperOrder",
    "PaperPosition",
    "TradeRecord",
    "PaperOrderStatus",
    "PaperPositionStatus",
    "CloseReason",
    
    # Exceptions
    "PaperTradingError",
    "InsufficientMarginError",
    "InvalidOrderError",
    "PositionNotFoundError",
    "OrderNotFoundError",
    "SymbolNotFoundError",
    "PositionAlreadyClosedError",
    "OrderAlreadyFilledError",
    "LiquidationWarning",
    "PriceFetchError",
    
    # Price feed
    "PriceFeedService",
    "MockPriceFeedService",
    
    # Monitoring
    "SLTPMonitor",
    "ManualTriggerChecker",
    
    # Persistence
    "PaperDB",
    "InMemoryPaperDB",
    
    # API wrappers
    "PaperOrdersAPI",
    "PaperPositionsAPI",
    "PaperWalletAPI",
    "PaperLeverageAPI",
    "PaperFeesAPI",
]
