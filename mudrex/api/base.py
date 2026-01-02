"""
Base API Module
===============

Base class for all API modules with shared functionality.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from mudrex.client import MudrexClient


class BaseAPI:
    """Base class for API modules."""
    
    def __init__(self, client: "MudrexClient"):
        self._client = client
    
    def _get(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        use_symbol: bool = False,
    ) -> Dict[str, Any]:
        """
        Make a GET request.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            use_symbol: If True, adds is_symbol query parameter for symbol-based lookups
        """
        if params is None:
            params = {}
        if use_symbol:
            params["is_symbol"] = ""  # Just needs to be present
        return self._client.get(endpoint, params)
    
    def _post(
        self, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        use_symbol: bool = False,
    ) -> Dict[str, Any]:
        """
        Make a POST request.
        
        Args:
            endpoint: API endpoint path
            data: JSON body data
            use_symbol: If True, endpoint uses symbol instead of asset_id
        """
        # For POST, we append is_symbol to the endpoint as query param
        if use_symbol:
            endpoint = f"{endpoint}?is_symbol"
        return self._client.post(endpoint, data)
    
    def _patch(
        self, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        use_symbol: bool = False,
    ) -> Dict[str, Any]:
        """Make a PATCH request."""
        if use_symbol:
            endpoint = f"{endpoint}?is_symbol"
        return self._client.patch(endpoint, data)
    
    def _delete(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        use_symbol: bool = False,
    ) -> Dict[str, Any]:
        """Make a DELETE request."""
        if params is None:
            params = {}
        if use_symbol:
            params["is_symbol"] = ""
        return self._client.delete(endpoint, params)
