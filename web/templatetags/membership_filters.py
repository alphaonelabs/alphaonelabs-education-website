from django import template

from web.templatetags.math_utils import safe_divide, safe_multiply, safe_percentage_off, safe_subtract

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
def percentage_off(monthly_price, yearly_price):
    """Calculates the percentage discount of yearly vs monthly billing"""
    return safe_percentage_off(monthly_price, yearly_price, default=0)
