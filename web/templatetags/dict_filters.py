from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key, default=0):
    """
    Access a dictionary value by key, with type conversion and error handling.

    Args:
        dictionary: The dictionary to access
        key: The key to look up (will be converted to int if it's a digit string)
        default: The default value to return if key is not found (defaults to 0)

    Returns:
        The value for the key or the default value if not found or on error
    """
    try:
        # If key is a string digit, convert to int
        if isinstance(key, str) and key.isdigit():
            key = int(key)
        return dictionary.get(key, default)
    except (ValueError, AttributeError, TypeError):
        return default
