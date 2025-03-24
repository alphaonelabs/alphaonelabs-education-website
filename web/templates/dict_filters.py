from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    # Convert to int if needed
    try:
        if isinstance(key, str) and key.isdigit():
            key = int(key)
        return dictionary.get(key, 0)
    except (ValueError, AttributeError, TypeError):
        return 0