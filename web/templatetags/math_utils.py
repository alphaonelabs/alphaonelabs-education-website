def safe_multiply(value: float, arg: float, default: float = None) -> float:
    """
    Multiplies the value by the argument with error handling.

    Args:
        value: The first value to multiply
        arg: The second value to multiply
        default: Value to return if an error occurs

    Returns:
        The product of value and arg as a float, or default if an error occurs
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return default


def safe_divide(value: float, arg: float, default: float = None) -> float:
    """
    Divides the value by the argument with error handling.

    Args:
        value: The numerator value
        arg: The denominator value
        default: Value to return if an error occurs

    Returns:
        The result of value divided by arg as a float, or default if an error occurs
    """
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return default


def safe_subtract(value: float, arg: float, default: float = None) -> float:
    """
    Subtracts the argument from the value with error handling.

    Args:
        value: The value to subtract from
        arg: The value to subtract
        default: Value to return if an error occurs

    Returns:
        The result of value minus arg as a float, or default if an error occurs
    """
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return default


def safe_add(value: float, arg: float, default: float = None) -> float:
    """
    Adds the argument to the value with error handling.

    Args:
        value: The first value to add
        arg: The second value to add
        default: Value to return if an error occurs

    Returns:
        The sum of value and arg as a float, or default if an error occurs
    """
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return default


def safe_percentage(value: float, arg: float = 100, default: float = None) -> float:
    """
    Calculates the percentage of a value with error handling.

    Args:
        value: The base value
        arg: The percentage to calculate
        default: Value to return if an error occurs

    Returns:
        The calculated percentage as a float, or default if an error occurs
    """
    try:
        return float(value) * float(arg) / 100
    except (ValueError, TypeError):
        return default


def safe_format_currency(value: float, decimal_places: int = 2, currency_symbol: str = "$", default: str = None) -> str:
    """
    Formats a number as currency with customizable symbol and error handling.

    Args:
        value: The numeric value to format
        decimal_places: Number of decimal places to include
        currency_symbol: Currency symbol to prepend to the value
        default: Value to return if an error occurs

    Returns:
        Formatted currency string, or default if an error occurs
    """
    try:
        formatted = "{}{:.{}f}".format(currency_symbol, float(value), decimal_places)
        return formatted
    except (ValueError, TypeError):
        return default


def safe_percentage_off(
    monthly_price: float,
    yearly_price: float,
    default: float = 0,
    min_percentage: float = 0,
    max_percentage: float = 100,
) -> int:
    """
    Calculates the percentage discount of yearly vs monthly billing with error handling.

    Args:
        monthly_price: The monthly price
        yearly_price: The yearly price
        default: Value to return if an error occurs
        min_percentage: Minimum allowed percentage value
        max_percentage: Maximum allowed percentage value

    Returns:
        The percentage discount as an integer, or default if an error occurs
    """
    try:
        monthly = float(monthly_price)
        yearly = float(yearly_price)
        monthly_total = monthly * 12

        # Add a minimum threshold check to avoid unrealistic discounts
        MIN_THRESHOLD = 0.01  # $0.01 minimum meaningful price
        if monthly_total < MIN_THRESHOLD:
            return default

        savings = monthly_total - yearly
        percentage = (savings / monthly_total) * 100

        # Cap the percentage to a reasonable range (default: 0-100%)
        percentage = max(min_percentage, min(max_percentage, percentage))

        return int(percentage)
    except (ValueError, TypeError, ZeroDivisionError):
        return default
