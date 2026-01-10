"""
Paper Trading Engine
====================

Core simulation engine for paper trading.
Handles order execution, position management, and PnL calculations.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Union, TYPE_CHECKING

from mudrex.paper.models import (
    PaperWallet,
    PaperOrder,
    PaperPosition,
    TradeRecord,
    PaperOrderStatus,
    PaperPositionStatus,
    CloseReason,
    generate_paper_id,
)
from mudrex.paper.exceptions import (
    InsufficientMarginError,
    InvalidOrderError,
    PositionNotFoundError,
    OrderNotFoundError,
    PositionAlreadyClosedError,
    OrderAlreadyFilledError,
    SymbolNotFoundError,
)

if TYPE_CHECKING:
    from mudrex.paper.price_feed import PriceFeedService

logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """
    Simulates futures trading without real orders.
    
    Features:
    - Market and limit order execution
    - LONG/SHORT position management
    - Leverage and margin calculations
    - Stop-loss and take-profit orders
    - Unrealized and realized PnL tracking
    - Position netting (one position per symbol per side)
    - Trading fee simulation
    
    Example:
        >>> from mudrex.paper import PaperTradingEngine, MockPriceFeedService
        >>> 
        >>> price_feed = MockPriceFeedService()
        >>> engine = PaperTradingEngine(
        ...     initial_balance=Decimal("10000"),
        ...     price_feed=price_feed
        ... )
        >>> 
        >>> # Place a market order
        >>> order = engine.create_market_order(
        ...     symbol="BTCUSDT",
        ...     side="LONG",
        ...     quantity=Decimal("0.1"),
        ...     leverage=10
        ... )
        >>> 
        >>> # Check positions
        >>> positions = engine.list_open_positions()
    """
    
    # Default trading fee rate (0.05% = 5 bps)
    DEFAULT_FEE_RATE = Decimal("0.0005")
    
    # Limit order expiry (24 hours)
    LIMIT_ORDER_EXPIRY_HOURS = 24
    
    def __init__(
        self,
        initial_balance: Decimal,
        price_feed: "PriceFeedService",
        fee_rate: Decimal = None,
        enable_logging: bool = True,
    ):
        """
        Initialize the paper trading engine.
        
        Args:
            initial_balance: Starting paper balance in USDT
            price_feed: Price feed service for getting live prices
            fee_rate: Trading fee rate (default: 0.05%)
            enable_logging: Enable detailed logging
        """
        self.price_feed = price_feed
        self.fee_rate = fee_rate or self.DEFAULT_FEE_RATE
        self.enable_logging = enable_logging
        
        # Core state
        self.wallet = PaperWallet(
            balance=initial_balance,
            available=initial_balance,
        )
        
        # Order and position storage
        self.orders: Dict[str, PaperOrder] = {}
        self.positions: Dict[str, PaperPosition] = {}
        self.trade_history: List[TradeRecord] = []
        
        # Pending limit orders (symbol -> list of order_ids)
        self.pending_orders: Dict[str, List[str]] = {}
        
        # Leverage settings per symbol (symbol -> leverage)
        self.leverage_settings: Dict[str, int] = {}
        
        if enable_logging:
            logger.info(f"Paper trading engine initialized with ${initial_balance} balance")
    
    # =========================================================================
    # Order Creation
    # =========================================================================
    
    def create_market_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        leverage: int = 1,
        stoploss_price: Optional[Decimal] = None,
        takeprofit_price: Optional[Decimal] = None,
        reduce_only: bool = False,
    ) -> PaperOrder:
        """
        Create and execute a market order.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            side: Order direction - "LONG" or "SHORT"
            quantity: Order quantity
            leverage: Leverage to use
            stoploss_price: Optional stop-loss price
            takeprofit_price: Optional take-profit price
            reduce_only: If True, only reduces existing position
            
        Returns:
            Executed PaperOrder
            
        Raises:
            InvalidOrderError: If parameters are invalid
            InsufficientMarginError: If not enough margin
        """
        # Normalize side
        side = side.upper()
        if side not in ("LONG", "SHORT"):
            raise InvalidOrderError("side", side, "Must be LONG or SHORT")
        
        # Validate symbol and get current price
        current_price = self.price_feed.get_price(symbol)
        
        # Validate quantity
        valid, error = self.price_feed.validate_quantity(symbol, quantity)
        if not valid:
            raise InvalidOrderError("quantity", str(quantity), error)
        
        # Validate leverage
        valid, error = self.price_feed.validate_leverage(symbol, leverage)
        if not valid:
            raise InvalidOrderError("leverage", str(leverage), error)
        
        # Create order
        order = PaperOrder(
            order_id=generate_paper_id("ord"),
            symbol=symbol,
            side=side,
            order_type="MARKET",
            quantity=quantity,
            leverage=leverage,
            status=PaperOrderStatus.PENDING,
            stoploss_price=stoploss_price,
            takeprofit_price=takeprofit_price,
            reduce_only=reduce_only,
        )
        
        # Execute immediately
        self._execute_order(order, current_price)
        
        return order
    
    def create_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        leverage: int = 1,
        stoploss_price: Optional[Decimal] = None,
        takeprofit_price: Optional[Decimal] = None,
        reduce_only: bool = False,
    ) -> PaperOrder:
        """
        Create a limit order (executes when price reaches target).
        
        Args:
            symbol: Trading symbol
            side: Order direction
            quantity: Order quantity
            price: Limit price (order fills when price reaches this level)
            leverage: Leverage to use
            stoploss_price: Optional stop-loss price
            takeprofit_price: Optional take-profit price
            reduce_only: If True, only reduces existing position
            
        Returns:
            Pending PaperOrder
        """
        # Normalize side
        side = side.upper()
        if side not in ("LONG", "SHORT"):
            raise InvalidOrderError("side", side, "Must be LONG or SHORT")
        
        # Validate symbol exists
        if not self.price_feed.is_valid_symbol(symbol):
            raise SymbolNotFoundError(symbol)
        
        # Validate quantity
        valid, error = self.price_feed.validate_quantity(symbol, quantity)
        if not valid:
            raise InvalidOrderError("quantity", str(quantity), error)
        
        # Validate leverage
        valid, error = self.price_feed.validate_leverage(symbol, leverage)
        if not valid:
            raise InvalidOrderError("leverage", str(leverage), error)
        
        # Calculate and reserve margin
        notional = quantity * price
        required_margin = notional / Decimal(leverage)
        fee = notional * self.fee_rate
        total_required = required_margin + fee
        
        if self.wallet.available < total_required:
            raise InsufficientMarginError(
                required=str(total_required),
                available=str(self.wallet.available)
            )
        
        # Create order
        order = PaperOrder(
            order_id=generate_paper_id("ord"),
            symbol=symbol,
            side=side,
            order_type="LIMIT",
            quantity=quantity,
            price=price,
            leverage=leverage,
            status=PaperOrderStatus.PENDING,
            stoploss_price=stoploss_price,
            takeprofit_price=takeprofit_price,
            reduce_only=reduce_only,
            margin_used=required_margin,
            expires_at=datetime.utcnow() + timedelta(hours=self.LIMIT_ORDER_EXPIRY_HOURS),
        )
        
        # Reserve margin
        self.wallet.lock_margin(required_margin)
        
        # Store order
        self.orders[order.order_id] = order
        
        # Add to pending orders for symbol
        if symbol not in self.pending_orders:
            self.pending_orders[symbol] = []
        self.pending_orders[symbol].append(order.order_id)
        
        if self.enable_logging:
            logger.info(f"Limit order created: {order.order_id} {side} {quantity} {symbol} @ {price}")
        
        return order
    
    def _execute_order(self, order: PaperOrder, execution_price: Decimal) -> None:
        """
        Execute an order at the given price.
        
        This handles:
        - Margin validation and deduction
        - Position creation or update
        - Fee calculation
        - Trade record creation
        """
        # Calculate costs
        notional = order.quantity * execution_price
        required_margin = notional / Decimal(order.leverage)
        fee = notional * self.fee_rate
        
        # For limit orders, margin is already locked
        if order.order_type == "MARKET":
            total_required = required_margin + fee
            
            # Check if this is reduce_only (closing existing position)
            if order.reduce_only:
                position = self._find_position(order.symbol, order.side)
                if not position:
                    # No position to reduce - try opposite side
                    opposite_side = "SHORT" if order.side == "LONG" else "LONG"
                    position = self._find_position(order.symbol, opposite_side)
                    if position:
                        # Close existing position
                        self._close_position_internal(position, execution_price, CloseReason.MANUAL)
                        order.fill(execution_price, position.position_id)
                        self.orders[order.order_id] = order
                        return
                    else:
                        raise InvalidOrderError("reduce_only", "true", "No position to reduce")
            
            if self.wallet.available < total_required:
                order.status = PaperOrderStatus.REJECTED
                self.orders[order.order_id] = order
                raise InsufficientMarginError(
                    required=str(total_required),
                    available=str(self.wallet.available)
                )
            
            # Lock margin
            self.wallet.lock_margin(required_margin)
        else:
            # Limit order - margin already locked, just need fee
            self.wallet.deduct_fee(fee)
        
        # Deduct fee (for market orders)
        if order.order_type == "MARKET":
            self.wallet.deduct_fee(fee)
        
        order.fee_paid = fee
        order.margin_used = required_margin
        
        # Handle position
        position = self._handle_position_for_order(order, execution_price)
        
        # Set SL/TP on position
        if order.stoploss_price and position:
            position.stoploss_price = order.stoploss_price
        if order.takeprofit_price and position:
            position.takeprofit_price = order.takeprofit_price
        if position:
            position.liquidation_price = position.calculate_liquidation_price()
        
        # Mark order as filled
        order.fill(execution_price, position.position_id if position else None)
        self.orders[order.order_id] = order
        
        # Record trade
        trade = TradeRecord(
            trade_id=generate_paper_id("trd"),
            order_id=order.order_id,
            position_id=position.position_id if position else "",
            symbol=order.symbol,
            side=order.side,
            action="OPEN",
            quantity=order.quantity,
            price=execution_price,
            notional=notional,
            fee=fee,
            executed_at=datetime.utcnow(),
        )
        self.trade_history.append(trade)
        
        if self.enable_logging:
            logger.info(
                f"Order executed: {order.order_id} {order.side} {order.quantity} {order.symbol} "
                f"@ {execution_price} (margin: {required_margin}, fee: {fee})"
            )
    
    def _handle_position_for_order(
        self,
        order: PaperOrder,
        execution_price: Decimal
    ) -> Optional[PaperPosition]:
        """
        Handle position creation/update for an executed order.
        
        Logic:
        - If no existing position: create new
        - If same side: average into existing position
        - If opposite side: net positions (close existing, open remainder)
        """
        existing = self._find_position(order.symbol, order.side)
        opposite = self._find_position(
            order.symbol,
            "SHORT" if order.side == "LONG" else "LONG"
        )
        
        # Case 1: No existing position, no opposite - create new
        if not existing and not opposite:
            return self._create_position(order, execution_price)
        
        # Case 2: Same side exists - average in
        if existing:
            return self._average_into_position(existing, order, execution_price)
        
        # Case 3: Opposite side exists - net off
        if opposite:
            return self._net_positions(opposite, order, execution_price)
        
        return None
    
    def _create_position(
        self,
        order: PaperOrder,
        execution_price: Decimal
    ) -> PaperPosition:
        """Create a new position from an order."""
        position = PaperPosition(
            position_id=generate_paper_id("pos"),
            symbol=order.symbol,
            side=order.side,
            status=PaperPositionStatus.OPEN,
            quantity=order.quantity,
            entry_price=execution_price,
            leverage=order.leverage,
            margin=order.margin_used,
        )
        
        self.positions[position.position_id] = position
        
        if self.enable_logging:
            logger.info(f"Position opened: {position.position_id} {order.side} {order.quantity} {order.symbol}")
        
        return position
    
    def _average_into_position(
        self,
        position: PaperPosition,
        order: PaperOrder,
        execution_price: Decimal
    ) -> PaperPosition:
        """Average a new order into an existing position."""
        old_notional = position.quantity * position.entry_price
        new_notional = order.quantity * execution_price
        
        new_quantity = position.quantity + order.quantity
        new_entry_price = (old_notional + new_notional) / new_quantity
        
        position.quantity = new_quantity
        position.entry_price = new_entry_price
        position.margin += order.margin_used
        position.updated_at = datetime.utcnow()
        position.liquidation_price = position.calculate_liquidation_price()
        
        if self.enable_logging:
            logger.info(
                f"Position averaged: {position.position_id} now {new_quantity} @ {new_entry_price}"
            )
        
        return position
    
    def _net_positions(
        self,
        existing: PaperPosition,
        order: PaperOrder,
        execution_price: Decimal
    ) -> Optional[PaperPosition]:
        """
        Net an order against an opposite position.
        
        Scenarios:
        - Order qty == position qty: Close position completely
        - Order qty < position qty: Partial close of position
        - Order qty > position qty: Close position, open new with remainder
        """
        if order.quantity == existing.quantity:
            # Exact match - close position
            self._close_position_internal(existing, execution_price, CloseReason.MANUAL)
            return None
        
        elif order.quantity < existing.quantity:
            # Partial close
            pnl = existing.partial_close(order.quantity, execution_price)
            
            # Release proportional margin and realize PnL
            released_margin = order.margin_used
            self.wallet.release_margin(released_margin)
            self.wallet.balance += pnl
            self.wallet.available += pnl
            self.wallet.realized_pnl += pnl
            
            if self.enable_logging:
                logger.info(
                    f"Position partially closed: {existing.position_id} "
                    f"closed {order.quantity}, remaining {existing.quantity}, PnL: {pnl}"
                )
            
            return existing
        
        else:
            # Close existing, open new with remainder
            self._close_position_internal(existing, execution_price, CloseReason.MANUAL)
            
            # Create new position with remainder
            remainder = order.quantity - existing.quantity
            remainder_margin = (remainder * execution_price) / Decimal(order.leverage)
            
            new_position = PaperPosition(
                position_id=generate_paper_id("pos"),
                symbol=order.symbol,
                side=order.side,
                status=PaperPositionStatus.OPEN,
                quantity=remainder,
                entry_price=execution_price,
                leverage=order.leverage,
                margin=remainder_margin,
            )
            
            self.positions[new_position.position_id] = new_position
            
            if self.enable_logging:
                logger.info(
                    f"Position flipped: closed {existing.position_id}, "
                    f"opened {new_position.position_id} with {remainder}"
                )
            
            return new_position
    
    # =========================================================================
    # Position Management
    # =========================================================================
    
    def list_open_positions(self) -> List[PaperPosition]:
        """Get all open positions with updated PnL."""
        open_positions = []
        
        for position in self.positions.values():
            if position.status == PaperPositionStatus.OPEN:
                # Update PnL with current price
                try:
                    current_price = self.price_feed.get_price(position.symbol)
                    position.update_pnl(current_price)
                except Exception as e:
                    logger.warning(f"Failed to update PnL for {position.position_id}: {e}")
                
                open_positions.append(position)
        
        # Update wallet unrealized PnL
        total_unrealized = sum(p.unrealized_pnl for p in open_positions)
        self.wallet.unrealized_pnl = total_unrealized
        
        return open_positions
    
    def get_position(self, position_id: str) -> PaperPosition:
        """Get a specific position by ID."""
        if position_id not in self.positions:
            raise PositionNotFoundError(position_id)
        
        position = self.positions[position_id]
        
        # Update PnL if open
        if position.status == PaperPositionStatus.OPEN:
            try:
                current_price = self.price_feed.get_price(position.symbol)
                position.update_pnl(current_price)
            except Exception:
                pass
        
        return position
    
    def close_position(
        self,
        position_id: str,
        quantity: Optional[Decimal] = None
    ) -> PaperPosition:
        """
        Close a position (full or partial).
        
        Args:
            position_id: Position to close
            quantity: Quantity to close (None = full close)
            
        Returns:
            Updated position
        """
        position = self.get_position(position_id)
        
        if position.status != PaperPositionStatus.OPEN:
            raise PositionAlreadyClosedError(position_id)
        
        current_price = self.price_feed.get_price(position.symbol)
        
        if quantity is None or quantity >= position.quantity:
            # Full close
            self._close_position_internal(position, current_price, CloseReason.MANUAL)
        else:
            # Partial close
            pnl = position.partial_close(quantity, current_price)
            
            # Release margin and realize PnL
            ratio = quantity / (position.quantity + quantity)
            released_margin = position.margin * ratio / (1 - ratio)
            self.wallet.realize_pnl(pnl, released_margin)
            
            # Record trade
            trade = TradeRecord(
                trade_id=generate_paper_id("trd"),
                order_id="",
                position_id=position_id,
                symbol=position.symbol,
                side=position.side,
                action="PARTIAL_CLOSE",
                quantity=quantity,
                price=current_price,
                notional=quantity * current_price,
                fee=Decimal("0"),
                pnl=pnl,
                pnl_percent=(pnl / (quantity * position.entry_price)) * 100,
                executed_at=datetime.utcnow(),
            )
            self.trade_history.append(trade)
        
        return position
    
    def _close_position_internal(
        self,
        position: PaperPosition,
        exit_price: Decimal,
        reason: CloseReason
    ) -> Decimal:
        """
        Internal method to close a position.
        
        Returns: realized PnL
        """
        pnl = position.close(exit_price, reason)
        
        # Calculate exit fee
        exit_notional = position.quantity * exit_price
        exit_fee = exit_notional * self.fee_rate
        
        # Release margin and realize PnL (minus exit fee)
        net_pnl = pnl - exit_fee
        self.wallet.realize_pnl(net_pnl, position.margin)
        self.wallet.total_fees_paid += exit_fee
        
        # Record trade
        action_map = {
            CloseReason.MANUAL: "CLOSE",
            CloseReason.STOPLOSS: "SL_TRIGGERED",
            CloseReason.TAKEPROFIT: "TP_TRIGGERED",
            CloseReason.LIQUIDATION: "LIQUIDATION",
        }
        
        trade = TradeRecord(
            trade_id=generate_paper_id("trd"),
            order_id="",
            position_id=position.position_id,
            symbol=position.symbol,
            side=position.side,
            action=action_map.get(reason, "CLOSE"),
            quantity=position.quantity,
            price=exit_price,
            notional=exit_notional,
            fee=exit_fee,
            pnl=net_pnl,
            pnl_percent=(pnl / (position.quantity * position.entry_price)) * 100 if position.entry_price else Decimal("0"),
            executed_at=datetime.utcnow(),
        )
        self.trade_history.append(trade)
        
        if self.enable_logging:
            logger.info(
                f"Position closed: {position.position_id} @ {exit_price} "
                f"(reason: {reason.value}, PnL: {net_pnl})"
            )
        
        return net_pnl
    
    def set_stoploss(self, position_id: str, stoploss_price: Decimal) -> bool:
        """Set stop-loss for a position."""
        position = self.get_position(position_id)
        
        if position.status != PaperPositionStatus.OPEN:
            raise PositionAlreadyClosedError(position_id)
        
        position.stoploss_price = stoploss_price
        position.updated_at = datetime.utcnow()
        
        if self.enable_logging:
            logger.info(f"Stop-loss set: {position_id} @ {stoploss_price}")
        
        return True
    
    def set_takeprofit(self, position_id: str, takeprofit_price: Decimal) -> bool:
        """Set take-profit for a position."""
        position = self.get_position(position_id)
        
        if position.status != PaperPositionStatus.OPEN:
            raise PositionAlreadyClosedError(position_id)
        
        position.takeprofit_price = takeprofit_price
        position.updated_at = datetime.utcnow()
        
        if self.enable_logging:
            logger.info(f"Take-profit set: {position_id} @ {takeprofit_price}")
        
        return True
    
    def set_risk_order(
        self,
        position_id: str,
        stoploss_price: Optional[Decimal] = None,
        takeprofit_price: Optional[Decimal] = None,
    ) -> bool:
        """Set both stop-loss and take-profit for a position."""
        position = self.get_position(position_id)
        
        if position.status != PaperPositionStatus.OPEN:
            raise PositionAlreadyClosedError(position_id)
        
        if stoploss_price is not None:
            position.stoploss_price = stoploss_price
        if takeprofit_price is not None:
            position.takeprofit_price = takeprofit_price
        
        position.updated_at = datetime.utcnow()
        
        if self.enable_logging:
            logger.info(f"Risk orders set: {position_id} SL={stoploss_price} TP={takeprofit_price}")
        
        return True
    
    def _find_position(self, symbol: str, side: str) -> Optional[PaperPosition]:
        """Find an open position by symbol and side."""
        for position in self.positions.values():
            if (
                position.symbol == symbol
                and position.side == side
                and position.status == PaperPositionStatus.OPEN
            ):
                return position
        return None
    
    # =========================================================================
    # Order Management
    # =========================================================================
    
    def list_open_orders(self) -> List[PaperOrder]:
        """Get all pending orders."""
        return [
            order for order in self.orders.values()
            if order.status == PaperOrderStatus.PENDING
        ]
    
    def get_order(self, order_id: str) -> PaperOrder:
        """Get a specific order by ID."""
        if order_id not in self.orders:
            raise OrderNotFoundError(order_id)
        return self.orders[order_id]
    
    def get_order_history(self, limit: int = 100) -> List[PaperOrder]:
        """Get order history."""
        orders = list(self.orders.values())
        orders.sort(key=lambda o: o.created_at, reverse=True)
        return orders[:limit]
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        order = self.get_order(order_id)
        
        if order.status == PaperOrderStatus.FILLED:
            raise OrderAlreadyFilledError(order_id)
        
        if order.status != PaperOrderStatus.PENDING:
            return False
        
        order.cancel()
        
        # Release locked margin
        if order.margin_used > 0:
            self.wallet.release_margin(order.margin_used)
        
        # Remove from pending orders
        if order.symbol in self.pending_orders:
            if order_id in self.pending_orders[order.symbol]:
                self.pending_orders[order.symbol].remove(order_id)
        
        if self.enable_logging:
            logger.info(f"Order cancelled: {order_id}")
        
        return True
    
    def check_limit_orders(self) -> List[PaperOrder]:
        """
        Check all pending limit orders for fill conditions.
        
        Called periodically by the SL/TP monitor.
        
        Returns:
            List of orders that were filled
        """
        filled_orders = []
        
        for symbol, order_ids in list(self.pending_orders.items()):
            if not order_ids:
                continue
            
            try:
                current_price = self.price_feed.get_price(symbol)
            except Exception:
                continue
            
            for order_id in list(order_ids):
                order = self.orders.get(order_id)
                if not order or order.status != PaperOrderStatus.PENDING:
                    continue
                
                # Check expiry
                if order.expires_at and datetime.utcnow() > order.expires_at:
                    order.status = PaperOrderStatus.EXPIRED
                    self.wallet.release_margin(order.margin_used)
                    order_ids.remove(order_id)
                    continue
                
                # Check fill condition
                should_fill = False
                
                if order.side == "LONG" and order.price:
                    # Buy limit fills when price drops to limit price
                    should_fill = current_price <= order.price
                elif order.side == "SHORT" and order.price:
                    # Sell limit fills when price rises to limit price
                    should_fill = current_price >= order.price
                
                if should_fill:
                    self._execute_order(order, order.price)
                    order_ids.remove(order_id)
                    filled_orders.append(order)
        
        return filled_orders
    
    # =========================================================================
    # Leverage Management
    # =========================================================================
    
    def get_leverage(self, symbol: str) -> int:
        """Get current leverage setting for a symbol."""
        return self.leverage_settings.get(symbol, 1)
    
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for a symbol."""
        valid, error = self.price_feed.validate_leverage(symbol, leverage)
        if not valid:
            raise InvalidOrderError("leverage", str(leverage), error)
        
        self.leverage_settings[symbol] = leverage
        
        if self.enable_logging:
            logger.info(f"Leverage set: {symbol} = {leverage}x")
        
        return True
    
    # =========================================================================
    # Wallet Operations
    # =========================================================================
    
    def get_wallet(self) -> PaperWallet:
        """Get current wallet state with updated unrealized PnL."""
        # Update unrealized PnL from positions
        self.list_open_positions()  # This updates wallet.unrealized_pnl
        return self.wallet
    
    def reset_wallet(self, new_balance: Decimal = None) -> None:
        """Reset wallet to initial state (clears all positions and orders)."""
        if new_balance is None:
            new_balance = self.wallet.balance
        
        self.wallet = PaperWallet(
            balance=new_balance,
            available=new_balance,
        )
        self.orders.clear()
        self.positions.clear()
        self.pending_orders.clear()
        self.trade_history.clear()
        self.leverage_settings.clear()
        
        if self.enable_logging:
            logger.info(f"Wallet reset to ${new_balance}")
    
    # =========================================================================
    # Trade History
    # =========================================================================
    
    def get_trade_history(self, limit: int = 100) -> List[TradeRecord]:
        """Get trade history."""
        history = sorted(self.trade_history, key=lambda t: t.executed_at, reverse=True)
        return history[:limit]
    
    def get_position_history(self, limit: int = 100) -> List[PaperPosition]:
        """Get closed positions."""
        closed = [
            p for p in self.positions.values()
            if p.status == PaperPositionStatus.CLOSED
        ]
        closed.sort(key=lambda p: p.closed_at or p.opened_at, reverse=True)
        return closed[:limit]
    
    # =========================================================================
    # State Export/Import
    # =========================================================================
    
    def export_state(self) -> dict:
        """Export engine state for persistence."""
        return {
            "wallet": self.wallet.to_dict(),
            "orders": {k: v.to_dict() for k, v in self.orders.items()},
            "positions": {k: v.to_dict() for k, v in self.positions.items()},
            "trade_history": [t.to_dict() for t in self.trade_history],
            "pending_orders": self.pending_orders,
            "leverage_settings": self.leverage_settings,
            "exported_at": datetime.utcnow().isoformat(),
        }
    
    def import_state(self, state: dict) -> None:
        """Import engine state from persistence."""
        self.wallet = PaperWallet.from_dict(state["wallet"])
        self.orders = {k: PaperOrder.from_dict(v) for k, v in state.get("orders", {}).items()}
        self.positions = {k: PaperPosition.from_dict(v) for k, v in state.get("positions", {}).items()}
        self.trade_history = [TradeRecord.from_dict(t) for t in state.get("trade_history", [])]
        self.pending_orders = state.get("pending_orders", {})
        self.leverage_settings = state.get("leverage_settings", {})
        
        if self.enable_logging:
            logger.info(f"State imported: {len(self.positions)} positions, {len(self.orders)} orders")
    
    @classmethod
    def from_state(cls, state: dict, price_feed) -> "PaperTradingEngine":
        """
        Create a new engine from saved state.
        
        Args:
            state: Previously exported state dict
            price_feed: Price feed service instance
            
        Returns:
            New PaperTradingEngine with restored state
        """
        # Create engine with dummy balance (will be overwritten)
        engine = cls(
            initial_balance=Decimal("0"),
            price_feed=price_feed,
        )
        engine.import_state(state)
        return engine
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def get_statistics(self) -> dict:
        """Get trading statistics."""
        open_positions = self.list_open_positions()
        closed_positions = self.get_position_history(limit=1000)
        
        winning_trades = [p for p in closed_positions if p.realized_pnl > 0]
        losing_trades = [p for p in closed_positions if p.realized_pnl < 0]
        
        total_pnl = self.wallet.realized_pnl + self.wallet.unrealized_pnl
        
        return {
            "total_balance": str(self.wallet.balance),
            "available_balance": str(self.wallet.available),
            "locked_margin": str(self.wallet.locked_margin),
            "unrealized_pnl": str(self.wallet.unrealized_pnl),
            "realized_pnl": str(self.wallet.realized_pnl),
            "total_pnl": str(total_pnl),
            "total_fees_paid": str(self.wallet.total_fees_paid),
            "open_positions": len(open_positions),
            "total_trades": len(closed_positions),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": f"{(len(winning_trades) / len(closed_positions) * 100):.1f}%" if closed_positions else "N/A",
        }
