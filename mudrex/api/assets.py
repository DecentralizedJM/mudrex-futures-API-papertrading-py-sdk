"""
Assets API Module
=================

Endpoints for discovering tradable futures instruments.
Supports 500+ trading pairs available on Mudrex.
"""

from typing import TYPE_CHECKING, Optional, List

from mudrex.api.base import BaseAPI
from mudrex.models import Asset, PaginatedResponse

if TYPE_CHECKING:
    from mudrex.client import MudrexClient


class AssetsAPI(BaseAPI):
    """
    Asset discovery endpoints.
    
    Use these methods to:
    - List ALL tradable futures contracts (500+ pairs)
    - Get detailed specifications for a specific asset by symbol
    - Search assets by name
    
    Example:
        >>> client = MudrexClient(api_secret="...")
        >>> 
        >>> # List ALL assets (no limit!)
        >>> assets = client.assets.list_all()
        >>> print(f"Found {len(assets)} tradable assets")  # 500+
        >>> 
        >>> # Get specific asset by symbol (recommended)
        >>> btc = client.assets.get("BTCUSDT")
        >>> xrp = client.assets.get("XRPUSDT")
        >>> print(f"Min qty: {btc.min_quantity}, Max qty: {btc.max_quantity}")
    """
    
    def list_all(
        self,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> List[Asset]:
        """
        List ALL tradable futures contracts.
        
        This fetches all available assets (500+) without pagination limits.
        The SDK automatically fetches all pages for you.
        
        Args:
            sort_by: Field to sort by (optional)
            sort_order: Sort direction - "asc" or "desc" (default: "asc")
            
        Returns:
            List[Asset]: Complete list of ALL tradable assets
            
        Example:
            >>> assets = client.assets.list_all()
            >>> print(f"Total tradable assets: {len(assets)}")  # 500+
            >>> 
            >>> # Find all USDT pairs
            >>> usdt_pairs = [a for a in assets if a.symbol.endswith("USDT")]
            >>> print(f"USDT pairs: {len(usdt_pairs)}")
        """
        all_assets = []
        page = 1
        per_page = 100  # Max per page for efficiency
        
        while True:
            params = {
                "page": page,
                "per_page": per_page,
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
            
            # Check if we've gotten all items
            if len(items) < per_page:
                break
            
            page += 1
        
        return all_assets
    
    def get(self, symbol: str) -> Asset:
        """
        Get detailed specifications for a specific asset by symbol.
        
        Use trading symbols like "BTCUSDT", "ETHUSDT", "XRPUSDT", etc.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT", "XRPUSDT", "SOLUSDT")
            
        Returns:
            Asset: Detailed asset specifications
            
        Example:
            >>> btc = client.assets.get("BTCUSDT")
            >>> print(f"Symbol: {btc.symbol}")
            >>> print(f"Min quantity: {btc.min_quantity}")
            >>> print(f"Max leverage: {btc.max_leverage}x")
            >>> print(f"Maker fee: {btc.maker_fee}%")
            >>> print(f"Taker fee: {btc.taker_fee}%")
            >>> 
            >>> # Works with any supported symbol
            >>> xrp = client.assets.get("XRPUSDT")
            >>> sol = client.assets.get("SOLUSDT")
        """
        response = self._get(f"/futures/{symbol}", use_symbol=True)
        return Asset.from_dict(response.get("data", response))
    
    def get_by_id(self, asset_id: str) -> Asset:
        """
        Get asset by internal asset ID (advanced usage).
        
        Most users should use get(symbol) instead.
        
        Args:
            asset_id: Internal Mudrex asset ID
            
        Returns:
            Asset: Detailed asset specifications
        """
        response = self._get(f"/futures/{asset_id}")
        return Asset.from_dict(response.get("data", response))
    
    def search(self, query: str) -> List[Asset]:
        """
        Search for assets by symbol pattern.
        
        Args:
            query: Search term (case-insensitive)
            
        Returns:
            List[Asset]: Matching assets
            
        Example:
            >>> # Find all BTC pairs
            >>> btc_assets = client.assets.search("BTC")
            >>> for asset in btc_assets:
            ...     print(asset.symbol)  # BTCUSDT, BTCUSD, etc.
            >>> 
            >>> # Find meme coins
            >>> meme = client.assets.search("DOGE")
        """
        all_assets = self.list_all()
        query_upper = query.upper()
        return [
            asset for asset in all_assets
            if query_upper in asset.symbol.upper()
        ]
    
    def exists(self, symbol: str) -> bool:
        """
        Check if a trading symbol exists.
        
        Args:
            symbol: Trading symbol to check
            
        Returns:
            bool: True if the symbol exists and is tradable
            
        Example:
            >>> if client.assets.exists("XRPUSDT"):
            ...     print("XRP is tradable!")
        """
        try:
            self.get(symbol)
            return True
        except Exception:
            return False
