"""
Price Feed Service
==================

Fetches real-time prices from Mudrex API for paper trading simulation.
Includes caching to minimize API calls and respect rate limits.
"""

import time
import logging
from decimal import Decimal
from typing import Dict, Optional, Tuple, TYPE_CHECKING, Callable

from mudrex.paper.exceptions import PriceFetchError, SymbolNotFoundError

if TYPE_CHECKING:
    from mudrex.api.assets import AssetsAPI

logger = logging.getLogger(__name__)


class PriceFeedService:
    """
    Fetches real prices from Mudrex for paper trading simulation.
    
    Features:
    - Caching with configurable TTL (default: 3 seconds)
    - Graceful error handling
    - Asset info caching for validation
    
    Example:
        >>> from mudrex import MudrexClient
        >>> client = MudrexClient(api_secret="...")
        >>> price_feed = PriceFeedService(client.assets)
        >>> 
        >>> price = price_feed.get_price("BTCUSDT")
        >>> print(f"BTC Price: ${price}")
    """
    
    def __init__(
        self,
        assets_api: "AssetsAPI",
        cache_ttl: int = 3,
        asset_cache_ttl: int = 300,  # 5 minutes for asset metadata
    ):
        """
        Initialize the price feed service.
        
        Args:
            assets_api: The AssetsAPI instance for fetching prices
            cache_ttl: Cache time-to-live in seconds for prices
            asset_cache_ttl: Cache TTL for asset metadata (min qty, leverage, etc.)
        """
        self.assets_api = assets_api
        self.cache_ttl = cache_ttl
        self.asset_cache_ttl = asset_cache_ttl
        
        # Price cache: symbol -> (price, timestamp)
        self._price_cache: Dict[str, Tuple[Decimal, float]] = {}
        
        # Asset info cache: symbol -> (asset_info, timestamp)
        self._asset_cache: Dict[str, Tuple[dict, float]] = {}
        
        # Track symbols we've verified exist
        self._valid_symbols: set = set()
    
    def get_price(self, symbol: str) -> Decimal:
        """
        Get current price for a symbol with caching.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            
        Returns:
            Current price as Decimal
            
        Raises:
            SymbolNotFoundError: If symbol is invalid
            PriceFetchError: If unable to fetch price
        """
        now = time.time()
        
        # Check cache first
        if symbol in self._price_cache:
            price, cached_at = self._price_cache[symbol]
            if now - cached_at < self.cache_ttl:
                logger.debug(f"Price cache hit for {symbol}: {price}")
                return price
        
        # Fetch fresh price
        try:
            asset = self.assets_api.get(symbol)
            
            # Get price from asset data
            price_str = getattr(asset, 'price', None) or getattr(asset, 'last_price', None)
            
            if not price_str:
                raise PriceFetchError(symbol, "No price field in asset data")
            
            price = Decimal(str(price_str))
            
            # Update cache
            self._price_cache[symbol] = (price, now)
            self._valid_symbols.add(symbol)
            
            logger.debug(f"Fetched price for {symbol}: {price}")
            return price
            
        except Exception as e:
            if "not found" in str(e).lower() or "404" in str(e):
                raise SymbolNotFoundError(symbol)
            raise PriceFetchError(symbol, str(e))
    
    def get_asset_info(self, symbol: str) -> dict:
        """
        Get asset metadata (min quantity, max leverage, etc.) with caching.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with asset information
        """
        now = time.time()
        
        # Check cache
        if symbol in self._asset_cache:
            info, cached_at = self._asset_cache[symbol]
            if now - cached_at < self.asset_cache_ttl:
                return info
        
        # Fetch fresh
        try:
            asset = self.assets_api.get(symbol)
            
            info = {
                "symbol": symbol,
                "min_quantity": getattr(asset, 'min_quantity', "0.001"),
                "max_quantity": getattr(asset, 'max_quantity', "1000000"),
                "quantity_step": getattr(asset, 'quantity_step', "0.001"),
                "min_leverage": getattr(asset, 'min_leverage', "1"),
                "max_leverage": getattr(asset, 'max_leverage', "100"),
                "price_step": getattr(asset, 'price_step', "0.01"),
                "price": getattr(asset, 'price', None),
            }
            
            self._asset_cache[symbol] = (info, now)
            self._valid_symbols.add(symbol)
            
            return info
            
        except Exception as e:
            if "not found" in str(e).lower():
                raise SymbolNotFoundError(symbol)
            raise PriceFetchError(symbol, str(e))
    
    def get_prices_batch(self, symbols: list) -> Dict[str, Decimal]:
        """
        Get prices for multiple symbols.
        
        Note: This fetches one at a time due to Mudrex API design.
        Results are cached for subsequent calls.
        
        Args:
            symbols: List of trading symbols
            
        Returns:
            Dictionary mapping symbol to price
        """
        prices = {}
        for symbol in symbols:
            try:
                prices[symbol] = self.get_price(symbol)
            except (SymbolNotFoundError, PriceFetchError) as e:
                logger.warning(f"Failed to fetch price for {symbol}: {e}")
                continue
        return prices
    
    def is_valid_symbol(self, symbol: str) -> bool:
        """
        Check if a symbol is valid/tradeable.
        
        Args:
            symbol: Trading symbol to validate
            
        Returns:
            True if symbol exists and is tradeable
        """
        if symbol in self._valid_symbols:
            return True
        
        try:
            self.get_asset_info(symbol)
            return True
        except (SymbolNotFoundError, PriceFetchError):
            return False
    
    def validate_quantity(self, symbol: str, quantity: Decimal) -> Tuple[bool, str]:
        """
        Validate that a quantity is valid for a symbol.
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            info = self.get_asset_info(symbol)
            min_qty = Decimal(info["min_quantity"])
            max_qty = Decimal(info["max_quantity"])
            
            if quantity < min_qty:
                return False, f"Quantity {quantity} below minimum {min_qty}"
            if quantity > max_qty:
                return False, f"Quantity {quantity} exceeds maximum {max_qty}"
            
            return True, ""
            
        except (SymbolNotFoundError, PriceFetchError) as e:
            return False, str(e)
    
    def validate_leverage(self, symbol: str, leverage: int) -> Tuple[bool, str]:
        """
        Validate that a leverage is valid for a symbol.
        
        Args:
            symbol: Trading symbol
            leverage: Leverage to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            info = self.get_asset_info(symbol)
            min_lev = int(info["min_leverage"])
            max_lev = int(info["max_leverage"])
            
            if leverage < min_lev:
                return False, f"Leverage {leverage}x below minimum {min_lev}x"
            if leverage > max_lev:
                return False, f"Leverage {leverage}x exceeds maximum {max_lev}x"
            
            return True, ""
            
        except (SymbolNotFoundError, PriceFetchError) as e:
            return False, str(e)
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        self._price_cache.clear()
        self._asset_cache.clear()
        logger.info("Price feed cache cleared")
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics for debugging."""
        return {
            "price_cache_size": len(self._price_cache),
            "asset_cache_size": len(self._asset_cache),
            "valid_symbols": len(self._valid_symbols),
            "cache_ttl": self.cache_ttl,
            "asset_cache_ttl": self.asset_cache_ttl,
        }


class MockPriceFeedService:
    """
    Mock price feed for testing without API calls.
    
    Useful for unit tests and offline development.
    """
    
    def __init__(self, default_prices: Dict[str, Decimal] = None):
        """
        Initialize with preset prices.
        
        Args:
            default_prices: Dictionary of symbol -> price
        """
        self.prices = default_prices or {
            "BTCUSDT": Decimal("100000"),
            "ETHUSDT": Decimal("3500"),
            "XRPUSDT": Decimal("2.50"),
            "SOLUSDT": Decimal("200"),
            "DOGEUSDT": Decimal("0.35"),
        }
        self.asset_info = {
            symbol: {
                "symbol": symbol,
                "min_quantity": "0.001",
                "max_quantity": "1000000",
                "quantity_step": "0.001",
                "min_leverage": "1",
                "max_leverage": "100",
                "price_step": "0.01",
                "price": str(price),
            }
            for symbol, price in self.prices.items()
        }
    
    def set_price(self, symbol: str, price: Decimal) -> None:
        """Set price for a symbol (for testing price movements)."""
        self.prices[symbol] = price
        if symbol in self.asset_info:
            self.asset_info[symbol]["price"] = str(price)
    
    def get_price(self, symbol: str) -> Decimal:
        """Get price for a symbol."""
        if symbol not in self.prices:
            raise SymbolNotFoundError(symbol)
        return self.prices[symbol]
    
    def get_asset_info(self, symbol: str) -> dict:
        """Get asset info for a symbol."""
        if symbol not in self.asset_info:
            raise SymbolNotFoundError(symbol)
        return self.asset_info[symbol]
    
    def get_prices_batch(self, symbols: list) -> Dict[str, Decimal]:
        """Get prices for multiple symbols."""
        return {s: self.prices[s] for s in symbols if s in self.prices}
    
    def is_valid_symbol(self, symbol: str) -> bool:
        """Check if symbol is valid."""
        return symbol in self.prices
    
    def validate_quantity(self, symbol: str, quantity: Decimal) -> Tuple[bool, str]:
        """Validate quantity (mock always succeeds for known symbols)."""
        if symbol not in self.prices:
            return False, f"Unknown symbol: {symbol}"
        if quantity <= 0:
            return False, "Quantity must be positive"
        return True, ""
    
    def validate_leverage(self, symbol: str, leverage: int) -> Tuple[bool, str]:
        """Validate leverage (mock allows 1-100x)."""
        if symbol not in self.prices:
            return False, f"Unknown symbol: {symbol}"
        if leverage < 1 or leverage > 100:
            return False, f"Leverage must be between 1-100x"
        return True, ""
