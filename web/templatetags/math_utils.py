def safe_multiply(value, arg, default=None):
    """Multiplies the value by the argument with error handling"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return default


def safe_divide(value, arg, default=None):
    """Divides the value by the argument with error handling"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return default


def safe_subtract(value, arg, default=None):
    """Subtracts the argument from the value with error handling"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return default


def safe_add(value, arg, default=None):
    """Adds the argument to the value with error handling"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return default


def safe_percentage(value, arg=100, default=None):
    """Calculates the percentage of a value with error handling"""
    try:
        return float(value) * float(arg) / 100
    except (ValueError, TypeError):
        return default


def safe_format_currency(value, decimal_places=2, currency_symbol="$", default=None):
    """Formats a number as currency with customizable symbol and error handling"""
    try:
        formatted = "{}{:.{}f}".format(currency_symbol, float(value), decimal_places)
        return formatted
    except (ValueError, TypeError):
        return default


def safe_percentage_off(monthly_price, yearly_price, default=0, min_percentage=0, max_percentage=100):
    """Calculates the percentage discount of yearly vs monthly billing with error handling"""
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
