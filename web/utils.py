from django.conf import settings
from web.models import Cart
import requests


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


# To geocode address
def geocode_address(address):
    """
    Convert a text address to latitude and longitude coordinates using Google Maps API.
    Returns a tuple of (latitude, longitude) or None if geocoding fails.

    You'll need to add a `GOOGLE_MAPS_API_KEY` to your settings.py.
    """
    if not address:
        return None
    api_key = getattr(settings, "GM_API_KEY", "")
    if not api_key:
        print("Google Maps API key is missing in settings.")
        return None

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
        data = response.json()

        if data.get("status") == "OK":
            location = data["results"][0]["geometry"]["location"]
            return (location["lat"], location["lng"])
        else:
            print(f"Geocoding failed: {data.get('status')}")
            return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None
