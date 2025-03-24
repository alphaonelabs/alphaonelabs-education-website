from django import template

register = template.Library()


@register.filter
def multiply(value, arg):
    """Multiplies the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value


@register.filter
def divide(value, arg):
    """Divides the value by the argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return value


@register.filter
def subtract(value, arg):
    """Subtracts the argument from the value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value


@register.filter
def add(value, arg):
    """Adds the argument to the value"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return value


@register.filter
def percentage(value, arg=100):
    """Calculates the percentage of a value"""
    try:
        return float(value) * float(arg) / 100
    except (ValueError, TypeError):
        return value


@register.filter
def format_currency(value, decimal_places=2):
    """Formats a number as currency with dollar sign"""
    try:
        formatted = "${:.{}f}".format(float(value), decimal_places)
        return formatted
    except (ValueError, TypeError):
        return value
