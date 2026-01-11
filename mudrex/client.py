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
    Simple rate limiter to stay within API limits.
    
    Limits:
    - 2 requests per second
    - 50 requests per minute
    - 1000 requests per hour
    - 10000 requests per day
    """
    
    def __init__(self, requests_per_second: float = 2.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
    
    def wait(self) -> None:
        """Wait if necessary to respect rate limits."""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            logger.debug(f"Rate limiter: sleeping {sleep_time:.3f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()


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
        
        self._paper_engine = None
        self._paper_db = None
        self._paper_sltp_monitor = None
        
        if self.mode == "paper":
            self._init_paper_trading(
                balance=paper_balance,
                db_path=paper_db_path,
                sltp_monitor=paper_sltp_monitor,
                sltp_interval=paper_sltp_interval,
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
    ) -> None:
        """Initialize paper trading engine and APIs."""
        from mudrex.paper import (
            PaperTradingEngine,
            PriceFeedService,
            PaperDB,
            SLTPMonitor,
        )
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
        
        if self._paper_sltp_monitor:
            self._paper_sltp_monitor.stop()
        
        from mudrex.paper import PaperTradingEngine, PriceFeedService
        
        price_feed = PriceFeedService(self)
        self._paper_engine = PaperTradingEngine(
            initial_balance=Decimal(new_balance),
            price_feed=price_feed,
        )
        
        from mudrex.paper.api import (
            PaperOrdersAPI,
            PaperPositionsAPI,
            PaperWalletAPI,
            PaperLeverageAPI,
            PaperFeesAPI,
        )
        
        self.wallet = PaperWalletAPI(self._paper_engine)
        self.leverage = PaperLeverageAPI(self._paper_engine)
        self.orders = PaperOrdersAPI(self._paper_engine)
        self.positions = PaperPositionsAPI(self._paper_engine)
        self.fees = PaperFeesAPI(self._paper_engine)
        
        if self._paper_sltp_monitor:
            from mudrex.paper import SLTPMonitor
            interval = self._paper_sltp_monitor._check_interval
            self._paper_sltp_monitor = SLTPMonitor(
                engine=self._paper_engine,
                check_interval=interval,
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
        
        if self._paper_sltp_monitor:
            self._paper_sltp_monitor.stop()
        
        from mudrex.paper import PaperTradingEngine, PriceFeedService
        
        price_feed = PriceFeedService(self)
        self._paper_engine = PaperTradingEngine.from_state(
            state=state,
            price_feed=price_feed,
        )
        
        from mudrex.paper.api import (
            PaperOrdersAPI,
            PaperPositionsAPI,
            PaperWalletAPI,
            PaperLeverageAPI,
            PaperFeesAPI,
        )
        
        self.wallet = PaperWalletAPI(self._paper_engine)
        self.leverage = PaperLeverageAPI(self._paper_engine)
        self.orders = PaperOrdersAPI(self._paper_engine)
        self.positions = PaperPositionsAPI(self._paper_engine)
        self.fees = PaperFeesAPI(self._paper_engine)
        
        if self._paper_sltp_monitor:
            from mudrex.paper import SLTPMonitor
            interval = self._paper_sltp_monitor._check_interval
            self._paper_sltp_monitor = SLTPMonitor(
                engine=self._paper_engine,
                check_interval=interval,
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
