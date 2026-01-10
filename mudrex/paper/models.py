"""
Paper Trading Data Models
=========================

Data models for simulated paper trading.
All numeric values use Decimal for precision.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
import uuid


class PaperOrderStatus(str, Enum):
    """Status of a paper order."""
    PENDING = "PENDING"      # Limit order waiting to fill
    FILLED = "FILLED"        # Order executed
    CANCELLED = "CANCELLED"  # Cancelled by user
    EXPIRED = "EXPIRED"      # Limit order expired (24h)
    REJECTED = "REJECTED"    # Failed validation


class PaperPositionStatus(str, Enum):
    """Status of a paper position."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class CloseReason(str, Enum):
    """Reason for position closure."""
    MANUAL = "MANUAL"
    STOPLOSS = "STOPLOSS"
    TAKEPROFIT = "TAKEPROFIT"
    LIQUIDATION = "LIQUIDATION"  # Warning only in V1


def generate_paper_id(prefix: str) -> str:
    """Generate a unique paper trading ID."""
    return f"paper_{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class PaperWallet:
    """
    Virtual wallet for paper trading.
    
    Invariants:
    - balance = available + locked_margin
    - available >= 0 (cannot go negative)
    """
    balance: Decimal = Decimal("10000")          # Total balance
    available: Decimal = Decimal("10000")        # Available for new trades
    locked_margin: Decimal = Decimal("0")        # Margin in open positions
    unrealized_pnl: Decimal = Decimal("0")       # Sum of position unrealized PnL
    realized_pnl: Decimal = Decimal("0")         # Cumulative realized PnL
    total_fees_paid: Decimal = Decimal("0")      # Total trading fees paid
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def lock_margin(self, amount: Decimal) -> None:
        """Lock margin for a new position."""
        if amount > self.available:
            raise ValueError(f"Cannot lock {amount}, only {self.available} available")
        self.available -= amount
        self.locked_margin += amount
        self.updated_at = datetime.utcnow()
    
    def release_margin(self, amount: Decimal) -> None:
        """Release margin when position closes."""
        self.locked_margin -= amount
        self.available += amount
        self.updated_at = datetime.utcnow()
    
    def realize_pnl(self, pnl: Decimal, released_margin: Decimal) -> None:
        """Record realized PnL and release margin."""
        self.realized_pnl += pnl
        self.locked_margin -= released_margin
        self.available += released_margin + pnl
        self.balance += pnl
        self.updated_at = datetime.utcnow()
    
    def deduct_fee(self, fee: Decimal) -> None:
        """Deduct trading fee from available balance."""
        self.available -= fee
        self.balance -= fee
        self.total_fees_paid += fee
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "balance": str(self.balance),
            "available": str(self.available),
            "locked_margin": str(self.locked_margin),
            "unrealized_pnl": str(self.unrealized_pnl),
            "realized_pnl": str(self.realized_pnl),
            "total_fees_paid": str(self.total_fees_paid),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaperWallet":
        """Create from dictionary."""
        return cls(
            balance=Decimal(data["balance"]),
            available=Decimal(data["available"]),
            locked_margin=Decimal(data["locked_margin"]),
            unrealized_pnl=Decimal(data.get("unrealized_pnl", "0")),
            realized_pnl=Decimal(data.get("realized_pnl", "0")),
            total_fees_paid=Decimal(data.get("total_fees_paid", "0")),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data["updated_at"], str) else data["updated_at"],
        )


@dataclass
class PaperOrder:
    """
    Simulated order record.
    
    Mirrors the real Order model structure for SDK compatibility.
    """
    order_id: str
    symbol: str
    side: str                           # "LONG" or "SHORT"
    order_type: str                     # "MARKET" or "LIMIT"
    quantity: Decimal
    leverage: int
    status: PaperOrderStatus
    
    # Pricing
    price: Optional[Decimal] = None     # Limit price (None for market)
    filled_price: Optional[Decimal] = None  # Actual execution price
    
    # Risk management
    stoploss_price: Optional[Decimal] = None
    takeprofit_price: Optional[Decimal] = None
    reduce_only: bool = False
    
    # Costs
    fee_paid: Decimal = Decimal("0")
    margin_used: Decimal = Decimal("0")
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None  # For limit orders
    
    # Links
    position_id: Optional[str] = None
    
    def fill(self, price: Decimal, position_id: str) -> None:
        """Mark order as filled."""
        self.status = PaperOrderStatus.FILLED
        self.filled_price = price
        self.filled_at = datetime.utcnow()
        self.position_id = position_id
    
    def cancel(self) -> None:
        """Cancel the order."""
        self.status = PaperOrderStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
    
    @property
    def notional_value(self) -> Decimal:
        """Calculate notional value using filled or limit price."""
        price = self.filled_price or self.price or Decimal("0")
        return self.quantity * price
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "quantity": str(self.quantity),
            "leverage": self.leverage,
            "status": self.status.value,
            "price": str(self.price) if self.price else None,
            "filled_price": str(self.filled_price) if self.filled_price else None,
            "stoploss_price": str(self.stoploss_price) if self.stoploss_price else None,
            "takeprofit_price": str(self.takeprofit_price) if self.takeprofit_price else None,
            "reduce_only": self.reduce_only,
            "fee_paid": str(self.fee_paid),
            "margin_used": str(self.margin_used),
            "created_at": self.created_at.isoformat(),
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "position_id": self.position_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaperOrder":
        """Create from dictionary."""
        def parse_dt(val):
            if val is None:
                return None
            return datetime.fromisoformat(val) if isinstance(val, str) else val
        
        return cls(
            order_id=data["order_id"],
            symbol=data["symbol"],
            side=data["side"],
            order_type=data["order_type"],
            quantity=Decimal(data["quantity"]),
            leverage=int(data["leverage"]),
            status=PaperOrderStatus(data["status"]),
            price=Decimal(data["price"]) if data.get("price") else None,
            filled_price=Decimal(data["filled_price"]) if data.get("filled_price") else None,
            stoploss_price=Decimal(data["stoploss_price"]) if data.get("stoploss_price") else None,
            takeprofit_price=Decimal(data["takeprofit_price"]) if data.get("takeprofit_price") else None,
            reduce_only=data.get("reduce_only", False),
            fee_paid=Decimal(data.get("fee_paid", "0")),
            margin_used=Decimal(data.get("margin_used", "0")),
            created_at=parse_dt(data["created_at"]) or datetime.utcnow(),
            filled_at=parse_dt(data.get("filled_at")),
            cancelled_at=parse_dt(data.get("cancelled_at")),
            expires_at=parse_dt(data.get("expires_at")),
            position_id=data.get("position_id"),
        )
    
    def to_sdk_order(self) -> Dict[str, Any]:
        """Convert to format matching SDK Order model."""
        return {
            "order_id": self.order_id,
            "id": self.order_id,
            "asset_id": self.symbol,
            "symbol": self.symbol,
            "order_type": self.side,  # SDK uses order_type for LONG/SHORT
            "trigger_type": self.order_type,  # SDK uses trigger_type for MARKET/LIMIT
            "status": self.status.value,
            "quantity": str(self.quantity),
            "filled_quantity": str(self.quantity) if self.status == PaperOrderStatus.FILLED else "0",
            "price": str(self.filled_price or self.price or "0"),
            "order_price": str(self.filled_price or self.price or "0"),
            "leverage": str(self.leverage),
            "created_at": self.created_at.isoformat(),
            "updated_at": (self.filled_at or self.created_at).isoformat(),
            "stoploss_price": str(self.stoploss_price) if self.stoploss_price else None,
            "takeprofit_price": str(self.takeprofit_price) if self.takeprofit_price else None,
        }


@dataclass
class PaperPosition:
    """
    Simulated futures position.
    
    Mirrors the real Position model structure for SDK compatibility.
    """
    position_id: str
    symbol: str
    side: str                           # "LONG" or "SHORT"
    status: PaperPositionStatus
    
    # Size & Entry
    quantity: Decimal
    entry_price: Decimal
    leverage: int
    
    # Margin & PnL
    margin: Decimal                     # Locked margin
    unrealized_pnl: Decimal = Decimal("0")  # Updated on price changes
    realized_pnl: Decimal = Decimal("0")    # Accumulated from partial closes
    
    # Risk Management
    stoploss_price: Optional[Decimal] = None
    takeprofit_price: Optional[Decimal] = None
    liquidation_price: Optional[Decimal] = None  # Estimated, warning only
    
    # Timestamps
    opened_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Close info
    close_reason: Optional[CloseReason] = None
    exit_price: Optional[Decimal] = None
    
    @property
    def notional_value(self) -> Decimal:
        """Current notional value based on entry price."""
        return self.quantity * self.entry_price
    
    @property
    def roe_percent(self) -> Decimal:
        """Return on Equity (PnL / Margin) * 100."""
        if self.margin == 0:
            return Decimal("0")
        return (self.unrealized_pnl / self.margin) * 100
    
    @property
    def pnl_percentage(self) -> float:
        """PnL as percentage of entry value."""
        if self.notional_value == 0:
            return 0.0
        return float((self.unrealized_pnl / self.notional_value) * 100)
    
    def calculate_unrealized_pnl(self, current_price: Decimal) -> Decimal:
        """Calculate unrealized PnL based on current market price."""
        price_diff = current_price - self.entry_price
        
        if self.side == "LONG":
            pnl = price_diff * self.quantity
        else:  # SHORT
            pnl = -price_diff * self.quantity
        
        return pnl
    
    def update_pnl(self, current_price: Decimal) -> None:
        """Update unrealized PnL with current price."""
        self.unrealized_pnl = self.calculate_unrealized_pnl(current_price)
        self.updated_at = datetime.utcnow()
    
    def calculate_liquidation_price(self) -> Optional[Decimal]:
        """
        Estimate liquidation price (simplified).
        
        Liquidation occurs when losses exceed margin.
        For LONG: entry_price - (margin / quantity) * safety_factor
        For SHORT: entry_price + (margin / quantity) * safety_factor
        """
        if self.quantity == 0:
            return None
        
        safety_factor = Decimal("0.9")  # 90% of margin triggers liquidation warning
        margin_per_unit = self.margin / self.quantity
        
        if self.side == "LONG":
            return self.entry_price - (margin_per_unit * safety_factor)
        else:
            return self.entry_price + (margin_per_unit * safety_factor)
    
    def close(self, exit_price: Decimal, reason: CloseReason) -> Decimal:
        """
        Close the position and calculate realized PnL.
        
        Returns: realized PnL for this close
        """
        final_pnl = self.calculate_unrealized_pnl(exit_price)
        
        self.status = PaperPositionStatus.CLOSED
        self.closed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.close_reason = reason
        self.exit_price = exit_price
        self.realized_pnl = final_pnl
        self.unrealized_pnl = Decimal("0")
        
        return final_pnl
    
    def partial_close(self, close_quantity: Decimal, exit_price: Decimal) -> Decimal:
        """
        Partially close the position.
        
        Returns: realized PnL for the closed portion
        """
        if close_quantity > self.quantity:
            raise ValueError(f"Cannot close {close_quantity}, only {self.quantity} in position")
        
        # Calculate PnL for closed portion
        ratio = close_quantity / self.quantity
        partial_pnl = self.calculate_unrealized_pnl(exit_price) * ratio
        
        # Update position
        self.quantity -= close_quantity
        self.margin *= (1 - ratio)
        self.realized_pnl += partial_pnl
        self.updated_at = datetime.utcnow()
        
        # Fully closed
        if self.quantity == 0:
            self.status = PaperPositionStatus.CLOSED
            self.closed_at = datetime.utcnow()
            self.close_reason = CloseReason.MANUAL
            self.exit_price = exit_price
        
        return partial_pnl
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "side": self.side,
            "status": self.status.value,
            "quantity": str(self.quantity),
            "entry_price": str(self.entry_price),
            "leverage": self.leverage,
            "margin": str(self.margin),
            "unrealized_pnl": str(self.unrealized_pnl),
            "realized_pnl": str(self.realized_pnl),
            "stoploss_price": str(self.stoploss_price) if self.stoploss_price else None,
            "takeprofit_price": str(self.takeprofit_price) if self.takeprofit_price else None,
            "liquidation_price": str(self.liquidation_price) if self.liquidation_price else None,
            "opened_at": self.opened_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "updated_at": self.updated_at.isoformat(),
            "close_reason": self.close_reason.value if self.close_reason else None,
            "exit_price": str(self.exit_price) if self.exit_price else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaperPosition":
        """Create from dictionary."""
        def parse_dt(val):
            if val is None:
                return None
            return datetime.fromisoformat(val) if isinstance(val, str) else val
        
        return cls(
            position_id=data["position_id"],
            symbol=data["symbol"],
            side=data["side"],
            status=PaperPositionStatus(data["status"]),
            quantity=Decimal(data["quantity"]),
            entry_price=Decimal(data["entry_price"]),
            leverage=int(data["leverage"]),
            margin=Decimal(data["margin"]),
            unrealized_pnl=Decimal(data.get("unrealized_pnl", "0")),
            realized_pnl=Decimal(data.get("realized_pnl", "0")),
            stoploss_price=Decimal(data["stoploss_price"]) if data.get("stoploss_price") else None,
            takeprofit_price=Decimal(data["takeprofit_price"]) if data.get("takeprofit_price") else None,
            liquidation_price=Decimal(data["liquidation_price"]) if data.get("liquidation_price") else None,
            opened_at=parse_dt(data["opened_at"]) or datetime.utcnow(),
            closed_at=parse_dt(data.get("closed_at")),
            updated_at=parse_dt(data.get("updated_at")) or datetime.utcnow(),
            close_reason=CloseReason(data["close_reason"]) if data.get("close_reason") else None,
            exit_price=Decimal(data["exit_price"]) if data.get("exit_price") else None,
        )
    
    def to_sdk_position(self) -> Dict[str, Any]:
        """Convert to format matching SDK Position model."""
        return {
            "position_id": self.position_id,
            "id": self.position_id,
            "asset_id": self.symbol,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.side,  # SDK uses order_type for side
            "status": self.status.value,
            "quantity": str(self.quantity),
            "entry_price": str(self.entry_price),
            "mark_price": str(self.entry_price),  # Updated by caller with live price
            "leverage": str(self.leverage),
            "margin": str(self.margin),
            "unrealized_pnl": str(self.unrealized_pnl),
            "realized_pnl": str(self.realized_pnl),
            "liquidation_price": str(self.liquidation_price) if self.liquidation_price else None,
            "stoploss_price": str(self.stoploss_price) if self.stoploss_price else None,
            "takeprofit_price": str(self.takeprofit_price) if self.takeprofit_price else None,
            "stoploss": {"price": str(self.stoploss_price)} if self.stoploss_price else None,
            "takeprofit": {"price": str(self.takeprofit_price)} if self.takeprofit_price else None,
            "created_at": self.opened_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class TradeRecord:
    """
    Historical record of an executed trade.
    
    Used for trade history and performance analysis.
    """
    trade_id: str
    order_id: str
    position_id: str
    symbol: str
    side: str                           # "LONG" or "SHORT"
    action: str                         # "OPEN", "CLOSE", "PARTIAL_CLOSE", "SL_TRIGGERED", "TP_TRIGGERED"
    
    quantity: Decimal
    price: Decimal
    notional: Decimal
    fee: Decimal
    
    pnl: Optional[Decimal] = None       # Only for close actions
    pnl_percent: Optional[Decimal] = None
    
    executed_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "position_id": self.position_id,
            "symbol": self.symbol,
            "side": self.side,
            "action": self.action,
            "quantity": str(self.quantity),
            "price": str(self.price),
            "notional": str(self.notional),
            "fee": str(self.fee),
            "pnl": str(self.pnl) if self.pnl is not None else None,
            "pnl_percent": str(self.pnl_percent) if self.pnl_percent is not None else None,
            "executed_at": self.executed_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TradeRecord":
        """Create from dictionary."""
        return cls(
            trade_id=data["trade_id"],
            order_id=data["order_id"],
            position_id=data["position_id"],
            symbol=data["symbol"],
            side=data["side"],
            action=data["action"],
            quantity=Decimal(data["quantity"]),
            price=Decimal(data["price"]),
            notional=Decimal(data["notional"]),
            fee=Decimal(data["fee"]),
            pnl=Decimal(data["pnl"]) if data.get("pnl") else None,
            pnl_percent=Decimal(data["pnl_percent"]) if data.get("pnl_percent") else None,
            executed_at=datetime.fromisoformat(data["executed_at"]) if isinstance(data["executed_at"], str) else data["executed_at"],
        )
