"""
Helper utilities for smarter order handling.
"""

from typing import Tuple

def calculate_order_from_usd(
    usd_amount: float,
    price: float,
    quantity_step: float
) -> Tuple[float, float]:
    """
    Calculate order quantity from USD amount and round to quantity_step.
    
    Args:
        usd_amount: Amount in USD to trade
        price: Current price of the asset
        quantity_step: Minimum quantity increment (from asset info)
    
    Returns:
        Tuple of (rounded_quantity, actual_usd_value)
    
    Example:
        \u003e\u003e\u003e qty, value = calculate_order_from_usd(5.0, 1.905, 0.1)
        \u003e\u003e\u003e print(f"Buy {qty} for ${value}")
        Buy 2.6 for $4.953
    """
    raw_quantity = usd_amount / price
    rounded_quantity = round(raw_quantity / quantity_step) * quantity_step
    
    # Determine precision
    precision = len(str(quantity_step).split('.')[-1]) if '.' in str(quantity_step) else 0
    rounded_quantity = round(rounded_quantity, precision)
    
    actual_value = rounded_quantity * price
    
    return rounded_quantity, actual_value


def validate_quantity(quantity: float, quantity_step: float) -> bool:
    """
    Check if quantity is a valid multiple of quantity_step.
    
    Args:
        quantity: Quantity to validate
        quantity_step: Required step size
    
    Returns:
        True if valid, False otherwise
    """
    if quantity_step == 0:
        return True
    
    remainder = quantity % quantity_step
    # Allow small floating point errors
    return abs(remainder) < (quantity_step * 0.01)
