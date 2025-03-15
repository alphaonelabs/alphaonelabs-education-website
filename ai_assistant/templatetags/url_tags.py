# Import from web.ai if it exists, otherwise define simple versions
try:
    from web.ai.templatetags.url_tags import *
except ImportError:
    from django import template
    
    register = template.Library()
    
    @register.simple_tag
    def active_url(request, url_name):
        """Return 'active' if the current URL matches the given URL name."""
        if request.resolver_match.url_name == url_name:
            return 'active'
        return ''
    
    @register.simple_tag
    def get_absolute_url(request, path=''):
        """Get absolute URL with domain."""
        protocol = 'https' if request.is_secure() else 'http'
        return f"{protocol}://{request.get_host()}{path}"