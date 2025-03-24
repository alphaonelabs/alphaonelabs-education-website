from django import template
from decimal import Decimal

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
def percentage_off(monthly_price, yearly_price):
    """Calculates the percentage discount of yearly vs monthly billing"""
    try:
        monthly = float(monthly_price)
        yearly = float(yearly_price)
        monthly_total = monthly * 12
        savings = monthly_total - yearly
        percentage = (savings / monthly_total) * 100
        return int(percentage)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0 