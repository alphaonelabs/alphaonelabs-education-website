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
    Convert a text address to latitude and longitude using OpenStreetMap's Nominatim API.
    """
    if not address:
        return None

    url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json"

    try:
        response = requests.get(url, headers={"User-Agent": "YourAppName"})
        data = response.json()

        if data and len(data) > 0:
            location = data[0]  # Take the first result
            return (float(location["lat"]), float(location["lon"]))
        return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None
