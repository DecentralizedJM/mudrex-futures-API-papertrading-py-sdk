"""
Mudrex API Data Models
======================

Pydantic models for type-safe API interactions.
All numeric values are strings to preserve precision (as per API spec).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


# ============================================================================
# Enums
# ============================================================================

class OrderType(str, Enum):
    """Order direction - LONG (buy) or SHORT (sell)."""
    LONG = "LONG"
    SHORT = "SHORT"


class TriggerType(str, Enum):
    """Order execution type - MARKET or LIMIT."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class MarginType(str, Enum):
    """Margin type for futures positions."""
    ISOLATED = "ISOLATED"
    # CROSS = "CROSS"  # May be added in future


class OrderStatus(str, Enum):
    """Order status values."""
    CREATED = "CREATED"  # Order created (async processing)
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class PositionStatus(str, Enum):
    """Position status values."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    LIQUIDATED = "LIQUIDATED"


class WalletType(str, Enum):
    """Wallet types for transfers."""
    SPOT = "SPOT"
    FUTURES = "FUTURES"


# ============================================================================
# Wallet Models
# ============================================================================

@dataclass
class WalletBalance:
    """Spot wallet balance information.
    
    Fields match API response from /wallet/funds (POST).
    """
    total: str
    withdrawable: str
    invested: str = "0"
    rewards: str = "0"
    coin_investable: str = "0"
    coinset_investable: str = "0"
    vault_investable: str = "0"
    
    @property
    def available(self) -> str:
        """Alias for withdrawable (backwards compatibility)."""
        return self.withdrawable
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WalletBalance":
        return cls(
            total=str(data.get("total", "0")),
            withdrawable=str(data.get("withdrawable", "0")),
            invested=str(data.get("invested", "0")),
            rewards=str(data.get("rewards", "0")),
            coin_investable=str(data.get("coin_investable", "0")),
            coinset_investable=str(data.get("coinset_investable", "0")),
            vault_investable=str(data.get("vault_investable", "0")),
        )
    
    def __repr__(self) -> str:
        return f"WalletBalance(total={self.total}, withdrawable={self.withdrawable}, invested={self.invested})"


@dataclass
class FuturesBalance:
    """Futures wallet balance information.
    
    Fields match API response from /futures/funds (GET).
    """
    balance: str
    locked_amount: str = "0"
    first_time_user: bool = False
    
    @property
    def available(self) -> str:
        """Available balance (balance - locked_amount)."""
        try:
            return str(float(self.balance) - float(self.locked_amount))
        except (ValueError, TypeError):
            return self.balance
    
    @property
    def available_transfer(self) -> str:
        """Alias for available (backwards compatibility)."""
        return self.available
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FuturesBalance":
        return cls(
            balance=str(data.get("balance", "0")),
            locked_amount=str(data.get("locked_amount", "0")),
            first_time_user=data.get("first_time_user", False),
        )
    
    def __repr__(self) -> str:
        return f"FuturesBalance(balance={self.balance}, locked={self.locked_amount}, available={self.available})"


@dataclass
class TransferResult:
    """Result of a wallet transfer operation."""
    success: bool
    from_wallet: WalletType
    to_wallet: WalletType
    amount: str
    transaction_id: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransferResult":
        return cls(
            success=data.get("success", False),
            from_wallet=WalletType(data.get("from_wallet_type", "SPOT")),
            to_wallet=WalletType(data.get("to_wallet_type", "FUTURES")),
            amount=str(data.get("amount", "0")),
            transaction_id=data.get("transaction_id"),
        )


# ============================================================================
# Asset Models
# ============================================================================

@dataclass
class Asset:
    """Futures trading instrument/asset details."""
    asset_id: str
    symbol: str
    base_currency: str
    quote_currency: str
    min_quantity: str
    max_quantity: str
    quantity_step: str
    min_leverage: str
    max_leverage: str
    maker_fee: str
    taker_fee: str
    is_active: bool = True
    # Price precision fields (for order rounding)
    price_step: Optional[str] = None  # Tick size for price rounding
    min_price: Optional[str] = None
    max_price: Optional[str] = None
    # Current market data
    price: Optional[str] = None  # Current price
    name: Optional[str] = None  # Asset display name (e.g., "Bitcoin")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Asset":
        return cls(
            asset_id=data.get("asset_id", data.get("id", "")),
            symbol=data.get("symbol", ""),
            base_currency=data.get("base_currency", ""),
            quote_currency=data.get("quote_currency", "USDT"),
            min_quantity=str(data.get("min_quantity", data.get("min_contract", "0"))),
            max_quantity=str(data.get("max_quantity", data.get("max_contract", "0"))),
            quantity_step=str(data.get("quantity_step", "0")),
            min_leverage=str(data.get("min_leverage", "1")),
            max_leverage=str(data.get("max_leverage", "100")),
            maker_fee=str(data.get("maker_fee", "0")),
            taker_fee=str(data.get("taker_fee", data.get("trading_fee_perc", "0"))),
            is_active=data.get("is_active", True),
            # Price precision fields
            price_step=data.get("price_step"),
            min_price=data.get("min_price"),
            max_price=data.get("max_price"),
            # Market data
            price=data.get("price"),
            name=data.get("name"),
        )


@dataclass  
class Leverage:
    """Current leverage settings for an asset."""
    asset_id: str
    leverage: str
    margin_type: MarginType
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Leverage":
        return cls(
            asset_id=data.get("asset_id", ""),
            leverage=str(data.get("leverage", "1")),
            margin_type=MarginType(data.get("margin_type", "ISOLATED")),
        )


# ============================================================================
# Order Models
# ============================================================================

@dataclass
class OrderRequest:
    """Request parameters for creating a new order."""
    quantity: str
    order_type: OrderType
    trigger_type: TriggerType
    leverage: str = "1"
    order_price: Optional[str] = None  # Required for LIMIT orders
    is_stoploss: bool = False
    stoploss_price: Optional[str] = None
    is_takeprofit: bool = False
    takeprofit_price: Optional[str] = None
    reduce_only: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API request format with numeric types."""
        data = {
            "leverage": float(self.leverage),  # API requires number, not string
            "quantity": float(self.quantity),  # API requires number, not string
            "order_type": self.order_type.value,
            "trigger_type": self.trigger_type.value,
            "reduce_only": self.reduce_only,
        }
        
        if self.order_price:
            data["order_price"] = float(self.order_price)  # API requires number, not string
            
        if self.is_stoploss and self.stoploss_price:
            data["is_stoploss"] = True
            data["stoploss_price"] = float(self.stoploss_price)  # API requires number
            
        if self.is_takeprofit and self.takeprofit_price:
            data["is_takeprofit"] = True
            data["takeprofit_price"] = float(self.takeprofit_price)  # API requires number
            
        return data


@dataclass
class Order:
    """Represents a futures order."""
    order_id: str
    asset_id: str
    symbol: str
    order_type: OrderType
    trigger_type: TriggerType
    status: OrderStatus
    quantity: str
    filled_quantity: str
    price: str
    leverage: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    stoploss_price: Optional[str] = None
    takeprofit_price: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Order":
        return cls(
            order_id=data.get("order_id", data.get("id", "")),
            asset_id=data.get("asset_id", ""),
            symbol=data.get("symbol", ""),
            order_type=OrderType(data.get("order_type", "LONG")),
            trigger_type=TriggerType(data.get("trigger_type", "MARKET")),
            status=OrderStatus(data.get("status", "OPEN")),
            quantity=str(data.get("quantity", "0")),
            filled_quantity=str(data.get("filled_quantity", "0")),
            price=str(data.get("price", data.get("order_price", "0"))),
            leverage=str(data.get("leverage", "1")),
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
            stoploss_price=data.get("stoploss_price"),
            takeprofit_price=data.get("takeprofit_price"),
        )


# ============================================================================
# Position Models
# ============================================================================

@dataclass
class Position:
    """Represents an open or closed futures position."""
    position_id: str
    asset_id: str
    symbol: str
    side: OrderType
    quantity: str
    entry_price: str
    mark_price: str
    leverage: str
    margin: str
    unrealized_pnl: str
    realized_pnl: str
    liquidation_price: Optional[str] = None
    stoploss_price: Optional[str] = None
    takeprofit_price: Optional[str] = None
    status: PositionStatus = PositionStatus.OPEN
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Position":
        # Extract stoploss_price from nested structure (API format) or flat field (legacy)
        # API returns: {"stoploss": {"price": "4100", "order_id": "...", "order_type": "SHORT"}}
        stoploss_data = data.get("stoploss")
        if isinstance(stoploss_data, dict):
            stoploss_price = stoploss_data.get("price")
        else:
            stoploss_price = data.get("stoploss_price")
        
        # Extract takeprofit_price from nested structure (API format) or flat field (legacy)
        # API returns: {"takeprofit": {"price": "5000", "order_id": "...", "order_type": "SHORT"}}
        takeprofit_data = data.get("takeprofit")
        if isinstance(takeprofit_data, dict):
            takeprofit_price = takeprofit_data.get("price")
        else:
            takeprofit_price = data.get("takeprofit_price")
        
        return cls(
            position_id=data.get("position_id", data.get("id", "")),
            asset_id=data.get("asset_id", ""),
            symbol=data.get("symbol", ""),
            side=OrderType(data.get("side", data.get("order_type", "LONG"))),
            quantity=str(data.get("quantity", "0")),
            entry_price=str(data.get("entry_price", "0")),
            mark_price=str(data.get("mark_price", "0")),
            leverage=str(data.get("leverage", "1")),
            margin=str(data.get("margin", "0")),
            unrealized_pnl=str(data.get("unrealized_pnl", "0")),
            realized_pnl=str(data.get("realized_pnl", "0")),
            liquidation_price=data.get("liquidation_price"),
            stoploss_price=stoploss_price,
            takeprofit_price=takeprofit_price,
            status=PositionStatus(data.get("status", "OPEN")),
            created_at=_parse_datetime(data.get("created_at")),
        )
    
    @property
    def pnl_percentage(self) -> float:
        """Calculate PnL as percentage of margin."""
        try:
            margin = float(self.margin)
            pnl = float(self.unrealized_pnl)
            if margin > 0:
                return (pnl / margin) * 100
        except (ValueError, ZeroDivisionError):
            pass
        return 0.0


@dataclass
class RiskOrder:
    """Stop-loss and take-profit settings for a position."""
    position_id: str
    stoploss_price: Optional[str] = None
    takeprofit_price: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = {"order_source": "API"}
        if self.stoploss_price:
            data["stoploss_price"] = self.stoploss_price
            data["is_stoploss"] = True
        if self.takeprofit_price:
            data["takeprofit_price"] = self.takeprofit_price
            data["is_takeprofit"] = True
        return data


# ============================================================================
# Fee Models
# ============================================================================

@dataclass
class FeeRecord:
    """A single fee transaction record."""
    fee_id: str
    asset_id: str
    symbol: str
    fee_amount: str
    fee_type: str
    order_id: Optional[str] = None
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeeRecord":
        return cls(
            fee_id=data.get("fee_id", data.get("id", "")),
            asset_id=data.get("asset_id", ""),
            symbol=data.get("symbol", ""),
            fee_amount=str(data.get("fee_amount", "0")),
            fee_type=data.get("fee_type", "TRADING"),
            order_id=data.get("order_id"),
            created_at=_parse_datetime(data.get("created_at")),
        )


# ============================================================================
# Pagination
# ============================================================================

@dataclass
class PaginatedResponse:
    """Wrapper for paginated API responses."""
    items: List[Any]
    page: int
    per_page: int
    total: int
    has_more: bool
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], item_class: type) -> "PaginatedResponse":
        items = [item_class.from_dict(item) for item in data.get("items", data.get("data", []))]
        return cls(
            items=items,
            page=data.get("page", 1),
            per_page=data.get("per_page", len(items)),
            total=data.get("total", len(items)),
            has_more=data.get("has_more", False),
        )


# ============================================================================
# Helpers
# ============================================================================

def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse datetime from various formats."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        # Unix timestamp (seconds or milliseconds)
        if value > 1e12:  # Milliseconds
            value = value / 1000
        return datetime.fromtimestamp(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return None
