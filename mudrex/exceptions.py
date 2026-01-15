"""
Mudrex API Exception Classes
============================

User-friendly exceptions with clear, human-readable error messages.
Technical details are included in brackets for developers.
"""

from typing import Optional, Dict, Any


# Human-readable error messages for common API errors
FRIENDLY_MESSAGES = {
    # Authentication errors
    "UNAUTHORIZED": "Your API key is invalid or has expired. Please check your credentials or generate a new API key.",
    "FORBIDDEN": "Access denied. Your account may not have permission for this action.",
    "invalid api key": "Your API key is invalid. Please check that you're using the correct Secret Key.",
    "authentication failed": "Login failed. Please verify your API credentials.",
    
    # Rate limiting
    "RATE_LIMIT_EXCEEDED": "Too many requests. Please slow down and try again in a few seconds.",
    "rate limit": "You're making requests too quickly. Please wait a moment before trying again.",
    
    # Validation errors
    "INVALID_REQUEST": "The request contains invalid data. Please check your input values.",
    "quantity not a multiple": "The order quantity must match the asset's minimum step size. The SDK should auto-round this - please report if you see this error.",
    "order value less than minimum": "Order value is too small. Please increase the quantity or use a different asset.",
    "leverage out of range": "The leverage value is outside the allowed range for this asset.",
    "insufficient balance": "Not enough funds in your wallet. Please deposit more or reduce your order size.",
    "insufficient margin": "Not enough margin for this trade. Please add more funds or reduce position size.",
    
    # Not found errors
    "NOT_FOUND": "The requested item was not found. It may have been deleted or never existed.",
    "asset not found": "This trading pair is not available. Please check the symbol name.",
    "order not found": "This order does not exist. It may have been filled or cancelled.",
    "position not found": "This position does not exist. It may have been closed.",
    
    # Conflict errors
    "CONFLICT": "This action conflicts with existing data. The item may already exist.",
    "position already closed": "This position has already been closed.",
    "order already cancelled": "This order has already been cancelled.",
    
    # Server errors
    "SERVER_ERROR": "The Mudrex server encountered an error. Please try again later.",
    "internal server error": "Something went wrong on Mudrex's side. Please try again in a few minutes.",
    "service unavailable": "The trading service is temporarily unavailable. Please try again later.",
    
    # Trading specific
    "market closed": "The market is currently closed. Please try again when trading resumes.",
    "trading disabled": "Trading is temporarily disabled for this asset.",
    "max positions reached": "You've reached the maximum number of open positions allowed.",
}


def get_friendly_message(error_text: str, error_code: str = "") -> str:
    """
    Convert technical error text to a user-friendly message.
    
    Args:
        error_text: The original error message from the API
        error_code: Optional error code
        
    Returns:
        A human-readable error message
    """
    error_lower = error_text.lower()
    code_upper = error_code.upper() if error_code else ""
    
    # First check by error code
    if code_upper in FRIENDLY_MESSAGES:
        return FRIENDLY_MESSAGES[code_upper]
    
    # Then check by error text patterns
    for pattern, friendly_msg in FRIENDLY_MESSAGES.items():
        if pattern.lower() in error_lower:
            return friendly_msg
    
    # Default: return original with slight improvement
    return error_text.capitalize() if error_text else "An unexpected error occurred."


class MudrexAPIError(Exception):
    """
    Base exception for all Mudrex API errors.
    
    Provides both user-friendly messages and technical details.
    
    Attributes:
        message: Human-readable error message for UI display
        technical_message: Original technical error from API
        code: Error code (if available)
        status_code: HTTP status code
        request_id: Request ID for support tickets
    
    Example:
        >>> try:
        ...     client.orders.create_market_order(...)
        ... except MudrexAPIError as e:
        ...     # Show to user
        ...     print(e.message)
        ...     # Log for debugging
        ...     print(f"Technical: {e.technical_message} [Code: {e.code}]")
    """
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        request_id: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None,
    ):
        self.technical_message = message
        self.message = get_friendly_message(message, code or "")
        self.code = code
        self.status_code = status_code
        self.request_id = request_id
        self.response = response or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """Return user-friendly message with technical details in brackets."""
        parts = [self.message]
        
        # Add technical details in brackets for developers
        technical = []
        if self.code:
            technical.append(f"Code: {self.code}")
        if self.status_code:
            technical.append(f"Status: {self.status_code}")
        if self.request_id:
            technical.append(f"Request ID: {self.request_id}")
        
        if technical:
            parts.append(f"[{', '.join(technical)}]")
        
        return " ".join(parts)
    
    def for_ui(self) -> str:
        """Get clean message suitable for UI display (no technical details)."""
        return self.message
    
    def for_log(self) -> str:
        """Get detailed message suitable for logging."""
        return f"{self.message} | Technical: {self.technical_message} | Code: {self.code} | Status: {self.status_code} | Request ID: {self.request_id}"


class MudrexAuthenticationError(MudrexAPIError):
    """
    Your API key is invalid, expired, or missing.
    
    How to fix:
    - Verify you're using the correct Secret Key (not API Key)
    - Generate a new API key from your Mudrex dashboard
    - Ensure KYC and 2FA are completed on your account
    """
    pass


class MudrexRateLimitError(MudrexAPIError):
    """
    You're making too many requests.
    
    Rate Limits:
    - 2 requests per second
    - 50 requests per minute
    - 1000 requests per hour
    - 10000 requests per day
    
    How to fix:
    - Wait a few seconds before retrying
    - Use the built-in rate limiter (enabled by default)
    - Batch operations where possible
    """
    
    def __init__(
        self,
        message: str = "Too many requests. Please slow down and try again.",
        retry_after: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
    
    def __str__(self) -> str:
        base = super().__str__()
        if self.retry_after:
            return f"{base} (Retry after {self.retry_after:.1f}s)"
        return base


class MudrexValidationError(MudrexAPIError):
    """
    The request contains invalid data.
    
    Common causes:
    - Order quantity doesn't match asset's step size
    - Leverage outside allowed range
    - Price outside allowed range
    - Missing required fields
    """
    pass


class MudrexNotFoundError(MudrexAPIError):
    """
    The requested resource was not found.
    
    Common causes:
    - Invalid symbol name (use correct format like "BTCUSDT")
    - Order/position was already filled/closed
    - Resource was deleted
    """
    pass


class MudrexConflictError(MudrexAPIError):
    """
    Action conflicts with existing data.
    
    Common causes:
    - Trying to create duplicate order
    - Position already closed
    - Resource already exists
    """
    pass


class MudrexServerError(MudrexAPIError):
    """
    Mudrex server encountered an error.
    
    How to fix:
    - Wait a moment and try again
    - Check Mudrex status page for outages
    - Contact support if the problem persists
    """
    pass


class MudrexInsufficientBalanceError(MudrexAPIError):
    """
    Not enough funds for this operation.
    
    How to fix:
    - Check your wallet balance
    - Transfer more funds to futures wallet
    - Reduce order size or leverage
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

# HTTP status code to exception class mapping
STATUS_CODE_MAP = {
    401: MudrexAuthenticationError,
    403: MudrexAuthenticationError,
    404: MudrexNotFoundError,
    409: MudrexConflictError,
    429: MudrexRateLimitError,
    500: MudrexServerError,
    502: MudrexServerError,
    503: MudrexServerError,
}


def raise_for_error(response: Dict[str, Any], status_code: int) -> None:
    """
    Parse API response and raise appropriate exception if error detected.
    
    Creates user-friendly error messages suitable for UI display.
    
    Args:
        response: The JSON response from the API
        status_code: HTTP status code
        
    Raises:
        MudrexAPIError: Or a more specific subclass based on error
    """
    # Check if success is explicitly False
    if response.get("success", True) and status_code < 400:
        return
    
    code = response.get("code", "")
    message = response.get("message", "An unexpected error occurred")
    request_id = response.get("requestId")
    
    # Handle string code (convert to string if int)
    if isinstance(code, int):
        code = str(code)
    
    # Check for errors array (common Mudrex API format)
    errors = response.get("errors", [])
    if errors:
        error_texts = [e.get("text", e.get("message", str(e))) for e in errors]
        if error_texts:
            message = "; ".join(error_texts)
            # Try to extract error code from first error
            if errors[0].get("code"):
                code = str(errors[0].get("code"))
    
    # Determine exception class
    exception_class = ERROR_CODE_MAP.get(code.upper() if code else "", None)
    if not exception_class:
        exception_class = STATUS_CODE_MAP.get(status_code, MudrexAPIError)
    
    # Handle rate limit specially to include retry_after
    if exception_class == MudrexRateLimitError:
        raise MudrexRateLimitError(
            message=message,
            code=code,
            status_code=status_code,
            request_id=request_id,
            response=response,
            retry_after=response.get("retry_after"),
        )
    
    raise exception_class(
        message=message,
        code=code,
        status_code=status_code,
        request_id=request_id,
        response=response,
    )
