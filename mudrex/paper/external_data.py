"""
External market data service for funding rates, mark prices, and klines.
Uses public API endpoints (no authentication required).

This service fetches real-time data for:
- Funding rates (for 8-hour funding payments)
- Mark prices (for liquidation calculations)
- Klines/OHLCV (for future backtesting)
"""

import time
import requests
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class FundingInfo:
    """Funding rate information for a symbol."""
    symbol: str
    funding_rate: Decimal  # e.g., 0.0001 = 0.01%
    next_funding_time: datetime
    mark_price: Decimal
    index_price: Decimal


@dataclass
class TickerInfo:
    """Real-time ticker information."""
    symbol: str
    last_price: Decimal
    mark_price: Decimal
    index_price: Decimal
    funding_rate: Decimal
    next_funding_time: datetime
    open_interest: Decimal
    volume_24h: Decimal


@dataclass
class Kline:
    """OHLCV candlestick data."""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


class ExternalDataError(Exception):
    """Exception raised for external data service errors."""
    pass


class ExternalDataService:
    """
    Fetches market data from external public API.
    Used for funding rates, mark prices, and klines.
    
    Features:
    - Funding rate fetching
    - Mark price for liquidation
    - Klines for backtesting (future)
    - Built-in caching to minimize API calls
    
    All endpoints are public and require no authentication.
    """
    
    BASE_URL = "https://api.bybit.com"
    
    def __init__(self, cache_ttl: int = 5):
        """
        Initialize the external data service.
        
        Args:
            cache_ttl: Cache time-to-live in seconds (default: 5)
        """
        self.cache_ttl = cache_ttl
        self._ticker_cache: Dict[str, Tuple[TickerInfo, float]] = {}
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": "MudrexPaperSDK/2.0"
        })
    
    def _convert_symbol(self, mudrex_symbol: str) -> str:
        """
        Convert Mudrex symbol format to external format.
        Mudrex: BTCUSDT → External: BTCUSDT (same for most)
        """
        return mudrex_symbol.upper()
    
    def get_ticker(self, symbol: str) -> TickerInfo:
        """
        Get real-time ticker information including mark price and funding rate.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            
        Returns:
            TickerInfo with current market data
            
        Raises:
            ExternalDataError: If API request fails
        """
        now = time.time()
        
        # Check cache
        if symbol in self._ticker_cache:
            cached, cached_at = self._ticker_cache[symbol]
            if now - cached_at < self.cache_ttl:
                return cached
        
        # Fetch fresh data
        ext_symbol = self._convert_symbol(symbol)
        
        try:
            response = self._session.get(
                f"{self.BASE_URL}/v5/market/tickers",
                params={"category": "linear", "symbol": ext_symbol},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("retCode") != 0:
                raise ExternalDataError(f"API error: {data.get('retMsg')}")
            
            result_list = data.get("result", {}).get("list", [])
            if not result_list:
                raise ExternalDataError(f"No data found for {symbol}")
            
            ticker_data = result_list[0]
            
            # Parse next funding time
            next_funding_ts = int(ticker_data.get("nextFundingTime", 0))
            next_funding_time = datetime.fromtimestamp(
                next_funding_ts / 1000, tz=timezone.utc
            ) if next_funding_ts else datetime.now(timezone.utc)
            
            ticker = TickerInfo(
                symbol=symbol,
                last_price=Decimal(ticker_data.get("lastPrice", "0")),
                mark_price=Decimal(ticker_data.get("markPrice", "0")),
                index_price=Decimal(ticker_data.get("indexPrice", "0")),
                funding_rate=Decimal(ticker_data.get("fundingRate", "0")),
                next_funding_time=next_funding_time,
                open_interest=Decimal(ticker_data.get("openInterest", "0")),
                volume_24h=Decimal(ticker_data.get("volume24h", "0")),
            )
            
            # Cache it
            self._ticker_cache[symbol] = (ticker, now)
            logger.debug(f"Fetched ticker for {symbol}: mark={ticker.mark_price}, funding={ticker.funding_rate}")
            return ticker
            
        except requests.RequestException as e:
            raise ExternalDataError(f"Failed to fetch ticker for {symbol}: {e}")
    
    def get_mark_price(self, symbol: str) -> Decimal:
        """
        Get current mark price for a symbol.
        Mark price is used for liquidation calculations.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            
        Returns:
            Current mark price as Decimal
        """
        ticker = self.get_ticker(symbol)
        return ticker.mark_price
    
    def get_funding_rate(self, symbol: str) -> Decimal:
        """
        Get current funding rate for a symbol.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            
        Returns:
            Current funding rate as Decimal (e.g., 0.0001 = 0.01%)
        """
        ticker = self.get_ticker(symbol)
        return ticker.funding_rate
    
    def get_funding_info(self, symbol: str) -> FundingInfo:
        """
        Get complete funding information for a symbol.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            
        Returns:
            FundingInfo with rate, next time, and prices
        """
        ticker = self.get_ticker(symbol)
        return FundingInfo(
            symbol=symbol,
            funding_rate=ticker.funding_rate,
            next_funding_time=ticker.next_funding_time,
            mark_price=ticker.mark_price,
            index_price=ticker.index_price,
        )
    
    def get_next_funding_time(self, symbol: str) -> datetime:
        """
        Get the next funding timestamp.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            
        Returns:
            Datetime of next funding settlement
        """
        ticker = self.get_ticker(symbol)
        return ticker.next_funding_time
    
    def get_funding_history(
        self, 
        symbol: str, 
        limit: int = 50
    ) -> List[Dict]:
        """
        Get historical funding rates.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            limit: Number of records (max 200)
            
        Returns:
            List of historical funding rate records
        """
        ext_symbol = self._convert_symbol(symbol)
        
        try:
            response = self._session.get(
                f"{self.BASE_URL}/v5/market/funding/history",
                params={
                    "category": "linear",
                    "symbol": ext_symbol,
                    "limit": min(limit, 200)
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("retCode") != 0:
                raise ExternalDataError(f"API error: {data.get('retMsg')}")
            
            history = []
            for item in data.get("result", {}).get("list", []):
                history.append({
                    "symbol": symbol,
                    "funding_rate": Decimal(item.get("fundingRate", "0")),
                    "funding_time": datetime.fromtimestamp(
                        int(item.get("fundingRateTimestamp", 0)) / 1000,
                        tz=timezone.utc
                    ),
                })
            
            return history
            
        except requests.RequestException as e:
            raise ExternalDataError(f"Failed to fetch funding history: {e}")
    
    def get_klines(
        self,
        symbol: str,
        interval: str = "15",  # minutes
        limit: int = 200
    ) -> List[Kline]:
        """
        Get historical OHLCV kline data.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Kline interval ("1", "5", "15", "60", "240", "D")
            limit: Number of klines (max 1000)
            
        Returns:
            List of Kline objects in chronological order
        """
        ext_symbol = self._convert_symbol(symbol)
        
        try:
            response = self._session.get(
                f"{self.BASE_URL}/v5/market/kline",
                params={
                    "category": "linear",
                    "symbol": ext_symbol,
                    "interval": interval,
                    "limit": min(limit, 1000)
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("retCode") != 0:
                raise ExternalDataError(f"API error: {data.get('retMsg')}")
            
            klines = []
            for item in data.get("result", {}).get("list", []):
                # Format: [timestamp, open, high, low, close, volume, turnover]
                klines.append(Kline(
                    timestamp=datetime.fromtimestamp(
                        int(item[0]) / 1000, tz=timezone.utc
                    ),
                    open=Decimal(item[1]),
                    high=Decimal(item[2]),
                    low=Decimal(item[3]),
                    close=Decimal(item[4]),
                    volume=Decimal(item[5]),
                ))
            
            # Reverse to chronological order (API returns newest first)
            klines.reverse()
            return klines
            
        except requests.RequestException as e:
            raise ExternalDataError(f"Failed to fetch klines: {e}")
    
    def clear_cache(self):
        """Clear all cached data."""
        self._ticker_cache.clear()
        logger.debug("External data cache cleared")


class MockExternalDataService:
    """
    Mock external data service for offline testing.
    Allows manual control of prices, funding rates, etc.
    
    Use this when:
    - Testing without internet
    - Running automated tests
    - Simulating specific market conditions
    """
    
    def __init__(self):
        self._tickers: Dict[str, TickerInfo] = {}
        self._funding_history: Dict[str, List[Dict]] = {}
        self._klines: Dict[str, List[Kline]] = {}
        self._default_funding_rate = Decimal("0.0001")  # 0.01%
    
    def set_ticker(
        self,
        symbol: str,
        last_price: Decimal,
        mark_price: Optional[Decimal] = None,
        funding_rate: Optional[Decimal] = None,
        next_funding_time: Optional[datetime] = None,
    ):
        """Set ticker data for a symbol."""
        self._tickers[symbol] = TickerInfo(
            symbol=symbol,
            last_price=last_price,
            mark_price=mark_price or last_price,
            index_price=last_price,
            funding_rate=funding_rate or self._default_funding_rate,
            next_funding_time=next_funding_time or datetime.now(timezone.utc),
            open_interest=Decimal("0"),
            volume_24h=Decimal("0"),
        )
    
    def set_mark_price(self, symbol: str, mark_price: Decimal):
        """Update mark price for a symbol (creates ticker if needed)."""
        if symbol in self._tickers:
            old = self._tickers[symbol]
            self._tickers[symbol] = TickerInfo(
                symbol=symbol,
                last_price=old.last_price,
                mark_price=mark_price,
                index_price=old.index_price,
                funding_rate=old.funding_rate,
                next_funding_time=old.next_funding_time,
                open_interest=old.open_interest,
                volume_24h=old.volume_24h,
            )
        else:
            self.set_ticker(symbol, mark_price, mark_price)
    
    def set_funding_rate(self, symbol: str, rate: Decimal):
        """Update funding rate for a symbol."""
        if symbol in self._tickers:
            old = self._tickers[symbol]
            self._tickers[symbol] = TickerInfo(
                symbol=symbol,
                last_price=old.last_price,
                mark_price=old.mark_price,
                index_price=old.index_price,
                funding_rate=rate,
                next_funding_time=old.next_funding_time,
                open_interest=old.open_interest,
                volume_24h=old.volume_24h,
            )
        else:
            self.set_ticker(symbol, Decimal("0"), funding_rate=rate)
    
    def get_ticker(self, symbol: str) -> TickerInfo:
        """Get ticker for symbol."""
        if symbol not in self._tickers:
            raise ExternalDataError(f"No mock data for {symbol}. Call set_ticker() first.")
        return self._tickers[symbol]
    
    def get_mark_price(self, symbol: str) -> Decimal:
        """Get mark price."""
        return self.get_ticker(symbol).mark_price
    
    def get_funding_rate(self, symbol: str) -> Decimal:
        """Get funding rate."""
        return self.get_ticker(symbol).funding_rate
    
    def get_funding_info(self, symbol: str) -> FundingInfo:
        """Get funding info."""
        ticker = self.get_ticker(symbol)
        return FundingInfo(
            symbol=symbol,
            funding_rate=ticker.funding_rate,
            next_funding_time=ticker.next_funding_time,
            mark_price=ticker.mark_price,
            index_price=ticker.index_price,
        )
    
    def get_next_funding_time(self, symbol: str) -> datetime:
        """Get next funding time."""
        return self.get_ticker(symbol).next_funding_time
    
    def get_funding_history(self, symbol: str, limit: int = 50) -> List[Dict]:
        """Get funding history."""
        return self._funding_history.get(symbol, [])[:limit]
    
    def get_klines(
        self, symbol: str, interval: str = "15", limit: int = 200
    ) -> List[Kline]:
        """Get klines."""
        return self._klines.get(symbol, [])[:limit]
    
    def add_klines(self, symbol: str, klines: List[Kline]):
        """Add klines for a symbol."""
        if symbol not in self._klines:
            self._klines[symbol] = []
        self._klines[symbol].extend(klines)
    
    def add_funding_history(self, symbol: str, history: List[Dict]):
        """Add funding history for a symbol."""
        if symbol not in self._funding_history:
            self._funding_history[symbol] = []
        self._funding_history[symbol].extend(history)
    
    def clear_cache(self):
        """No-op for mock."""
        pass
