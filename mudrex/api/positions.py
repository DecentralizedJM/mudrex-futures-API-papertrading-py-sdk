"""
Positions API Module
====================

Endpoints for viewing and managing futures positions.
"""

from typing import TYPE_CHECKING, Optional, List, Dict, Any

from mudrex.api.base import BaseAPI
from mudrex.models import Position, RiskOrder

if TYPE_CHECKING:
    from mudrex.client import MudrexClient


class PositionsAPI(BaseAPI):
    """
    Position management endpoints.
    
    Use these methods to:
    - View open positions
    - Close or partially close positions
    - Set stop-loss and take-profit levels
    - Reverse position direction
    - Add or reduce margin
    - Get liquidation price
    - View position history
    
    Example:
        >>> client = MudrexClient(api_secret="...")
        >>> 
        >>> # View open positions
        >>> positions = client.positions.list_open()
        >>> for pos in positions:
        ...     print(f"{pos.symbol}: {pos.side.value} {pos.quantity}")
        ...     print(f"  Entry: {pos.entry_price}, PnL: {pos.unrealized_pnl}")
        >>> 
        >>> # Set stop-loss on a position
        >>> client.positions.set_stoploss("pos_123", "95000")
        >>>
        >>> # Add margin to a position
        >>> client.positions.add_margin("pos_123", "50.00")
    """
    
    def list_open(self) -> List[Position]:
        """
        Get all open positions.
        
        Returns:
            List[Position]: List of open positions
            
        Example:
            >>> positions = client.positions.list_open()
            >>> for pos in positions:
            ...     print(f"{pos.symbol}: {pos.side.value}")
            ...     print(f"  Quantity: {pos.quantity}")
            ...     print(f"  Entry: ${pos.entry_price}")
            ...     print(f"  Current: ${pos.mark_price}")
            ...     print(f"  PnL: ${pos.unrealized_pnl} ({pos.pnl_percentage:.2f}%)")
        """
        response = self._get("/futures/positions")
        
        # Handle None or empty responses
        if not response:
            return []
        
        data = response.get("data", response)
        
        # Handle None data
        if not data:
            return []
        
        if isinstance(data, list):
            return [Position.from_dict(item) for item in data if item]
        
        items = data.get("items", data.get("data", []))
        if not items:
            return []
        return [Position.from_dict(item) for item in items if item]
    
    def get(self, position_id: str) -> Position:
        """
        Get details of a specific position.
        
        Args:
            position_id: The position ID to retrieve
            
        Returns:
            Position: Position details
        """
        # API uses query parameter, not path parameter
        response = self._get("/futures/positions", {"id": position_id})
        data = response.get("data", response)
        
        # Response may be a list with single item or the position directly
        if isinstance(data, list):
            if data:
                return Position.from_dict(data[0])
            raise ValueError(f"Position {position_id} not found")
        return Position.from_dict(data)
    
    def close(self, position_id: str) -> bool:
        """
        Fully close a position.
        
        Args:
            position_id: The position ID to close
            
        Returns:
            bool: True if closed successfully
            
        Example:
            >>> positions = client.positions.list_open()
            >>> for pos in positions:
            ...     if float(pos.unrealized_pnl) > 100:  # Take profit > $100
            ...         client.positions.close(pos.position_id)
            ...         print(f"Closed {pos.symbol} with ${pos.unrealized_pnl} profit")
        """
        response = self._post(f"/futures/positions/{position_id}/close")
        return response.get("success", False)
    
    def close_partial(self, position_id: str, quantity: str) -> Position:
        """
        Partially close a position.
        
        Args:
            position_id: The position ID to partially close
            quantity: Amount to close
            
        Returns:
            Position: Updated position after partial close
            
        Example:
            >>> pos = client.positions.list_open()[0]
            >>> # Close half the position
            >>> half_qty = str(float(pos.quantity) / 2)
            >>> updated = client.positions.close_partial(pos.position_id, half_qty)
            >>> print(f"Remaining: {updated.quantity}")
        """
        response = self._post(f"/futures/positions/{position_id}/close/partial", {
            "quantity": quantity,
        })
        return Position.from_dict(response.get("data", response))
    
    def reverse(self, position_id: str) -> Position:
        """
        Reverse a position (LONG -> SHORT or SHORT -> LONG).
        
        This closes the current position and opens an opposite one
        with the same quantity.
        
        Args:
            position_id: The position ID to reverse
            
        Returns:
            Position: New reversed position
            
        Example:
            >>> pos = client.positions.list_open()[0]
            >>> print(f"Before: {pos.side.value}")
            >>> reversed_pos = client.positions.reverse(pos.position_id)
            >>> print(f"After: {reversed_pos.side.value}")
        """
        response = self._post(f"/futures/positions/{position_id}/reverse")
        return Position.from_dict(response.get("data", response))
    
    def set_risk_order(
        self,
        position_id: str,
        stoploss_price: Optional[str] = None,
        takeprofit_price: Optional[str] = None,
    ) -> bool:
        """
        Set stop-loss and/or take-profit for a position.
        
        Args:
            position_id: The position ID
            stoploss_price: Stop-loss price (optional)
            takeprofit_price: Take-profit price (optional)
            
        Returns:
            bool: True if set successfully
            
        Example:
            >>> # Set both SL and TP
            >>> client.positions.set_risk_order(
            ...     position_id="pos_123",
            ...     stoploss_price="95000",
            ...     takeprofit_price="110000"
            ... )
        """
        risk_order = RiskOrder(
            position_id=position_id,
            stoploss_price=stoploss_price,
            takeprofit_price=takeprofit_price,
        )
        response = self._post(
            f"/futures/positions/{position_id}/riskorder",
            risk_order.to_dict()
        )
        return response.get("success", False)
    
    def set_stoploss(self, position_id: str, price: str) -> bool:
        """
        Set stop-loss for a position.
        
        Args:
            position_id: The position ID
            price: Stop-loss price
            
        Returns:
            bool: True if set successfully
            
        Example:
            >>> client.positions.set_stoploss("pos_123", "95000")
        """
        return self.set_risk_order(position_id, stoploss_price=price)
    
    def set_takeprofit(self, position_id: str, price: str) -> bool:
        """
        Set take-profit for a position.
        
        Args:
            position_id: The position ID
            price: Take-profit price
            
        Returns:
            bool: True if set successfully
            
        Example:
            >>> client.positions.set_takeprofit("pos_123", "110000")
        """
        return self.set_risk_order(position_id, takeprofit_price=price)
    
    def edit_risk_order(
        self,
        position_id: str,
        stoploss_price: Optional[str] = None,
        takeprofit_price: Optional[str] = None,
    ) -> bool:
        """
        Edit existing stop-loss and/or take-profit levels.
        
        Args:
            position_id: The position ID
            stoploss_price: New stop-loss price (optional)
            takeprofit_price: New take-profit price (optional)
            
        Returns:
            bool: True if updated successfully
        """
        data = {}
        if stoploss_price is not None:
            data["stoploss_price"] = stoploss_price
        if takeprofit_price is not None:
            data["takeprofit_price"] = takeprofit_price
        
        response = self._patch(f"/futures/positions/{position_id}/riskorder", data)
        return response.get("success", False)
    
    def get_history(self, limit: Optional[int] = None) -> List[Position]:
        """
        Get position history (all closed positions).
        
        Args:
            limit: Maximum positions to return. If None, returns ALL (no limit).
            
        Returns:
            List[Position]: Historical/closed positions (newest first)
            
        Examples:
            >>> # Get ALL position history (no limit)
            >>> all_history = client.positions.get_history()
            >>> print(f"Total closed positions: {len(all_history)}")
            
            >>> # Get only last 50
            >>> recent = client.positions.get_history(limit=50)
            
            >>> # Calculate win rate
            >>> history = client.positions.get_history()
            >>> profitable = [p for p in history if float(p.realized_pnl) > 0]
            >>> if history:
            ...     win_rate = len(profitable) / len(history) * 100
            ...     print(f"Win rate: {win_rate:.1f}%")
        """
        all_positions = []
        page = 1
        per_page = 100  # Max per request
        
        while True:
            response = self._get("/futures/positions/history", {
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
            
            all_positions.extend([Position.from_dict(item) for item in items])
            
            # Check if we've reached the limit
            if limit and len(all_positions) >= limit:
                return all_positions[:limit]
            
            # Check if there are more pages
            if len(items) < per_page:
                break
            
            page += 1
        
        return all_positions
    
    def get_liquidation_price(self, position_id: str) -> Dict[str, Any]:
        """
        Get the liquidation price for a specific position.
        
        The liquidation price is the price at which the position will be
        automatically closed to prevent further losses beyond the margin.
        
        Args:
            position_id: The position ID to get liquidation price for
            
        Returns:
            Dict containing liquidation price information:
            - liquidation_price: The price at which liquidation would occur
            - symbol: The trading symbol
            - position_id: The position ID
            
        Example:
            >>> pos = client.positions.list_open()[0]
            >>> liq_info = client.positions.get_liquidation_price(pos.position_id)
            >>> print(f"Liquidation price: ${liq_info.get('liquidation_price')}")
            
        Note:
            For LONG positions, liquidation occurs when price drops below this level.
            For SHORT positions, liquidation occurs when price rises above this level.
        """
        # Get the position data which includes liquidation_price
        position = self.get(position_id)
        return {
            "position_id": position.position_id,
            "symbol": position.symbol,
            "liquidation_price": position.liquidation_price,
            "entry_price": position.entry_price,
            "mark_price": position.mark_price,
            "side": position.side.value,
        }
    
    def add_margin(self, position_id: str, amount: str) -> Dict[str, Any]:
        """
        Add margin to an existing position.
        
        Adding margin reduces the liquidation risk by increasing the buffer
        between the current price and the liquidation price.
        
        Args:
            position_id: The position ID to add margin to
            amount: Amount of margin to add (positive value, as string for precision)
            
        Returns:
            Dict containing updated position/margin information
            
        Example:
            >>> pos = client.positions.list_open()[0]
            >>> # Add $50 margin to reduce liquidation risk
            >>> result = client.positions.add_margin(pos.position_id, "50.00")
            >>> print(f"New margin: ${result.get('margin')}")
            
        Note:
            The amount will be deducted from your futures wallet balance.
        """
        return self._adjust_margin(position_id, amount, action="add")
    
    def reduce_margin(self, position_id: str, amount: str) -> Dict[str, Any]:
        """
        Reduce margin from an existing position.
        
        Reducing margin increases your available balance but also increases
        liquidation risk. Use with caution.
        
        Args:
            position_id: The position ID to reduce margin from
            amount: Amount of margin to reduce (positive value, as string for precision)
            
        Returns:
            Dict containing updated position/margin information
            
        Raises:
            MudrexValidationError: If the reduction would cause immediate liquidation
            
        Example:
            >>> pos = client.positions.list_open()[0]
            >>> # Reduce margin by $25 to free up balance
            >>> result = client.positions.reduce_margin(pos.position_id, "25.00")
            >>> print(f"New margin: ${result.get('margin')}")
            
        Warning:
            Reducing margin increases liquidation risk. Ensure you have
            sufficient margin to avoid liquidation.
        """
        return self._adjust_margin(position_id, amount, action="reduce")
    
    def _adjust_margin(self, position_id: str, amount: str, action: str = "add") -> Dict[str, Any]:
        """
        Internal method to adjust margin on a position.
        
        Args:
            position_id: The position ID
            amount: Amount to adjust (always positive)
            action: "add" or "reduce"
            
        Returns:
            Dict containing the API response
        """
        endpoint = f"/futures/positions/{position_id}/add-margin"
        response = self._post(endpoint, {
            "margin": float(amount),  # API expects 'margin' not 'amount'
        })
        return response.get("data", response)
