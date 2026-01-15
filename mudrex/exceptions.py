"""
Mudrex API Exception Classes
============================

Custom exceptions for handling Mudrex API errors with helpful messages.
"""

from typing import Optional, Dict, Any


class MudrexAPIError(Exception):
    """Base exception for all Mudrex API errors."""
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        request_id: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.request_id = request_id
        self.response = response or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.code:
            parts.append(f"Code: {self.code}")
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        if self.request_id:
            parts.append(f"Request ID: {self.request_id}")
        return " | ".join(parts)


class MudrexAuthenticationError(MudrexAPIError):
    """
    Raised when authentication fails.
    
    Common causes:
    - Invalid or expired API secret
    - Missing X-Authentication header
    - API key revoked or not yet activated
    
    Solution:
    - Verify your API secret is correct
    - Generate a new API key if needed
    - Ensure KYC and 2FA are completed
    """
    pass


class MudrexRateLimitError(MudrexAPIError):
    """
    Raised when rate limits are exceeded.
    
    Rate Limits:
    - 2 requests per second
    - 50 requests per minute
    - 1000 requests per hour
    - 10000 requests per day
    
    Solution:
    - Implement exponential backoff
    - Use the built-in rate limiter in MudrexClient
    - Batch operations where possible
    """
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class MudrexValidationError(MudrexAPIError):
    """
    Raised when request validation fails.
    
    Common causes:
    - Invalid parameter values
    - Missing required fields
    - Out-of-range values (e.g., leverage too high)
    
    Solution:
    - Check parameter types and ranges
    - Refer to API documentation for valid values
    """
    pass


class MudrexNotFoundError(MudrexAPIError):
    """
    Raised when a resource is not found.
    
    Common causes:
    - Invalid asset_id or symbol
    - Order or position doesn't exist
    - Resource was deleted
    """
    pass


class MudrexConflictError(MudrexAPIError):
    """
    Raised when there's a conflicting or duplicate action.
    
    Common causes:
    - Duplicate order submission
    - Position already closed
    - Conflicting leverage settings
    """
    pass


class MudrexServerError(MudrexAPIError):
    """
    Raised when the server encounters an internal error.
    
    Solution:
    - Retry with exponential backoff
    - Contact Mudrex support if persistent
    """
    pass


class MudrexInsufficientBalanceError(MudrexAPIError):
    """
    Raised when there's insufficient balance for an operation.
    
    Solution:
    - Check wallet balance before trading
    - Transfer more funds to futures wallet
    - Reduce order size
    """
    pass


# Error code to exception class mapping
ERROR_CODE_MAP = {
    "UNAUTHORIZED": MudrexAuthenticationError,
    "FORBIDDEN": MudrexAuthenticationError,
    "RATE_LIMIT_EXCEEDED": MudrexRateLimitError,
    "INVALID_REQUEST": MudrexValidationError,
    "NOT_FOUND": MudrexNotFoundError,
    "CONFLICT": MudrexConflictError,
    "SERVER_ERROR": MudrexServerError,
    "INSUFFICIENT_BALANCE": MudrexInsufficientBalanceError,
}


def raise_for_error(response: Dict[str, Any], status_code: int) -> None:
    """
    Parse API response and raise appropriate exception if error detected.
    
    Args:
        response: The JSON response from the API
        status_code: HTTP status code
        
    Raises:
        MudrexAPIError: Or a more specific subclass based on error code
    """
    # Check if success is explicitly False (some endpoints don't return success on error)
    if response.get("success", True) and status_code < 400:
        return
    
    code = response.get("code", "UNKNOWN_ERROR")
    message = response.get("message", "An unknown error occurred")
    request_id = response.get("requestId")
    
    # Check for errors array (common Mudrex API format)
    errors = response.get("errors", [])
    if errors:
        # Extract detailed error messages from errors array
        error_texts = [e.get("text", e.get("message", str(e))) for e in errors]
        if error_texts:
            message = "; ".join(error_texts)
            # Try to extract error code from first error
            if errors[0].get("code"):
                code = errors[0].get("code")
    
    exception_class = ERROR_CODE_MAP.get(code, MudrexAPIError)
    
    raise exception_class(
        message=message,
        code=code,
        status_code=status_code,
        request_id=request_id,
        response=response,
    )
