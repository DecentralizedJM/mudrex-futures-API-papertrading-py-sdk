"""
Orders API Module
=================

Endpoints for creating, managing, and tracking futures orders.

Supports both:
- Symbol-first trading: Use symbols like "BTCUSDT", "XRPUSDT" (recommended)
- Asset ID trading: Use internal asset IDs (legacy/backward compatible)
"""

from typing import TYPE_CHECKING, Optional, List, Union

from mudrex.api.base import BaseAPI
from mudrex.models import Order, OrderRequest, OrderType, TriggerType, PaginatedResponse

if TYPE_CHECKING:
    from mudrex.client import MudrexClient


class OrdersAPI(BaseAPI):
    """
    Order management endpoints.
    
    Supports two ways to identify assets:
    1. **Symbol (recommended)**: Use trading symbols like "BTCUSDT", "XRPUSDT"
    2. **Asset ID (legacy)**: Use internal Mudrex asset IDs for backward compatibility
    
    Examples:
        >>> # Using symbol (recommended)
        >>> order = client.orders.create_market_order(
        ...     symbol="BTCUSDT",
        ...     side="LONG",
        ...     quantity="0.001",
        ...     leverage="10"
        ... )
        
        >>> # Using asset_id (legacy/backward compatible)
        >>> order = client.orders.create_market_order(
        ...     asset_id="01903a7b-bf65-707d-a7dc-d7b84c3c756c",
        ...     side="LONG", 
        ...     quantity="0.001",
        ...     leverage="10"
        ... )
    """
    
    def _resolve_identifier(
        self, 
        symbol: Optional[str] = None, 
        asset_id: Optional[str] = None
    ) -> tuple:
        """
        Resolve asset identifier - supports both symbol and asset_id.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            asset_id: Internal asset ID (UUID format)
            
        Returns:
            Tuple of (identifier, use_symbol_flag)
            
        Raises:
            ValueError: If neither or both are provided
        """
        if symbol and asset_id:
            raise ValueError(
                "Please provide either 'symbol' or 'asset_id', not both. "
                "Symbol is recommended (e.g., symbol='BTCUSDT')"
            )
        if not symbol and not asset_id:
            raise ValueError(
                "Please provide 'symbol' (recommended) or 'asset_id'. "
                "Example: symbol='BTCUSDT' or asset_id='01903a7b-...'"
            )
        
        if symbol:
            return symbol, True
        return asset_id, False
    
    def create_market_order(
        self,
        side: Union[str, OrderType],
        quantity: str,
        leverage: str = "1",
        *,
        symbol: Optional[str] = None,
        asset_id: Optional[str] = None,
        stoploss_price: Optional[str] = None,
        takeprofit_price: Optional[str] = None,
        reduce_only: bool = False,
    ) -> Order:
        """
        Place a market order (executes immediately at current price).
        
        Args:
            side: Order direction - "LONG" or "SHORT"
            quantity: Order quantity (as string for precision)
            leverage: Leverage to use (default: "1")
            symbol: Trading symbol, e.g., "BTCUSDT" (recommended)
            asset_id: Internal asset ID (legacy, for backward compatibility)
            stoploss_price: Optional stop-loss price
            takeprofit_price: Optional take-profit price
            reduce_only: If True, only reduces existing position
            
        Returns:
            Order: Created order details with order_id, status, etc.
            
        Examples:
            >>> # Using symbol (recommended)
            >>> order = client.orders.create_market_order(
            ...     symbol="BTCUSDT",
            ...     side="LONG",
            ...     quantity="0.001",
            ...     leverage="10"
            ... )
            >>> print(f"Order placed! ID: {order.order_id}")
            
            >>> # Using asset_id (backward compatible)
            >>> order = client.orders.create_market_order(
            ...     asset_id="01903a7b-bf65-707d-a7dc-d7b84c3c756c",
            ...     side="LONG",
            ...     quantity="0.001",
            ...     leverage="10"
            ... )
            
            >>> # With stop-loss and take-profit
            >>> order = client.orders.create_market_order(
            ...     symbol="XRPUSDT",
            ...     side="LONG",
            ...     quantity="100",
            ...     leverage="5",
            ...     stoploss_price="2.00",
            ...     takeprofit_price="3.00"
            ... )
        """
        identifier, use_symbol = self._resolve_identifier(symbol, asset_id)
        
        return self._create_order(
            identifier=identifier,
            use_symbol=use_symbol,
            side=side,
            quantity=quantity,
            trigger_type=TriggerType.MARKET,
            leverage=leverage,
            stoploss_price=stoploss_price,
            takeprofit_price=takeprofit_price,
            reduce_only=reduce_only,
        )
    
    def create_market_order_with_amount(
        self,
        side: Union[str, OrderType],
        amount: str,
        leverage: str = "1",
        *,
        symbol: Optional[str] = None,
        asset_id: Optional[str] = None,
        stoploss_price: Optional[str] = None,
        takeprofit_price: Optional[str] = None,
        reduce_only: bool = False,
    ) -> Order:
        """
        Place a market order specified by quote currency amount (USDT).
        
        Automatically calculates the correct quantity based on current price.
        
        Args:
            side: Order direction - "LONG" or "SHORT"
            amount: Amount in USDT to trade (e.g., "100" for $100)
            leverage: Leverage to use (default: "1")
            symbol: Trading symbol, e.g., "BTCUSDT" (recommended)
            asset_id: Internal asset ID (legacy, for backward compatibility)
            stoploss_price: Optional stop-loss price
            takeprofit_price: Optional take-profit price
            reduce_only: If True, only reduces existing position
            
        Returns:
            Order: Created order details
            
        Example:
            >>> # Buy $50 worth of BTC
            >>> order = client.orders.create_market_order_with_amount(
            ...     symbol="BTCUSDT",
            ...     side="LONG",
            ...     amount="50",
            ...     leverage="10"
            ... )
        """
        identifier, use_symbol = self._resolve_identifier(symbol, asset_id)
        
        # Fetch asset info to get current price
        if use_symbol:
            asset = self._client.assets.get(identifier)
        else:
            asset = self._client.assets.get_by_id(identifier)
        
        if not asset.price:
            raise ValueError(
                f"Could not get current price for this asset. "
                f"Unable to calculate quantity from amount ${amount}."
            )
        
        try:
            price = float(asset.price)
            quantity_step = float(asset.quantity_step) if asset.quantity_step else 0.0
            target_amount = float(amount)
        except (ValueError, TypeError):
            raise ValueError(
                f"Invalid price data for asset. "
                f"Price: {asset.price}, Quantity step: {asset.quantity_step}"
            )

        from mudrex.utils import calculate_order_from_usd
        qty, _ = calculate_order_from_usd(target_amount, price, quantity_step)
        
        if qty <= 0:
            raise ValueError(
                f"Order amount too small. ${amount} at price ${price} "
                f"results in quantity below minimum."
            )
        
        return self.create_market_order(
            symbol=symbol,
            asset_id=asset_id,
            side=side,
            quantity=str(qty),
            leverage=leverage,
            stoploss_price=stoploss_price,
            takeprofit_price=takeprofit_price,
            reduce_only=reduce_only,
        )

    def create_limit_order(
        self,
        side: Union[str, OrderType],
        quantity: str,
        price: str,
        leverage: str = "1",
        *,
        symbol: Optional[str] = None,
        asset_id: Optional[str] = None,
        stoploss_price: Optional[str] = None,
        takeprofit_price: Optional[str] = None,
        reduce_only: bool = False,
    ) -> Order:
        """
        Place a limit order (executes when price reaches target).
        
        Args:
            side: Order direction - "LONG" or "SHORT"
            quantity: Order quantity (as string for precision)
            price: Limit price (order triggers when market reaches this price)
            leverage: Leverage to use (default: "1")
            symbol: Trading symbol, e.g., "BTCUSDT" (recommended)
            asset_id: Internal asset ID (legacy, for backward compatibility)
            stoploss_price: Optional stop-loss price
            takeprofit_price: Optional take-profit price
            reduce_only: If True, only reduces existing position
            
        Returns:
            Order: Created order details
            
        Examples:
            >>> # Limit buy - order triggers when price drops to $95,000
            >>> order = client.orders.create_limit_order(
            ...     symbol="BTCUSDT",
            ...     side="LONG",
            ...     quantity="0.001",
            ...     price="95000",
            ...     leverage="10"
            ... )
            
            >>> # Using asset_id (backward compatible)
            >>> order = client.orders.create_limit_order(
            ...     asset_id="01903a7b-bf65-707d-a7dc-d7b84c3c756c",
            ...     side="LONG",
            ...     quantity="0.001",
            ...     price="95000",
            ...     leverage="10"
            ... )
        """
        identifier, use_symbol = self._resolve_identifier(symbol, asset_id)
        
        return self._create_order(
            identifier=identifier,
            use_symbol=use_symbol,
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
        identifier: str,
        use_symbol: bool,
        side: Union[str, OrderType],
        quantity: str,
        trigger_type: TriggerType,
        leverage: str = "1",
        price: Optional[str] = None,
        stoploss_price: Optional[str] = None,
        takeprofit_price: Optional[str] = None,
        reduce_only: bool = False,
    ) -> Order:
        """Internal method to create orders with smart quantity handling."""
        # Convert side to OrderType if string
        if isinstance(side, str):
            side = OrderType(side.upper())
        
        # Fetch asset info for proper rounding
        try:
            if use_symbol:
                asset = self._client.assets.get(identifier)
            else:
                asset = self._client.assets.get_by_id(identifier)
            
            quantity_step = float(asset.quantity_step) if asset.quantity_step else None
            
            # Auto-round quantity to match asset's quantity_step
            if quantity_step and quantity_step > 0:
                raw_qty = float(quantity)
                rounded_qty = round(raw_qty / quantity_step) * quantity_step
                precision = len(str(quantity_step).split('.')[-1]) if '.' in str(quantity_step) else 0
                quantity = str(round(rounded_qty, precision))
            
            # Auto-round price to match asset's price_step
            if price and asset.price_step:
                price_step = float(asset.price_step)
                if price_step > 0:
                    raw_price = float(price)
                    rounded_price = round(raw_price / price_step) * price_step
                    price_precision = len(str(asset.price_step).split('.')[-1]) if '.' in str(asset.price_step) else 0
                    price = str(round(rounded_price, price_precision))
        except Exception:
            pass  # Use values as-is if asset fetch fails
        
        # Mudrex API requires order_price even for MARKET orders
        if price is None and trigger_type == TriggerType.MARKET:
            price = "999999999"
        
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
        
        response = self._post(
            f"/futures/{identifier}/order", 
            request.to_dict(),
            use_symbol=use_symbol
        )
        
        data = response.get("data", response)
        # Ensure both fields are populated for consistency
        if use_symbol:
            data["symbol"] = identifier
            data["asset_id"] = data.get("asset_id", identifier)
        else:
            data["asset_id"] = identifier
            data["symbol"] = data.get("symbol", "")
        
        return Order.from_dict(data)
    
    def create(
        self, 
        request: OrderRequest,
        *,
        symbol: Optional[str] = None,
        asset_id: Optional[str] = None,
    ) -> Order:
        """
        Create an order using an OrderRequest object.
        
        Use this for full control over order parameters.
        
        Args:
            request: OrderRequest with all order parameters
            symbol: Trading symbol (recommended)
            asset_id: Internal asset ID (legacy)
            
        Returns:
            Order: Created order details
        """
        identifier, use_symbol = self._resolve_identifier(symbol, asset_id)
        
        response = self._post(
            f"/futures/{identifier}/order", 
            request.to_dict(),
            use_symbol=use_symbol
        )
        data = response.get("data", response)
        
        if use_symbol:
            data["symbol"] = identifier
        else:
            data["asset_id"] = identifier
            
        return Order.from_dict(data)
    
    def list_open(self) -> List[Order]:
        """
        Get all open orders.
        
        Returns:
            List[Order]: List of all your open/pending orders
            
        Example:
            >>> orders = client.orders.list_open()
            >>> print(f"You have {len(orders)} open orders")
            >>> for order in orders:
            ...     print(f"  {order.symbol}: {order.order_type.value} {order.quantity}")
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
            Order: Complete order details
        """
        response = self._get(f"/futures/orders/{order_id}")
        return Order.from_dict(response.get("data", response))
    
    def get_history(self, limit: Optional[int] = None) -> List[Order]:
        """
        Get order history (all past orders).
        
        Args:
            limit: Maximum number of orders to return. 
                   If None, returns ALL orders (no limit).
            
        Returns:
            List[Order]: Historical orders (newest first)
            
        Examples:
            >>> # Get all order history
            >>> all_orders = client.orders.get_history()
            >>> print(f"Total orders ever: {len(all_orders)}")
            
            >>> # Get last 50 orders only
            >>> recent = client.orders.get_history(limit=50)
        """
        all_orders = []
        page = 1
        per_page = 100  # Max per page
        
        while True:
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
            
            # Check if we've reached the limit
            if limit and len(all_orders) >= limit:
                return all_orders[:limit]
            
            # Check if there are more pages
            if len(items) < per_page:
                break
            
            page += 1
        
        return all_orders
    
    def cancel(self, order_id: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            order_id: The order ID to cancel
            
        Returns:
            bool: True if cancelled successfully
            
        Example:
            >>> success = client.orders.cancel("order_123")
            >>> if success:
            ...     print("Order cancelled!")
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
        Amend/modify an existing open order.
        
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
