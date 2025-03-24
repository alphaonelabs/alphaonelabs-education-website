from django import template

from web.templatetags.math_utils import (
    safe_add,
    safe_divide,
    safe_format_currency,
    safe_multiply,
    safe_percentage,
    safe_subtract,
)

register = template.Library()


@register.filter
def multiply(value, arg):
    """Multiplies the value by the argument"""
    return safe_multiply(value, arg, default=value)


@register.filter
def divide(value, arg):
    """Divides the value by the argument"""
    return safe_divide(value, arg, default=value)


@register.filter
def subtract(value, arg):
    """Subtracts the argument from the value"""
    return safe_subtract(value, arg, default=value)


@register.filter
def add(value, arg):
    """Adds the argument to the value"""
    return safe_add(value, arg, default=value)


@register.filter
def percentage(value, arg=100):
    """Calculates the percentage of a value"""
    return safe_percentage(value, arg, default=value)


@register.filter
def format_currency(value, decimal_places=2, currency_symbol="$"):
    """Formats a number as currency with customizable symbol"""
    return safe_format_currency(value, decimal_places, currency_symbol, default=value)
