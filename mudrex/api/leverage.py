"""
Leverage API Module
===================

Endpoints for getting and setting leverage on futures positions.
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
    - Get current leverage settings for an asset
    - Set leverage and margin type for trading
    
    Example:
        >>> client = MudrexClient(api_secret="...")
        >>> 
        >>> # Check current leverage
        >>> lev = client.leverage.get("BTCUSDT")
        >>> print(f"Current leverage: {lev.leverage}x")
        >>> 
        >>> # Set leverage before trading
        >>> client.leverage.set("BTCUSDT", leverage="10", margin_type="ISOLATED")
    
    Note:
        - Leverage must be within the asset's min/max range
        - Currently only ISOLATED margin type is supported
        - Changing leverage affects new orders only
    """
    
    def get(self, asset_id: str) -> Leverage:
        """
        Get current leverage settings for an asset.
        
        Args:
            asset_id: Asset identifier (e.g., "BTCUSDT")
            
        Returns:
            Leverage: Current leverage and margin type settings.
                     Returns default (1x ISOLATED) if not previously set.
            
        Example:
            >>> leverage = client.leverage.get("BTCUSDT")
            >>> print(f"Leverage: {leverage.leverage}x")
            >>> print(f"Margin type: {leverage.margin_type.value}")
            
        Note:
            If leverage hasn't been set for this asset, the API may return
            a 400 error. In this case, use set() to configure leverage first.
        """
        from mudrex.exceptions import MudrexAPIError
        
        try:
            response = self._get(f"/futures/{asset_id}/leverage")
            data = response.get("data", response) if response else {}
            data["asset_id"] = asset_id
            return Leverage.from_dict(data)
        except MudrexAPIError as e:
            # If leverage not set, return default values
            if e.status_code == 400:
                return Leverage(
                    asset_id=asset_id,
                    leverage="1",
                    margin_type=MarginType.ISOLATED,
                )
            raise
    
    def set(
        self,
        asset_id: str,
        leverage: str,
        margin_type: str = "ISOLATED",
    ) -> Leverage:
        """
        Set leverage and margin type for an asset.
        
        Args:
            asset_id: Asset identifier (e.g., "BTCUSDT")
            leverage: Desired leverage (e.g., "5", "10", "20")
            margin_type: Margin type - currently only "ISOLATED" supported
            
        Returns:
            Leverage: Updated leverage settings
            
        Raises:
            MudrexValidationError: If leverage is out of allowed range
            
        Example:
            >>> # Set 10x leverage with isolated margin
            >>> result = client.leverage.set(
            ...     asset_id="BTCUSDT",
            ...     leverage="10",
            ...     margin_type="ISOLATED"
            ... )
            >>> print(f"New leverage: {result.leverage}x")
            
        Note:
            Check asset specifications for min/max leverage limits:
            >>> asset = client.assets.get("BTCUSDT")
            >>> print(f"Allowed: {asset.min_leverage}x - {asset.max_leverage}x")
        """
        # Validate margin type
        margin_type_enum = MarginType(margin_type.upper())
        
        response = self._post(f"/futures/{asset_id}/leverage", {
            "margin_type": margin_type_enum.value,
            "leverage": leverage,
        })
        
        data = response.get("data", {})
        data["asset_id"] = asset_id
        data["leverage"] = leverage
        data["margin_type"] = margin_type_enum.value
        
        return Leverage.from_dict(data)
