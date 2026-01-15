"""
Assets API Module
=================

Endpoints for discovering ALL tradable futures instruments.
No pagination limits - get the complete list of 500+ trading pairs.
"""

from typing import TYPE_CHECKING, Optional, List

from mudrex.api.base import BaseAPI
from mudrex.models import Asset, PaginatedResponse

if TYPE_CHECKING:
    from mudrex.client import MudrexClient


class AssetsAPI(BaseAPI):
    """
    Asset discovery endpoints - access ALL tradable instruments.
    
    Key Features:
    - **No pagination limits**: Get ALL 500+ trading pairs in one call
    - **Symbol lookup**: Get any asset by trading symbol (e.g., "BTCUSDT")
    - **Asset ID lookup**: Get asset by internal ID (backward compatible)
    - **Search**: Find assets matching a pattern
    
    Examples:
        >>> # Get ALL tradable assets (no limit!)
        >>> assets = client.assets.list_all()
        >>> print(f"Total: {len(assets)} trading pairs")  # 500+
        
        >>> # Get by symbol (recommended)
        >>> btc = client.assets.get("BTCUSDT")
        
        >>> # Get by asset_id (backward compatible)
        >>> asset = client.assets.get_by_id("01903a7b-bf65-...")
        
        >>> # Search for assets
        >>> meme_coins = client.assets.search("DOGE")
    """
    
    def list_all(
        self,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> List[Asset]:
        """
        Get ALL tradable futures contracts - no limits!
        
        Automatically fetches all pages to return the complete list.
        Currently 500+ trading pairs available.
        
        Args:
            sort_by: Field to sort by (optional)
            sort_order: Sort direction - "asc" or "desc" (default: "asc")
            
        Returns:
            List[Asset]: Complete list of ALL tradable assets (no limit)
            
        Examples:
            >>> # Get everything
            >>> assets = client.assets.list_all()
            >>> print(f"Total available: {len(assets)} trading pairs")
            
            >>> # Find specific categories
            >>> usdt_pairs = [a for a in assets if a.symbol.endswith("USDT")]
            >>> high_leverage = [a for a in assets if int(a.max_leverage) >= 100]
            
            >>> # Get asset details
            >>> for asset in assets[:5]:
            ...     print(f"{asset.symbol}: {asset.min_quantity} - {asset.max_quantity}")
        """
        all_assets = []
        offset = 0
        batch_size = 100  # Fetch in batches of 100 for efficiency
        
        while True:
            params = {
                "offset": offset,
                "limit": batch_size,
            }
            if sort_by:
                params["sort_by"] = sort_by
                params["sort_order"] = sort_order
            
            response = self._get("/futures", params)
            
            # Handle both list and paginated responses
            data = response.get("data", response)
            if isinstance(data, list):
                items = data
            else:
                items = data.get("items", data.get("data", []))
            
            if not items:
                break
                
            all_assets.extend([Asset.from_dict(item) for item in items])
            
            # If we got fewer than requested, we've reached the end
            if len(items) < batch_size:
                break
            
            offset += batch_size
        
        return all_assets
    
    def get(self, symbol: str) -> Asset:
        """
        Get asset by trading symbol (recommended).
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT", "XRPUSDT", "ETHUSDT")
            
        Returns:
            Asset: Complete asset specifications including:
                - symbol, asset_id
                - min_quantity, max_quantity, quantity_step
                - min_leverage, max_leverage
                - maker_fee, taker_fee
                - current price
            
        Examples:
            >>> btc = client.assets.get("BTCUSDT")
            >>> print(f"Symbol: {btc.symbol}")
            >>> print(f"Price: ${btc.price}")
            >>> print(f"Min qty: {btc.min_quantity}")
            >>> print(f"Max leverage: {btc.max_leverage}x")
            >>> print(f"Taker fee: {btc.taker_fee}%")
        """
        response = self._get(f"/futures/{symbol}", use_symbol=True)
        return Asset.from_dict(response.get("data", response))
    
    def get_by_id(self, asset_id: str) -> Asset:
        """
        Get asset by internal asset ID (backward compatible).
        
        For new integrations, use get(symbol) instead - it's simpler.
        
        Args:
            asset_id: Internal Mudrex asset ID (UUID format)
            
        Returns:
            Asset: Complete asset specifications
            
        Example:
            >>> asset = client.assets.get_by_id("01903a7b-bf65-707d-a7dc-d7b84c3c756c")
            >>> print(f"Symbol: {asset.symbol}")
        """
        response = self._get(f"/futures/{asset_id}")
        return Asset.from_dict(response.get("data", response))
    
    def search(self, query: str) -> List[Asset]:
        """
        Search for assets matching a pattern.
        
        Case-insensitive search across all asset symbols.
        
        Args:
            query: Search term (e.g., "BTC", "DOGE", "ETH")
            
        Returns:
            List[Asset]: All assets containing the search term
            
        Examples:
            >>> # Find all BTC pairs
            >>> btc_assets = client.assets.search("BTC")
            >>> print(f"Found {len(btc_assets)} BTC pairs")
            
            >>> # Find meme coins
            >>> doge = client.assets.search("DOGE")
            >>> shib = client.assets.search("SHIB")
        """
        all_assets = self.list_all()
        query_upper = query.upper()
        return [
            asset for asset in all_assets
            if query_upper in asset.symbol.upper()
        ]
    
    def exists(self, symbol: str) -> bool:
        """
        Check if a trading symbol exists and is tradable.
        
        Args:
            symbol: Trading symbol to check
            
        Returns:
            bool: True if the symbol exists and can be traded
            
        Example:
            >>> if client.assets.exists("XRPUSDT"):
            ...     print("XRP is tradable!")
            ... else:
            ...     print("XRP not available")
        """
        try:
            self.get(symbol)
            return True
        except Exception:
            return False
    
    def get_symbols(self) -> List[str]:
        """
        Get list of all trading symbols (convenience method).
        
        Returns:
            List[str]: All available trading symbols
            
        Example:
            >>> symbols = client.assets.get_symbols()
            >>> print(f"Available symbols: {len(symbols)}")
            >>> print(symbols[:10])  # First 10
        """
        return [asset.symbol for asset in self.list_all()]
