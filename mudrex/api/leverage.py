"""
Leverage API Module
===================

Endpoints for getting and setting leverage on futures positions.

Supports both:
- Symbol-first trading: Use symbols like "BTCUSDT", "XRPUSDT" (recommended)
- Asset ID trading: Use internal asset IDs (legacy/backward compatible)
"""

from typing import TYPE_CHECKING, Optional

from mudrex.api.base import BaseAPI
from mudrex.models import Leverage, MarginType

if TYPE_CHECKING:
    from mudrex.client import MudrexClient


class LeverageAPI(BaseAPI):
    """
    Leverage management endpoints.
    
    Supports two ways to identify assets:
    1. **Symbol (recommended)**: Use trading symbols like "BTCUSDT", "XRPUSDT"
    2. **Asset ID (legacy)**: Use internal Mudrex asset IDs for backward compatibility
    
    Examples:
        >>> # Using symbol (recommended)
        >>> leverage = client.leverage.get(symbol="BTCUSDT")
        >>> print(f"Current leverage: {leverage.leverage}x")
        
        >>> # Set leverage using symbol
        >>> client.leverage.set(symbol="BTCUSDT", leverage="10")
        
        >>> # Using asset_id (backward compatible)
        >>> leverage = client.leverage.get(asset_id="01903a7b-...")
    
    Note:
        - Leverage must be within the asset's min/max range
        - Currently only ISOLATED margin type is supported
        - Changing leverage affects new orders only
    """
    
    def _resolve_identifier(
        self, 
        symbol: Optional[str] = None, 
        asset_id: Optional[str] = None
    ) -> tuple:
        """
        Resolve asset identifier - supports both symbol and asset_id.
        
        Returns:
            Tuple of (identifier, use_symbol_flag)
        """
        if symbol and asset_id:
            raise ValueError(
                "Please provide either 'symbol' or 'asset_id', not both. "
                "Symbol is recommended (e.g., symbol='BTCUSDT')"
            )
        if not symbol and not asset_id:
            raise ValueError(
                "Please provide 'symbol' (recommended) or 'asset_id'. "
                "Example: symbol='BTCUSDT'"
            )
        
        if symbol:
            return symbol, True
        return asset_id, False
    
    def get(
        self,
        *,
        symbol: Optional[str] = None,
        asset_id: Optional[str] = None,
    ) -> Leverage:
        """
        Get current leverage settings for an asset.
        
        Args:
            symbol: Trading symbol, e.g., "BTCUSDT" (recommended)
            asset_id: Internal asset ID (legacy, for backward compatibility)
            
        Returns:
            Leverage: Current leverage and margin type settings.
                     Returns default (1x ISOLATED) if not previously set.
            
        Examples:
            >>> # Using symbol (recommended)
            >>> lev = client.leverage.get(symbol="BTCUSDT")
            >>> print(f"Leverage: {lev.leverage}x, Margin: {lev.margin_type.value}")
            
            >>> # Using asset_id (backward compatible)
            >>> lev = client.leverage.get(asset_id="01903a7b-...")
        """
        from mudrex.exceptions import MudrexAPIError
        
        identifier, use_symbol = self._resolve_identifier(symbol, asset_id)
        
        try:
            response = self._get(
                f"/futures/{identifier}/leverage", 
                use_symbol=use_symbol
            )
            data = response.get("data", response) if response else {}
            data["asset_id"] = identifier
            data["symbol"] = identifier if use_symbol else data.get("symbol", "")
            return Leverage.from_dict(data)
        except MudrexAPIError as e:
            # If leverage not set, return default values
            if e.status_code == 400:
                return Leverage(
                    asset_id=identifier,
                    leverage="1",
                    margin_type=MarginType.ISOLATED,
                )
            raise
    
    def set(
        self,
        leverage: str,
        margin_type: str = "ISOLATED",
        *,
        symbol: Optional[str] = None,
        asset_id: Optional[str] = None,
    ) -> Leverage:
        """
        Set leverage and margin type for an asset.
        
        Args:
            leverage: Desired leverage (e.g., "5", "10", "20")
            margin_type: Margin type - currently only "ISOLATED" supported
            symbol: Trading symbol, e.g., "BTCUSDT" (recommended)
            asset_id: Internal asset ID (legacy, for backward compatibility)
            
        Returns:
            Leverage: Updated leverage settings
            
        Raises:
            MudrexValidationError: If leverage is outside allowed range
            
        Examples:
            >>> # Using symbol (recommended)
            >>> result = client.leverage.set(symbol="BTCUSDT", leverage="10")
            >>> print(f"Leverage set to {result.leverage}x")
            
            >>> # Using asset_id (backward compatible)
            >>> result = client.leverage.set(
            ...     asset_id="01903a7b-...",
            ...     leverage="20",
            ...     margin_type="ISOLATED"
            ... )
            
        Note:
            Check asset specifications for allowed leverage range:
            >>> asset = client.assets.get(symbol="BTCUSDT")
            >>> print(f"Allowed: {asset.min_leverage}x - {asset.max_leverage}x")
        """
        identifier, use_symbol = self._resolve_identifier(symbol, asset_id)
        
        # Validate margin type
        margin_type_enum = MarginType(margin_type.upper())
        
        response = self._post(
            f"/futures/{identifier}/leverage", 
            {
                "margin_type": margin_type_enum.value,
                "leverage": leverage,
            },
            use_symbol=use_symbol
        )
        
        data = response.get("data", {})
        data["asset_id"] = identifier
        data["symbol"] = identifier if use_symbol else data.get("symbol", "")
        data["leverage"] = leverage
        data["margin_type"] = margin_type_enum.value
        
        return Leverage.from_dict(data)
