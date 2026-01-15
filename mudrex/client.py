"""
Mudrex API Client
=================

The main client class for interacting with Mudrex Trading API.
Handles authentication, rate limiting, and provides access to all API modules.

Supports both live trading and paper trading modes.
"""

import time
import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal
import requests

from mudrex.exceptions import (
    MudrexAPIError,
    MudrexRateLimitError,
    raise_for_error,
)
from mudrex.api.wallet import WalletAPI
from mudrex.api.assets import AssetsAPI
from mudrex.api.leverage import LeverageAPI
from mudrex.api.orders import OrdersAPI
from mudrex.api.positions import PositionsAPI
from mudrex.api.fees import FeesAPI

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Comprehensive rate limiter to stay within all API limits.
    
    Tracks requests across multiple time windows:
    - 2 requests per second
    - 50 requests per minute
    - 1000 requests per hour
    - 10000 requests per day
    
    Uses a sliding window approach to accurately track request counts.
    """
    
    # Default rate limits from Mudrex API documentation
    DEFAULT_LIMITS = {
        "second": 2,
        "minute": 50,
        "hour": 1000,
        "day": 10000,
    }
    
    # Time windows in seconds
    TIME_WINDOWS = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
    }
    
    def __init__(
        self,
        requests_per_second: int = 2,
        requests_per_minute: int = 50,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000,
    ):
        """
        Initialize the rate limiter with configurable limits.
        
        Args:
            requests_per_second: Max requests per second (default: 2)
            requests_per_minute: Max requests per minute (default: 50)
            requests_per_hour: Max requests per hour (default: 1000)
            requests_per_day: Max requests per day (default: 10000)
        """
        self.limits = {
            "second": requests_per_second,
            "minute": requests_per_minute,
            "hour": requests_per_hour,
            "day": requests_per_day,
        }
        
        # Store timestamps of recent requests for sliding window tracking
        self._request_times: List[float] = []
        
        # Minimum interval between requests (based on per-second limit)
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
    
    def _cleanup_old_requests(self, now: float) -> None:
        """Remove request timestamps older than the longest window (1 day)."""
        cutoff = now - self.TIME_WINDOWS["day"]
        self._request_times = [t for t in self._request_times if t > cutoff]
    
    def _count_requests_in_window(self, now: float, window_seconds: float) -> int:
        """Count requests within a time window."""
        cutoff = now - window_seconds
        return sum(1 for t in self._request_times if t > cutoff)
    
    def _get_wait_time(self, now: float) -> float:
        """
        Calculate how long to wait before the next request is allowed.
        
        Returns:
            Wait time in seconds (0 if no wait needed)
        """
        max_wait = 0.0
        
        for window_name, window_seconds in self.TIME_WINDOWS.items():
            limit = self.limits[window_name]
            count = self._count_requests_in_window(now, window_seconds)
            
            if count >= limit:
                # Find the oldest request in this window
                cutoff = now - window_seconds
                relevant_times = [t for t in self._request_times if t > cutoff]
                
                if relevant_times:
                    # We need to wait until the oldest request falls out of the window
                    oldest = min(relevant_times)
                    wait = (oldest + window_seconds) - now + 0.01  # Add small buffer
                    max_wait = max(max_wait, wait)
                    logger.debug(
                        f"Rate limit ({window_name}): {count}/{limit}, "
                        f"wait {wait:.2f}s"
                    )
        
        # Also enforce minimum interval between requests
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            interval_wait = self.min_interval - elapsed
            max_wait = max(max_wait, interval_wait)
        
        return max_wait
    
    def wait(self) -> None:
        """Wait if necessary to respect all rate limits."""
        now = time.time()
        
        # Clean up old timestamps
        self._cleanup_old_requests(now)
        
        # Calculate and apply wait time
        wait_time = self._get_wait_time(now)
        if wait_time > 0:
            logger.debug(f"Rate limiter: sleeping {wait_time:.3f}s")
            time.sleep(wait_time)
            now = time.time()
        
        # Record this request
        self._request_times.append(now)
        self.last_request_time = now
    
    def get_usage(self) -> Dict[str, Dict[str, int]]:
        """
        Get current rate limit usage for monitoring.
        
        Returns:
            Dict with usage counts and limits for each window
            
        Example:
            >>> usage = client._rate_limiter.get_usage()
            >>> print(f"Minute: {usage['minute']['used']}/{usage['minute']['limit']}")
        """
        now = time.time()
        self._cleanup_old_requests(now)
        
        return {
            window_name: {
                "used": self._count_requests_in_window(now, window_seconds),
                "limit": self.limits[window_name],
            }
            for window_name, window_seconds in self.TIME_WINDOWS.items()
        }


class MudrexClient:
    """
    Main client for Mudrex Trading API.
    
    Supports both live trading and paper (simulated) trading modes.
    
    Example (Live Trading):
        >>> client = MudrexClient(api_secret="your-secret-key")
        >>> balance = client.wallet.get_futures_balance()
    
    Example (Paper Trading):
        >>> client = MudrexClient(
        ...     api_secret="your-secret-key",
        ...     mode="paper",
        ...     paper_balance="10000",
        ... )
    
    Args:
        api_secret: Your Mudrex API secret key
        base_url: API base URL (default: https://trade.mudrex.com/fapi/v1)
        timeout: Request timeout in seconds (default: 30)
        rate_limit: Enable automatic rate limiting (default: True)
        max_retries: Maximum retries on rate limit errors (default: 3)
        mode: Trading mode - "live" or "paper" (default: "live")
        paper_balance: Initial balance for paper trading (default: "10000")
        paper_db_path: SQLite database path for paper trading persistence
        paper_sltp_monitor: Enable background SL/TP monitoring (default: False)
        paper_sltp_interval: SL/TP check interval in seconds (default: 5)
        paper_funding: Enable funding rate payments (default: False)
        paper_liquidation: Enable auto-liquidation (default: False)
    """
    
    BASE_URL = "https://trade.mudrex.com/fapi/v1"
    
    def __init__(
        self,
        *,
        api_secret: str,
        base_url: Optional[str] = None,
        timeout: int = 30,
        rate_limit: bool = True,
        max_retries: int = 3,
        mode: str = "live",
        paper_balance: str = "10000",
        paper_db_path: Optional[str] = None,
        paper_sltp_monitor: bool = False,
        paper_sltp_interval: int = 5,
        paper_funding: bool = False,
        paper_liquidation: bool = False,
    ):
        if not api_secret:
            raise ValueError("api_secret is required")
        
        if api_secret.startswith(("http://", "https://", "www.")):
            raise ValueError(
                "api_secret looks like a URL. Did you mean to use base_url?"
            )
        
        self.mode = mode.lower()
        if self.mode not in ("live", "paper"):
            raise ValueError("mode must be 'live' or 'paper'")
        
        self.api_secret = api_secret
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        
        self._rate_limiter = RateLimiter() if rate_limit else None
        
        self._session = requests.Session()
        self._session.headers.update({
            "X-Authentication": api_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "mudrex-python-sdk/1.0.0",
        })
        
        # Paper trading state
        self._paper_engine = None
        self._paper_db = None
        self._paper_sltp_monitor = None
        self._paper_funding_monitor = None
        self._paper_liquidation_engine = None
        self._external_data = None
        
        # Store paper trading config for reset/import operations
        self._paper_funding_enabled = paper_funding
        self._paper_liquidation_enabled = paper_liquidation
        self._paper_sltp_interval = paper_sltp_interval
        
        if self.mode == "paper":
            self._init_paper_trading(
                balance=paper_balance,
                db_path=paper_db_path,
                sltp_monitor=paper_sltp_monitor,
                sltp_interval=paper_sltp_interval,
                enable_funding=paper_funding,
                enable_liquidation=paper_liquidation,
            )
        else:
            self._init_live_trading()
    
    def _init_live_trading(self) -> None:
        """Initialize live trading API modules."""
        self.wallet = WalletAPI(self)
        self.assets = AssetsAPI(self)
        self.leverage = LeverageAPI(self)
        self.orders = OrdersAPI(self)
        self.positions = PositionsAPI(self)
        self.fees = FeesAPI(self)
    
    def _init_paper_trading(
        self,
        balance: str,
        db_path: Optional[str],
        sltp_monitor: bool,
        sltp_interval: int,
        enable_funding: bool = False,
        enable_liquidation: bool = False,
    ) -> None:
        """Initialize paper trading engine and APIs."""
        from mudrex.paper import (
            PaperTradingEngine,
            PriceFeedService,
            PaperDB,
            SLTPMonitor,
        )
        from mudrex.paper.external_data import ExternalDataService
        from mudrex.paper.funding import FundingMonitor
        from mudrex.paper.liquidation import LiquidationEngine
        from mudrex.paper.api import (
            PaperOrdersAPI,
            PaperPositionsAPI,
            PaperWalletAPI,
            PaperLeverageAPI,
            PaperFeesAPI,
        )
        
        # Create AssetsAPI first - needed for price feed
        self.assets = AssetsAPI(self)
        price_feed = PriceFeedService(self.assets)
        
        if db_path:
            self._paper_db = PaperDB(db_path)
        else:
            import os
            default_path = os.path.expanduser("~/.mudrex_paper.db")
            self._paper_db = PaperDB(default_path)
        
        saved_state = self._paper_db.load_state()
        
        if saved_state:
            logger.info("Loaded paper trading state from database")
            self._paper_engine = PaperTradingEngine.from_state(
                state=saved_state,
                price_feed=price_feed,
            )
        else:
            logger.info(f"Starting new paper trading session with ${balance}")
            self._paper_engine = PaperTradingEngine(
                initial_balance=Decimal(balance),
                price_feed=price_feed,
            )
        
        if sltp_monitor:
            self._paper_sltp_monitor = SLTPMonitor(
                engine=self._paper_engine,
                check_interval=sltp_interval,
            )
            self._paper_sltp_monitor.start()
            logger.info(f"Started SL/TP monitor (interval: {sltp_interval}s)")
        
        self.wallet = PaperWalletAPI(self._paper_engine)
        self.leverage = PaperLeverageAPI(self._paper_engine, self.assets)
        self.orders = PaperOrdersAPI(self._paper_engine, self.assets)
        self.positions = PaperPositionsAPI(self._paper_engine, self.assets)
        self.fees = PaperFeesAPI(self._paper_engine)
        
        # Initialize external data service for funding rates and mark prices
        if enable_funding or enable_liquidation:
            self._external_data = ExternalDataService()
        
        # Initialize funding monitor
        if enable_funding and self._external_data:
            self._paper_funding_monitor = FundingMonitor(
                engine=self._paper_engine,
                external_data=self._external_data,
                enabled=True,
            )
            self._paper_funding_monitor.start()
            logger.info("Funding rate monitor started (8-hour intervals)")
        
        # Initialize liquidation engine
        if enable_liquidation and self._external_data:
            self._paper_liquidation_engine = LiquidationEngine(
                engine=self._paper_engine,
                external_data=self._external_data,
                enabled=True,
            )
            self._paper_liquidation_engine.start()
            logger.info("Liquidation engine started")
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint path."""
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}"
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an API request with rate limiting and retry logic."""
        url = self._build_url(endpoint)
        
        for attempt in range(self.max_retries + 1):
            if self._rate_limiter:
                self._rate_limiter.wait()
            
            try:
                logger.debug(f"Request: {method} {url}")
                
                response = self._session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    timeout=self.timeout,
                )
                
                try:
                    data = response.json()
                except ValueError:
                    data = {"success": False, "message": response.text}
                
                if response.status_code == 429:
                    if attempt < self.max_retries:
                        retry_after = float(response.headers.get("Retry-After", 1))
                        logger.warning(f"Rate limited, retrying in {retry_after}s...")
                        time.sleep(retry_after)
                        continue
                    raise MudrexRateLimitError(
                        message="Rate limit exceeded after retries",
                        retry_after=float(response.headers.get("Retry-After", 1)),
                        status_code=429,
                    )
                
                if response.status_code >= 400:
                    logger.error(f"API error ({response.status_code}): {data}")
                raise_for_error(data, response.status_code)
                
                return data
                
            except requests.exceptions.Timeout:
                raise MudrexAPIError(f"Request timed out after {self.timeout}s")
            except requests.exceptions.ConnectionError as e:
                raise MudrexAPIError(f"Connection error: {e}")
        
        raise MudrexAPIError("Max retries exceeded")
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request."""
        return self._request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a POST request."""
        return self._request("POST", endpoint, json_data=data)
    
    def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a PATCH request."""
        return self._request("PATCH", endpoint, json_data=data)
    
    def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a DELETE request."""
        return self._request("DELETE", endpoint, params=params)
    
    # Paper Trading Methods
    
    def save_paper_state(self) -> None:
        """Save paper trading state to database."""
        if self.mode != "paper":
            raise RuntimeError("save_paper_state() only works in paper mode")
        
        # PaperDB.save_state expects the engine, not a dict
        self._paper_db.save_state(self._paper_engine)
        
        logger.info("Paper trading state saved")
    
    def reset_paper_trading(self, new_balance: str = "10000") -> None:
        """Reset paper trading to a fresh state."""
        if self.mode != "paper":
            raise RuntimeError("reset_paper_trading() only works in paper mode")
        
        # Stop existing monitors
        if self._paper_sltp_monitor:
            self._paper_sltp_monitor.stop()
        if self._paper_funding_monitor:
            self._paper_funding_monitor.stop()
        if self._paper_liquidation_engine:
            self._paper_liquidation_engine.stop()
        
        from mudrex.paper import PaperTradingEngine, PriceFeedService, SLTPMonitor
        from mudrex.paper.external_data import ExternalDataService
        from mudrex.paper.funding import FundingMonitor
        from mudrex.paper.liquidation import LiquidationEngine
        from mudrex.paper.api import (
            PaperOrdersAPI,
            PaperPositionsAPI,
            PaperWalletAPI,
            PaperLeverageAPI,
            PaperFeesAPI,
        )
        
        # Create new price feed with existing assets API
        price_feed = PriceFeedService(self.assets)
        self._paper_engine = PaperTradingEngine(
            initial_balance=Decimal(new_balance),
            price_feed=price_feed,
        )
        
        # Reinitialize APIs with new engine
        self.wallet = PaperWalletAPI(self._paper_engine)
        self.leverage = PaperLeverageAPI(self._paper_engine, self.assets)
        self.orders = PaperOrdersAPI(self._paper_engine, self.assets)
        self.positions = PaperPositionsAPI(self._paper_engine, self.assets)
        self.fees = PaperFeesAPI(self._paper_engine)
        
        # Reinitialize external data and monitors if they were enabled
        if self._paper_funding_enabled or self._paper_liquidation_enabled:
            self._external_data = ExternalDataService()
        
        if self._paper_funding_enabled and self._external_data:
            self._paper_funding_monitor = FundingMonitor(
                engine=self._paper_engine,
                external_data=self._external_data,
                enabled=True,
            )
            self._paper_funding_monitor.start()
            logger.info("Funding rate monitor started (8-hour intervals)")
        
        if self._paper_liquidation_enabled and self._external_data:
            self._paper_liquidation_engine = LiquidationEngine(
                engine=self._paper_engine,
                external_data=self._external_data,
                enabled=True,
            )
            self._paper_liquidation_engine.start()
            logger.info("Liquidation engine started")
        
        # Restart SL/TP monitor if it was running
        if self._paper_sltp_monitor:
            self._paper_sltp_monitor = SLTPMonitor(
                engine=self._paper_engine,
                check_interval=self._paper_sltp_interval,
            )
            self._paper_sltp_monitor.start()
        
        self._paper_db.clear_state()
        logger.info(f"Paper trading reset with ${new_balance}")
    
    def get_paper_statistics(self) -> Dict[str, Any]:
        """Get paper trading statistics."""
        if self.mode != "paper":
            raise RuntimeError("get_paper_statistics() only works in paper mode")
        return self._paper_engine.get_statistics()
    
    def get_paper_trade_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get paper trading trade history."""
        if self.mode != "paper":
            raise RuntimeError("get_paper_trade_history() only works in paper mode")
        trades = self._paper_db.get_trade_history(symbol=symbol, limit=limit)
        return [t.to_dict() for t in trades]
    
    def export_paper_state(self) -> Dict[str, Any]:
        """Export paper trading state as JSON-serializable dict."""
        if self.mode != "paper":
            raise RuntimeError("export_paper_state() only works in paper mode")
        return self._paper_engine.export_state()
    
    def import_paper_state(self, state: Dict[str, Any]) -> None:
        """Import paper trading state from a previously exported dict."""
        if self.mode != "paper":
            raise RuntimeError("import_paper_state() only works in paper mode")
        
        # Stop existing monitors
        if self._paper_sltp_monitor:
            self._paper_sltp_monitor.stop()
        if self._paper_funding_monitor:
            self._paper_funding_monitor.stop()
        if self._paper_liquidation_engine:
            self._paper_liquidation_engine.stop()
        
        from mudrex.paper import PaperTradingEngine, PriceFeedService, SLTPMonitor
        from mudrex.paper.external_data import ExternalDataService
        from mudrex.paper.funding import FundingMonitor
        from mudrex.paper.liquidation import LiquidationEngine
        from mudrex.paper.api import (
            PaperOrdersAPI,
            PaperPositionsAPI,
            PaperWalletAPI,
            PaperLeverageAPI,
            PaperFeesAPI,
        )
        
        # Create price feed with existing assets API
        price_feed = PriceFeedService(self.assets)
        self._paper_engine = PaperTradingEngine.from_state(
            state=state,
            price_feed=price_feed,
        )
        
        # Reinitialize APIs with new engine
        self.wallet = PaperWalletAPI(self._paper_engine)
        self.leverage = PaperLeverageAPI(self._paper_engine, self.assets)
        self.orders = PaperOrdersAPI(self._paper_engine, self.assets)
        self.positions = PaperPositionsAPI(self._paper_engine, self.assets)
        self.fees = PaperFeesAPI(self._paper_engine)
        
        # Reinitialize external data and monitors if they were enabled
        if self._paper_funding_enabled or self._paper_liquidation_enabled:
            self._external_data = ExternalDataService()
        
        if self._paper_funding_enabled and self._external_data:
            self._paper_funding_monitor = FundingMonitor(
                engine=self._paper_engine,
                external_data=self._external_data,
                enabled=True,
            )
            self._paper_funding_monitor.start()
            logger.info("Funding rate monitor started (8-hour intervals)")
        
        if self._paper_liquidation_enabled and self._external_data:
            self._paper_liquidation_engine = LiquidationEngine(
                engine=self._paper_engine,
                external_data=self._external_data,
                enabled=True,
            )
            self._paper_liquidation_engine.start()
            logger.info("Liquidation engine started")
        
        # Restart SL/TP monitor if it was running
        if self._paper_sltp_monitor:
            self._paper_sltp_monitor = SLTPMonitor(
                engine=self._paper_engine,
                check_interval=self._paper_sltp_interval,
            )
            self._paper_sltp_monitor.start()
        
        logger.info("Paper trading state imported")
    
    def close(self) -> None:
        """Close the client and cleanup resources."""
        if self.mode == "paper":
            try:
                self.save_paper_state()
            except Exception as e:
                logger.warning(f"Failed to save paper state: {e}")
            
            if self._paper_sltp_monitor:
                self._paper_sltp_monitor.stop()
            
            if self._paper_funding_monitor:
                self._paper_funding_monitor.stop()
            
            if self._paper_liquidation_engine:
                self._paper_liquidation_engine.stop()
            
            # PaperDB uses context manager, no explicit close needed
        
        self._session.close()
    
    def __enter__(self) -> "MudrexClient":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
    
    def __repr__(self) -> str:
        """String representation."""
        mode_str = f"mode={self.mode}"
        if self.mode == "paper" and self._paper_engine:
            balance = self._paper_engine.wallet.balance
            mode_str += f", balance=${balance}"
        return f"<MudrexClient {mode_str}>"
