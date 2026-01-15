"""
Leverage API Module
===================

Endpoints for getting and setting leverage on futures positions.
Use trading symbols like "BTCUSDT", "XRPUSDT" directly.
"""

from typing import TYPE_CHECKING

from mudrex.api.base import BaseAPI
from mudrex.models import Leverage, MarginType

if TYPE_CHECKING:
    from mudrex.client import MudrexClient


class LeverageAPI(BaseAPI):
    """
    Leverage management endpoints.
    
    Use these methods to:
    - Get current leverage settings for a symbol
    - Set leverage and margin type for trading
    
    All methods accept trading symbols like "BTCUSDT", "XRPUSDT".
    
    Example:
        >>> client = MudrexClient(api_secret="...")
        >>> 
        >>> # Check current leverage
        >>> lev = client.leverage.get("BTCUSDT")
        >>> print(f"Current leverage: {lev.leverage}x")
        >>> 
        >>> # Set leverage before trading
        >>> client.leverage.set("XRPUSDT", leverage="10", margin_type="ISOLATED")
    
    Note:
        - Leverage must be within the asset's min/max range
        - Currently only ISOLATED margin type is supported
        - Changing leverage affects new orders only
    """
    
    def get(self, symbol: str) -> Leverage:
        """
        Get current leverage settings for a trading symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT", "XRPUSDT")
            
        Returns:
            Leverage: Current leverage and margin type settings.
                     Returns default (1x ISOLATED) if not previously set.
            
        Example:
            >>> leverage = client.leverage.get("XRPUSDT")
            >>> print(f"Leverage: {leverage.leverage}x")
            >>> print(f"Margin type: {leverage.margin_type.value}")
        """
        from mudrex.exceptions import MudrexAPIError
        
        try:
            response = self._get(f"/futures/{symbol}/leverage", use_symbol=True)
            data = response.get("data", response) if response else {}
            data["asset_id"] = symbol
            data["symbol"] = symbol
            return Leverage.from_dict(data)
        except MudrexAPIError as e:
            # If leverage not set, return default values
            if e.status_code == 400:
                return Leverage(
                    asset_id=symbol,
                    leverage="1",
                    margin_type=MarginType.ISOLATED,
                )
            raise
    
    def set(
        self,
        symbol: str,
        leverage: str,
        margin_type: str = "ISOLATED",
    ) -> Leverage:
        """
        Set leverage and margin type for a trading symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT", "XRPUSDT")
            leverage: Desired leverage (e.g., "5", "10", "20")
            margin_type: Margin type - currently only "ISOLATED" supported
            
        Returns:
            Leverage: Updated leverage settings
            
        Raises:
            MudrexValidationError: If leverage is out of allowed range
            
        Example:
            >>> # Set 10x leverage for XRP
            >>> result = client.leverage.set(
            ...     symbol="XRPUSDT",
            ...     leverage="10",
            ...     margin_type="ISOLATED"
            ... )
            >>> print(f"New leverage: {result.leverage}x")
            
        Note:
            Check asset specifications for min/max leverage limits:
            >>> asset = client.assets.get("XRPUSDT")
            >>> print(f"Allowed: {asset.min_leverage}x - {asset.max_leverage}x")
        """
        # Validate margin type
        margin_type_enum = MarginType(margin_type.upper())
        
        response = self._post(
            f"/futures/{symbol}/leverage", 
            {
                "margin_type": margin_type_enum.value,
                "leverage": leverage,
            },
            use_symbol=True
        )
        
        data = response.get("data", {})
        data["asset_id"] = symbol
        data["symbol"] = symbol
        data["leverage"] = leverage
        data["margin_type"] = margin_type_enum.value
        
        return Leverage.from_dict(data)
