"""
Mudrex API Client
=================

The main client class for interacting with Mudrex Trading API.
Handles authentication, rate limiting, and provides access to all API modules.
"""

import time
import logging
from typing import Optional, Dict, Any, Callable
from urllib.parse import urljoin
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
    
    Example:
        >>> client = MudrexClient(api_secret="your-secret-key")
        >>> 
        >>> # Check balance
        >>> balance = client.wallet.get_spot_balance()
        >>> print(f"Available: {balance.available}")
        >>> 
        >>> # Get assets
        >>> assets = client.assets.list_all()
        >>> for asset in assets:
        ...     print(f"{asset.symbol}: max leverage {asset.max_leverage}x")
        >>> 
        >>> # Place an order
        >>> order = client.orders.create_market_order(
        ...     asset_id="BTCUSDT",
        ...     side="LONG",
        ...     quantity="0.001",
        ...     leverage="5",
        ... )
    
    Args:
        api_secret: Your Mudrex API secret key
        base_url: API base URL (default: https://trade.mudrex.com/fapi/v1)
        timeout: Request timeout in seconds (default: 30)
        rate_limit: Enable automatic rate limiting (default: True)
        max_retries: Maximum retries on rate limit errors (default: 3)
        
    Attributes:
        wallet: Wallet management endpoints
        assets: Asset discovery endpoints
        leverage: Leverage management endpoints
        orders: Order management endpoints
        positions: Position management endpoints
        fees: Fee history endpoints
    """
    
    BASE_URL = "https://trade.mudrex.com/fapi/v1"
    
    def __init__(
        self,
        *,  # Force keyword-only arguments
        api_secret: str,
        base_url: Optional[str] = None,
        timeout: int = 30,
        rate_limit: bool = True,
        max_retries: int = 3,
    ):
        if not api_secret:
            raise ValueError("api_secret is required")
        
        # Validate api_secret doesn't look like a URL (common mistake)
        if api_secret.startswith(("http://", "https://", "www.")):
            raise ValueError(
                "api_secret looks like a URL. Did you mean to use base_url? "
                "Usage: MudrexClient(api_secret='your-secret-key')"
            )
        
        self.api_secret = api_secret
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Set up rate limiter
        self._rate_limiter = RateLimiter() if rate_limit else None
        
        # Set up session with default headers
        self._session = requests.Session()
        self._session.headers.update({
            "X-Authentication": api_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "mudrex-python-sdk/1.0.0",
        })
        
        # Initialize API modules
        self.wallet = WalletAPI(self)
        self.assets = AssetsAPI(self)
        self.leverage = LeverageAPI(self)
        self.orders = OrdersAPI(self)
        self.positions = PositionsAPI(self)
        self.fees = FeesAPI(self)
    
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
        """
        Make an API request with rate limiting and retry logic.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body data
            
        Returns:
            Parsed JSON response
            
        Raises:
            MudrexAPIError: On API errors
            MudrexRateLimitError: When rate limited (after retries exhausted)
        """
        url = self._build_url(endpoint)
        
        for attempt in range(self.max_retries + 1):
            # Apply rate limiting
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
                
                # Parse response
                try:
                    data = response.json()
                except ValueError:
                    data = {"success": False, "message": response.text}
                
                # Handle rate limiting with retry
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
                
                # Raise for other errors
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
    
    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()
    
    def __enter__(self) -> "MudrexClient":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
