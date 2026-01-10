"""
Paper Trading Exceptions
========================

Custom exceptions for paper trading operations.
"""


class PaperTradingError(Exception):
    """Base exception for paper trading errors."""
    
    def __init__(self, message: str, code: str = "PAPER_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)
    
    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class InsufficientMarginError(PaperTradingError):
    """
    Raised when there's not enough margin for an order.
    
    Example:
        Order requires $500 margin but only $300 available.
    """
    
    def __init__(self, required: str, available: str, message: str = None):
        self.required = required
        self.available = available
        msg = message or f"Insufficient margin: requires {required} USDT, only {available} available"
        super().__init__(msg, "INSUFFICIENT_MARGIN")


class InvalidOrderError(PaperTradingError):
    """
    Raised when order parameters are invalid.
    
    Examples:
        - Quantity below minimum
        - Leverage exceeds maximum
        - Invalid symbol
    """
    
    def __init__(self, field: str, value: str, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        msg = f"Invalid order: {field}={value} - {reason}"
        super().__init__(msg, "INVALID_ORDER")


class PositionNotFoundError(PaperTradingError):
    """Raised when trying to access a position that doesn't exist."""
    
    def __init__(self, position_id: str):
        self.position_id = position_id
        msg = f"Position not found: {position_id}"
        super().__init__(msg, "POSITION_NOT_FOUND")


class OrderNotFoundError(PaperTradingError):
    """Raised when trying to access an order that doesn't exist."""
    
    def __init__(self, order_id: str):
        self.order_id = order_id
        msg = f"Order not found: {order_id}"
        super().__init__(msg, "ORDER_NOT_FOUND")


class SymbolNotFoundError(PaperTradingError):
    """Raised when trying to trade an invalid or unsupported symbol."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        msg = f"Symbol not found or not tradeable: {symbol}"
        super().__init__(msg, "SYMBOL_NOT_FOUND")


class PositionAlreadyClosedError(PaperTradingError):
    """Raised when trying to modify a closed position."""
    
    def __init__(self, position_id: str):
        self.position_id = position_id
        msg = f"Position already closed: {position_id}"
        super().__init__(msg, "POSITION_CLOSED")


class OrderAlreadyFilledError(PaperTradingError):
    """Raised when trying to cancel a filled order."""
    
    def __init__(self, order_id: str):
        self.order_id = order_id
        msg = f"Order already filled: {order_id}"
        super().__init__(msg, "ORDER_FILLED")


class LiquidationWarning(PaperTradingError):
    """
    Warning when position is approaching liquidation.
    
    Note: V1 does not auto-liquidate, only warns.
    """
    
    def __init__(self, position_id: str, current_price: str, liquidation_price: str):
        self.position_id = position_id
        self.current_price = current_price
        self.liquidation_price = liquidation_price
        msg = f"Position {position_id} approaching liquidation: current={current_price}, liq={liquidation_price}"
        super().__init__(msg, "LIQUIDATION_WARNING")


class PriceFetchError(PaperTradingError):
    """Raised when unable to fetch current price from Mudrex."""
    
    def __init__(self, symbol: str, reason: str = None):
        self.symbol = symbol
        msg = f"Failed to fetch price for {symbol}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg, "PRICE_FETCH_ERROR")
