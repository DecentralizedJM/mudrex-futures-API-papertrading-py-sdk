"""
Orders API Module
=================

Endpoints for creating, managing, and tracking futures orders.
Use symbols like "BTCUSDT", "XRPUSDT", "ETHUSDT" directly.
"""

from typing import TYPE_CHECKING, Optional, List, Union

from mudrex.api.base import BaseAPI
from mudrex.models import Order, OrderRequest, OrderType, TriggerType, PaginatedResponse

if TYPE_CHECKING:
    from mudrex.client import MudrexClient


class OrdersAPI(BaseAPI):
    """
    Order management endpoints.
    
    Use these methods to:
    - Place market and limit orders using trading symbols
    - View open orders
    - Get order details and history
    - Cancel or amend existing orders
    
    All methods accept trading symbols like "BTCUSDT", "XRPUSDT", "ETHUSDT".
    
    Example:
        >>> client = MudrexClient(api_secret="...")
        >>> 
        >>> # Place a market order (uses symbol directly!)
        >>> order = client.orders.create_market_order(
        ...     symbol="XRPUSDT",  # Trading symbol
        ...     side="LONG",
        ...     quantity="100",
        ...     leverage="5"
        ... )
        >>> print(f"Order placed: {order.order_id}")
    """
    
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
            symbol: Trading symbol (e.g., "BTCUSDT", "XRPUSDT", "ETHUSDT")
            side: Order direction - "LONG" or "SHORT"
            quantity: Order quantity (as string for precision)
            leverage: Leverage to use (default: "1")
            stoploss_price: Optional stop-loss price
            takeprofit_price: Optional take-profit price
            reduce_only: If True, only reduces existing position
            
        Returns:
            Order: Created order details
            
        Example:
            >>> # Simple market buy
            >>> order = client.orders.create_market_order(
            ...     symbol="BTCUSDT",
            ...     side="LONG",
            ...     quantity="0.001",
            ...     leverage="10"
            ... )
            >>> 
            >>> # Trade XRP with SL/TP
            >>> order = client.orders.create_market_order(
            ...     symbol="XRPUSDT",
            ...     side="LONG",
            ...     quantity="100",
            ...     leverage="5",
            ...     stoploss_price="2.00",
            ...     takeprofit_price="3.00"
            ... )
        """
        return self._create_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            trigger_type=TriggerType.MARKET,
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
            symbol: Trading symbol (e.g., "BTCUSDT", "XRPUSDT", "ETHUSDT")
            side: Order direction - "LONG" or "SHORT"
            quantity: Order quantity (as string for precision)
            price: Limit price (order triggers at this price)
            leverage: Leverage to use (default: "1")
            stoploss_price: Optional stop-loss price
            takeprofit_price: Optional take-profit price
            reduce_only: If True, only reduces existing position
            
        Returns:
            Order: Created order details
            
        Example:
            >>> # Limit buy XRP when it dips
            >>> order = client.orders.create_limit_order(
            ...     symbol="XRPUSDT",
            ...     side="LONG",
            ...     quantity="100",
            ...     price="2.00",  # Buy when XRP drops to $2
            ...     leverage="5"
            ... )
        """
        return self._create_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            trigger_type=TriggerType.LIMIT,
            price=price,
            leverage=leverage,
            stoploss_price=stoploss_price,
            takeprofit_price=takeprofit_price,
            reduce_only=reduce_only,
        )
    
    def _create_order(
        self,
        symbol: str,
        side: Union[str, OrderType],
        quantity: str,
        trigger_type: TriggerType,
        leverage: str = "1",
        price: Optional[str] = None,
        stoploss_price: Optional[str] = None,
        takeprofit_price: Optional[str] = None,
        reduce_only: bool = False,
    ) -> Order:
        """Internal method to create orders with symbol support."""
        # Convert side to OrderType if string
        if isinstance(side, str):
            side = OrderType(side.upper())
        
        # Mudrex API requires order_price even for MARKET orders!
        # If not provided, fetch current market price
        if price is None and trigger_type == TriggerType.MARKET:
            # Import here to avoid circular dependency
            from mudrex.api.assets import AssetsAPI
            assets_api = AssetsAPI(self._client)
            asset = assets_api.get(symbol)
            # Use the price from asset data, or fallback to a reasonable value
            # Note: The asset response may not have 'price' field populated
            # In that case, we'll use a placeholder that the API accepts
            price = "999999999"  # Placeholder for market orders
        
        # Build order request
        request = OrderRequest(
            quantity=quantity,
            order_type=side,
            trigger_type=trigger_type,
            leverage=leverage,
            order_price=price,
            is_stoploss=stoploss_price is not None,
            stoploss_price=stoploss_price,
            is_takeprofit=takeprofit_price is not None,
            takeprofit_price=takeprofit_price,
            reduce_only=reduce_only,
        )
        
        # Use symbol with is_symbol parameter
        response = self._post(
            f"/futures/{symbol}/order", 
            request.to_dict(),
            use_symbol=True  # Critical: tells API we're using symbol, not asset_id
        )
        
        data = response.get("data", response)
        data["asset_id"] = symbol
        data["symbol"] = symbol
        
        return Order.from_dict(data)
    
    def create(self, symbol: str, request: OrderRequest) -> Order:
        """
        Create an order using an OrderRequest object.
        
        This is useful when you need full control over order parameters.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            request: OrderRequest with all order parameters
            
        Returns:
            Order: Created order details
        """
        response = self._post(
            f"/futures/{symbol}/order", 
            request.to_dict(),
            use_symbol=True
        )
        data = response.get("data", response)
        data["asset_id"] = symbol
        data["symbol"] = symbol
        return Order.from_dict(data)
    
    def list_open(self) -> List[Order]:
        """
        Get all open orders.
        
        Returns:
            List[Order]: List of open orders
            
        Example:
            >>> orders = client.orders.list_open()
            >>> for order in orders:
            ...     print(f"{order.symbol}: {order.order_type.value} {order.quantity}")
        """
        response = self._get("/futures/orders")
        data = response.get("data", response)
        
        if isinstance(data, list):
            return [Order.from_dict(item) for item in data]
        
        items = data.get("items", data.get("data", []))
        return [Order.from_dict(item) for item in items]
    
    def get(self, order_id: str) -> Order:
        """
        Get details of a specific order.
        
        Args:
            order_id: The order ID to retrieve
            
        Returns:
            Order: Order details
        """
        response = self._get(f"/futures/orders/{order_id}")
        return Order.from_dict(response.get("data", response))
    
    def get_history(self, limit: int = 100) -> List[Order]:
        """
        Get order history.
        
        Args:
            limit: Maximum number of orders to return (default: 100)
            
        Returns:
            List[Order]: Historical orders
            
        Example:
            >>> history = client.orders.get_history()
            >>> print(f"Total orders: {len(history)}")
        """
        all_orders = []
        page = 1
        per_page = min(limit, 100)
        
        while len(all_orders) < limit:
            response = self._get("/futures/orders/history", {
                "page": page,
                "per_page": per_page,
            })
            data = response.get("data", response)
            
            if isinstance(data, list):
                items = data
            else:
                items = data.get("items", data.get("data", []))
            
            if not items:
                break
            
            all_orders.extend([Order.from_dict(item) for item in items])
            
            if len(items) < per_page:
                break
            
            page += 1
        
        return all_orders[:limit]
    
    def cancel(self, order_id: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            order_id: The order ID to cancel
            
        Returns:
            bool: True if cancelled successfully
        """
        response = self._delete(f"/futures/orders/{order_id}")
        return response.get("success", False)
    
    def amend(
        self,
        order_id: str,
        price: Optional[str] = None,
        quantity: Optional[str] = None,
    ) -> Order:
        """
        Amend an existing order.
        
        Args:
            order_id: The order ID to amend
            price: New price (optional)
            quantity: New quantity (optional)
            
        Returns:
            Order: Updated order details
        """
        data = {}
        if price is not None:
            data["order_price"] = price
        if quantity is not None:
            data["quantity"] = quantity
        
        response = self._patch(f"/futures/orders/{order_id}", data)
        return Order.from_dict(response.get("data", response))
