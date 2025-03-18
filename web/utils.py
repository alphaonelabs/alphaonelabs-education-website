import requests
from django.conf import settings

from web.models import Cart


def send_slack_message(message):
    """Send message to Slack webhook"""
    webhook_url = settings.SLACK_WEBHOOK_URL
    if not webhook_url:
        return False

    try:
        response = requests.post(webhook_url, json={"text": message})
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def format_currency(amount):
    """Format amount as currency"""
    return f"${amount:.2f}"


def get_or_create_cart(request):
    """Helper function to get or create a cart for both logged in and guest users."""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


def geocode_address(address):
    """
    Convert a text address to latitude and longitude coordinates.
    Returns a tuple of (latitude, longitude) or None if geocoding fails.
    
    Need to add a GEOCODING_API_KEY to your settings.py
    and sign up for a service like Google Maps, Mapbox, or OpenCage.
    """
    if not address:
        return None
        
    # Using OpenCage Geocoder
    api_key = getattr(settings, 'OPENCAGE_API_KEY', '')
    if not api_key:
        return None
        
    url = f"https://api.opencagedata.com/geocode/v1/json?q={address}&key={api_key}"
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data['total_results'] > 0:
            location = data['results'][0]['geometry']
            return (location['lat'], location['lng'])
        return None
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Geocoding error for address '{address}': {e}")
        return None