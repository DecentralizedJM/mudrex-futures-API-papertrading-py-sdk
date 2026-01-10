"""
Paper Trading API Wrappers
==========================

API classes that match the existing SDK interface but route to the paper trading engine.
This allows seamless switching between live and paper trading with mode="paper".
"""

import logging
from decimal import Decimal
from typing import List, Optional, Union, TYPE_CHECKING

from mudrex.models import (
    Order,
    Position,
    FuturesBalance,
    Leverage,
    OrderType,
    TriggerType,
    OrderStatus,
    PositionStatus,
)
from mudrex.paper.models import (
    PaperOrder,
    PaperPosition,
    PaperOrderStatus,
    PaperPositionStatus,
)

if TYPE_CHECKING:
    from mudrex.paper.engine import PaperTradingEngine
    from mudrex.api.assets import AssetsAPI

logger = logging.getLogger(__name__)


class PaperOrdersAPI:
    """
    Paper trading implementation of OrdersAPI.
    
    Provides the same interface as the live OrdersAPI but routes
    all operations to the paper trading engine.
    
    Example:
        >>> # Used internally by MudrexClient in paper mode
        >>> client = MudrexClient(api_secret="...", mode="paper")
        >>> order = client.orders.create_market_order(
        ...     symbol="BTCUSDT",
        ...     side="LONG",
        ...     quantity="0.01",
        ...     leverage="10"
        ... )
    """
    
    def __init__(self, engine: "PaperTradingEngine", assets_api: "AssetsAPI"):
        """
        Initialize the paper orders API.
        
        Args:
            engine: PaperTradingEngine instance
            assets_api: Live AssetsAPI for validation
        """
        self._engine = engine
        self._assets_api = assets_api
    
    def create_market_order(
        self,
        symbol: str,
        side: Union[str, OrderType],
        quantity: str,
        leverage: str = "1",
        stoploss_price: Optional[str] = None,
        takeprofit_price: Optional[str] = None,
        reduce_only: bool = False,
    ) -> Order:
        """
        Place a market order (executes immediately at current price).
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            side: Order direction - "LONG" or "SHORT"
            quantity: Order quantity (as string for precision)
            leverage: Leverage to use (default: "1")
            stoploss_price: Optional stop-loss price
            takeprofit_price: Optional take-profit price
            reduce_only: If True, only reduces existing position
            
        Returns:
            Order: Executed order details
        """
        # Convert types
        side_str = side.value if isinstance(side, OrderType) else side.upper()
        
        paper_order = self._engine.create_market_order(
            symbol=symbol,
            side=side_str,
            quantity=Decimal(quantity),
            leverage=int(leverage),
            stoploss_price=Decimal(stoploss_price) if stoploss_price else None,
            takeprofit_price=Decimal(takeprofit_price) if takeprofit_price else None,
            reduce_only=reduce_only,
        )
        
        return self._convert_to_sdk_order(paper_order)
    
    def create_market_order_with_amount(
        self,
        symbol: str,
        side: Union[str, OrderType],
        amount: str,
        leverage: str = "1",
        stoploss_price: Optional[str] = None,
        takeprofit_price: Optional[str] = None,
        reduce_only: bool = False,
    ) -> Order:
        """
        Place a market order specified by quote currency amount (USDT).
        
        Args:
            symbol: Trading symbol
            side: Order direction
            amount: Amount in USDT
            leverage: Leverage to use
            stoploss_price: Optional stop-loss price
            takeprofit_price: Optional take-profit price
            reduce_only: If True, only reduces existing position
            
        Returns:
            Order: Executed order details
        """
        # Get current price and calculate quantity
        current_price = self._engine.price_feed.get_price(symbol)
        quantity = Decimal(amount) / current_price
        
        # Get asset info for quantity rounding
        try:
            asset_info = self._engine.price_feed.get_asset_info(symbol)
            quantity_step = Decimal(asset_info.get("quantity_step", "0.001"))
            if quantity_step > 0:
                quantity = (quantity // quantity_step) * quantity_step
        except Exception:
            pass
        
        return self.create_market_order(
            symbol=symbol,
            side=side,
            quantity=str(quantity),
            leverage=leverage,
            stoploss_price=stoploss_price,
            takeprofit_price=takeprofit_price,
            reduce_only=reduce_only,
        )
    
    def create_limit_order(
        self,
        symbol: str,
        side: Union[str, OrderType],
        quantity: str,
        price: str,
        leverage: str = "1",
        stoploss_price: Optional[str] = None,
        takeprofit_price: Optional[str] = None,
        reduce_only: bool = False,
    ) -> Order:
        """
        Place a limit order (executes when price reaches target).
        
        Args:
            symbol: Trading symbol
            side: Order direction
            quantity: Order quantity
            price: Limit price
            leverage: Leverage to use
            stoploss_price: Optional stop-loss price
            takeprofit_price: Optional take-profit price
            reduce_only: If True, only reduces existing position
            
        Returns:
            Order: Pending order details
        """
        side_str = side.value if isinstance(side, OrderType) else side.upper()
        
        paper_order = self._engine.create_limit_order(
            symbol=symbol,
            side=side_str,
            quantity=Decimal(quantity),
            price=Decimal(price),
            leverage=int(leverage),
            stoploss_price=Decimal(stoploss_price) if stoploss_price else None,
            takeprofit_price=Decimal(takeprofit_price) if takeprofit_price else None,
            reduce_only=reduce_only,
        )
        
        return self._convert_to_sdk_order(paper_order)
    
    def list_open(self) -> List[Order]:
        """
        Get all open (pending) orders.
        
        Returns:
            List[Order]: List of pending orders
        """
        paper_orders = self._engine.list_open_orders()
        return [self._convert_to_sdk_order(o) for o in paper_orders]
    
    def get(self, order_id: str) -> Order:
        """
        Get details of a specific order.
        
        Args:
            order_id: The order ID
            
        Returns:
            Order: Order details
        """
        paper_order = self._engine.get_order(order_id)
        return self._convert_to_sdk_order(paper_order)
    
    def get_history(self, limit: int = 100) -> List[Order]:
        """
        Get order history.
        
        Args:
            limit: Maximum number of orders to return
            
        Returns:
            List[Order]: Historical orders
        """
        paper_orders = self._engine.get_order_history(limit)
        return [self._convert_to_sdk_order(o) for o in paper_orders]
    
    def cancel(self, order_id: str) -> bool:
        """
        Cancel a pending order.
        
        Args:
            order_id: The order ID to cancel
            
        Returns:
            bool: True if cancelled successfully
        """
        return self._engine.cancel_order(order_id)
    
    def amend(
        self,
        order_id: str,
        price: Optional[str] = None,
        quantity: Optional[str] = None,
    ) -> Order:
        """
        Amend a pending order.
        
        Note: Paper trading does not support amendment - cancel and recreate instead.
        """
        raise NotImplementedError(
            "Order amendment not supported in paper trading. "
            "Cancel the order and create a new one instead."
        )
    
    def _convert_to_sdk_order(self, paper_order: PaperOrder) -> Order:
        """Convert PaperOrder to SDK Order model."""
        # Map paper status to SDK status
        status_map = {
            PaperOrderStatus.PENDING: OrderStatus.OPEN,
            PaperOrderStatus.FILLED: OrderStatus.FILLED,
            PaperOrderStatus.CANCELLED: OrderStatus.CANCELLED,
            PaperOrderStatus.EXPIRED: OrderStatus.EXPIRED,
            PaperOrderStatus.REJECTED: OrderStatus.CANCELLED,
        }
        
        return Order.from_dict(paper_order.to_sdk_order())


class PaperPositionsAPI:
    """
    Paper trading implementation of PositionsAPI.
    """
    
    def __init__(self, engine: "PaperTradingEngine", assets_api: "AssetsAPI"):
        self._engine = engine
        self._assets_api = assets_api
    
    def list_open(self) -> List[Position]:
        """
        Get all open positions.
        
        Returns:
            List[Position]: List of open positions with updated PnL
        """
        paper_positions = self._engine.list_open_positions()
        positions = []
        
        for pp in paper_positions:
            # Get current price for mark_price
            try:
                current_price = self._engine.price_feed.get_price(pp.symbol)
                sdk_data = pp.to_sdk_position()
                sdk_data["mark_price"] = str(current_price)
                positions.append(Position.from_dict(sdk_data))
            except Exception as e:
                logger.warning(f"Failed to convert position {pp.position_id}: {e}")
                positions.append(Position.from_dict(pp.to_sdk_position()))
        
        return positions
    
    def get(self, position_id: str) -> Position:
        """
        Get a specific position.
        
        Args:
            position_id: The position ID
            
        Returns:
            Position: Position details
        """
        paper_position = self._engine.get_position(position_id)
        
        # Get current price
        try:
            current_price = self._engine.price_feed.get_price(paper_position.symbol)
            sdk_data = paper_position.to_sdk_position()
            sdk_data["mark_price"] = str(current_price)
            return Position.from_dict(sdk_data)
        except Exception:
            return Position.from_dict(paper_position.to_sdk_position())
    
    def close(self, position_id: str) -> bool:
        """
        Close a position completely.
        
        Args:
            position_id: The position ID to close
            
        Returns:
            bool: True if closed successfully
        """
        self._engine.close_position(position_id)
        return True
    
    def partial_close(self, position_id: str, quantity: str) -> Position:
        """
        Partially close a position.
        
        Args:
            position_id: The position ID
            quantity: Quantity to close
            
        Returns:
            Position: Updated position
        """
        paper_position = self._engine.close_position(
            position_id,
            quantity=Decimal(quantity)
        )
        return Position.from_dict(paper_position.to_sdk_position())
    
    def reverse(self, position_id: str) -> Position:
        """
        Reverse a position (close and open opposite).
        
        Args:
            position_id: The position ID to reverse
            
        Returns:
            Position: New reversed position
        """
        position = self._engine.get_position(position_id)
        
        # Close existing
        self._engine.close_position(position_id)
        
        # Open opposite
        opposite_side = "SHORT" if position.side == "LONG" else "LONG"
        current_price = self._engine.price_feed.get_price(position.symbol)
        
        order = self._engine.create_market_order(
            symbol=position.symbol,
            side=opposite_side,
            quantity=position.quantity,
            leverage=position.leverage,
        )
        
        # Get the new position
        new_position = self._engine.get_position(order.position_id)
        return Position.from_dict(new_position.to_sdk_position())
    
    def set_stoploss(self, position_id: str, stoploss_price: str) -> bool:
        """
        Set stop-loss for a position.
        
        Args:
            position_id: The position ID
            stoploss_price: Stop-loss price
            
        Returns:
            bool: True if set successfully
        """
        return self._engine.set_stoploss(position_id, Decimal(stoploss_price))
    
    def set_takeprofit(self, position_id: str, takeprofit_price: str) -> bool:
        """
        Set take-profit for a position.
        
        Args:
            position_id: The position ID
            takeprofit_price: Take-profit price
            
        Returns:
            bool: True if set successfully
        """
        return self._engine.set_takeprofit(position_id, Decimal(takeprofit_price))
    
    def set_risk_order(
        self,
        position_id: str,
        stoploss_price: Optional[str] = None,
        takeprofit_price: Optional[str] = None,
    ) -> bool:
        """
        Set both stop-loss and take-profit for a position.
        
        Args:
            position_id: The position ID
            stoploss_price: Optional stop-loss price
            takeprofit_price: Optional take-profit price
            
        Returns:
            bool: True if set successfully
        """
        return self._engine.set_risk_order(
            position_id,
            stoploss_price=Decimal(stoploss_price) if stoploss_price else None,
            takeprofit_price=Decimal(takeprofit_price) if takeprofit_price else None,
        )
    
    def list_history(self, limit: int = 100) -> List[Position]:
        """
        Get position history (closed positions).
        
        Args:
            limit: Maximum positions to return
            
        Returns:
            List[Position]: Closed positions
        """
        paper_positions = self._engine.get_position_history(limit)
        return [Position.from_dict(p.to_sdk_position()) for p in paper_positions]


class PaperWalletAPI:
    """
    Paper trading implementation of WalletAPI.
    """
    
    def __init__(self, engine: "PaperTradingEngine"):
        self._engine = engine
    
    def get_spot_balance(self):
        """
        Get spot wallet balance.
        
        Note: In paper trading, there's no spot wallet - returns zeros.
        """
        from mudrex.models import WalletBalance
        return WalletBalance(
            available="0",
            locked="0",
            total="0",
        )
    
    def get_futures_balance(self) -> FuturesBalance:
        """
        Get futures wallet balance.
        
        Returns:
            FuturesBalance: Paper trading balance
        """
        wallet = self._engine.get_wallet()
        
        return FuturesBalance(
            balance=str(wallet.balance),
            available=str(wallet.available),
            locked=str(wallet.locked_margin),
            unrealized_pnl=str(wallet.unrealized_pnl),
        )
    
    def transfer_to_futures(self, amount: str) -> bool:
        """
        Transfer funds to futures wallet.
        
        Note: In paper trading, this just adds to the balance.
        """
        wallet = self._engine.wallet
        add_amount = Decimal(amount)
        
        wallet.balance += add_amount
        wallet.available += add_amount
        
        logger.info(f"Paper wallet: Added ${amount} (transfer simulation)")
        return True
    
    def transfer_to_spot(self, amount: str) -> bool:
        """
        Transfer funds from futures to spot wallet.
        
        Note: In paper trading, this reduces the available balance.
        """
        wallet = self._engine.wallet
        withdraw_amount = Decimal(amount)
        
        if wallet.available < withdraw_amount:
            raise ValueError(f"Insufficient available balance: {wallet.available}")
        
        wallet.balance -= withdraw_amount
        wallet.available -= withdraw_amount
        
        logger.info(f"Paper wallet: Withdrew ${amount} (transfer simulation)")
        return True


class PaperLeverageAPI:
    """
    Paper trading implementation of LeverageAPI.
    """
    
    def __init__(self, engine: "PaperTradingEngine", assets_api: "AssetsAPI"):
        self._engine = engine
        self._assets_api = assets_api
    
    def get(self, symbol: str) -> Leverage:
        """
        Get current leverage setting for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Leverage: Current leverage settings
        """
        leverage_value = self._engine.get_leverage(symbol)
        
        return Leverage(
            asset_id=symbol,
            symbol=symbol,
            leverage=str(leverage_value),
            margin_type="ISOLATED",
        )
    
    def set(
        self,
        symbol: str,
        leverage: str,
        margin_type: str = "ISOLATED",
    ) -> Leverage:
        """
        Set leverage for a symbol.
        
        Args:
            symbol: Trading symbol
            leverage: Leverage value (1-100)
            margin_type: Margin type (only ISOLATED supported)
            
        Returns:
            Leverage: Updated leverage settings
        """
        self._engine.set_leverage(symbol, int(leverage))
        
        return Leverage(
            asset_id=symbol,
            symbol=symbol,
            leverage=leverage,
            margin_type=margin_type,
        )


class PaperFeesAPI:
    """
    Paper trading implementation of FeesAPI.
    """
    
    def __init__(self, engine: "PaperTradingEngine"):
        self._engine = engine
    
    def get_history(self, limit: int = 100) -> list:
        """
        Get fee history.
        
        Note: Paper trading simulates fees at 0.05% per trade.
        Returns fee records from trade history.
        """
        trades = self._engine.get_trade_history(limit)
        
        # Convert to fee records
        fee_records = []
        for trade in trades:
            if trade.fee > 0:
                fee_records.append({
                    "trade_id": trade.trade_id,
                    "symbol": trade.symbol,
                    "fee": str(trade.fee),
                    "fee_rate": "0.0005",  # 0.05%
                    "executed_at": trade.executed_at.isoformat() if trade.executed_at else None,
                })
        
        return fee_records
    
    def get_total_fees(self) -> str:
        """
        Get total fees paid.
        
        Returns:
            str: Total fees paid in paper trading
        """
        wallet = self._engine.get_wallet()
        return str(wallet.total_fees_paid)
