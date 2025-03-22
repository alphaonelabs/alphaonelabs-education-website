import logging

import requests
from django.conf import settings
from django.core.cache import cache

from web.models import Cart

logger = logging.getLogger(__name__)


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
    Convert a text address to latitude and longitude using OpenStreetMap's Nominatim API.
    Follows Nominatim Usage Policy: https://operations.osmfoundation.org/policies/nominatim/
    """
    if not address:
        return None

    # Use caching if available to avoid repeated requests
    cache_key = f"geocode_{address}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json"

    try:
        # Use application name in User-Agent as required by Nominatim ToS
        response = requests.get(url, headers={"User-Agent": "AlphaOneLabs_Education_Website"}, timeout=5)

        if response.status_code != 200:
            logger.error(f"Geocoding error: API returned status {response.status_code}")
            return None

        data = response.json()

        if data and len(data) > 0:

            location = data[0]  # Take the first result
            result = (float(location["lat"]), float(location["lon"]))

            # Cache result for 24 hours to reduce API calls
            cache.set(cache_key, result, 60 * 60 * 24)

            return result
        return None
    except requests.exceptions.Timeout:
        logger.error("Geocoding error: Request timed out")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Geocoding error: {e}")
        return None
    except Exception as e:
        logger.error(f"Geocoding unexpected error: {e}")
        return None
