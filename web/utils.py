import requests
from django.conf import settings
import logging
from django.db.models.fields import FieldDoesNotExist
from django.core.exceptions import FieldError

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
    Convert a text address to latitude and longitude coordinates.
    Returns a tuple of (latitude, longitude) or None if geocoding fails.

    Need to add a GEOCODING_API_KEY to your settings.py
    and sign up for a service like Google Maps, Mapbox, or OpenCage.
    """
    if not address:
        return None

    # Using OpenCage Geocoder
    api_key = getattr(settings, "OPENCAGE_API_KEY", "")
    if not api_key:
        return None

    from urllib.parse import quote
    encoded_address = quote(address)
    url = f"https://api.opencagedata.com/geocode/v1/json?q={encoded_address}&key={api_key}"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        if data["total_results"] > 0:
            location = data["results"][0]["geometry"]
            return (location["lat"], location["lng"])
        return None
    except Exception as e:
        logger.error(f"Geocoding error for address '{address}': {e}")
        return None


def apply_map_filters(sessions, subject_id, age_group, teaching_style):
    """Apply common filters to session querysets for map views"""
    if subject_id:
        sessions = sessions.filter(course__subject_id=subject_id)

    if age_group:
        sessions = sessions.filter(course__level=age_group)

    if teaching_style:
        try:
            # Attempt to filter, but don't fail if field doesn't exist
            sessions = sessions.filter(course__teaching_style=teaching_style)
        except (FieldError, FieldDoesNotExist) as e:
            # Log the error but continue without this filter
            logger.error(f"Error filtering by teaching_style: {e}")

    return sessions
