"""
Positions API Module
====================

Endpoints for viewing and managing futures positions.
"""

from typing import TYPE_CHECKING, Optional, List

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
        response = self._get(f"/futures/positions/{position_id}")
        return Position.from_dict(response.get("data", response))
    
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
    
    def get_history(
        self,
        page: int = 1,
        per_page: int = 50,
    ) -> List[Position]:
        """
        Get position history (closed positions).
        
        Args:
            page: Page number (default: 1)
            per_page: Items per page (default: 50)
            
        Returns:
            List[Position]: Historical positions
            
        Example:
            >>> history = client.positions.get_history()
            >>> profitable = [p for p in history if float(p.realized_pnl) > 0]
            >>> print(f"Win rate: {len(profitable)/len(history)*100:.1f}%")
        """
        response = self._get("/futures/positions/history", {
            "page": page,
            "per_page": per_page,
        })
        data = response.get("data", response)
        
        if isinstance(data, list):
            return [Position.from_dict(item) for item in data]
        
        items = data.get("items", data.get("data", []))
        return [Position.from_dict(item) for item in items]
