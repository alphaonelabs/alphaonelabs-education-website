import pytz
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt
@require_POST
def set_timezone(request):
    """
    Sets the timezone for the current session based on the client's local timezone.
    Expected POST data: timezone (e.g., 'America/New_York')
    """
    timezone_name = request.POST.get("timezone")

    if not timezone_name:
        return JsonResponse({"status": "error", "message": "No timezone provided"}, status=400)

    # Validate the timezone
    try:
        pytz.timezone(timezone_name)
    except pytz.exceptions.UnknownTimeZoneError:
        return JsonResponse({"status": "error", "message": "Invalid timezone"}, status=400)

from django.http import HttpRequest

def set_timezone(request: HttpRequest) -> JsonResponse:
    # Store in session
    request.session["user_timezone"] = timezone_name

    return JsonResponse({"status": "success", "timezone": timezone_name})
