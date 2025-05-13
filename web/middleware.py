import logging
import traceback
from typing import Any, Callable

import sentry_sdk
from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import Resolver404, resolve

from .models import Course, UserQuiz, WebRequest
from .views import send_slack_message

logger = logging.getLogger(__name__)


class HostnameRewriteMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request):
        # Rewrite the hostname only if it contains alphaonelabs99282llkb
        if "alphaonelabs99282llkb" in request.META.get("HTTP_HOST", ""):
            request.META["HTTP_HOST"] = "alphaonelabs.com"

        # Proceed with the request
        response = self.get_response(request)
        return response


class GlobalExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Proceed with the request
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        from django.conf import settings

        # Don't handle 404 errors, let Django's built-in handling work
        if isinstance(exception, Http404):
            return None

        # Report to Sentry
        sentry_sdk.capture_exception(exception)

        # Print exception details to console
        print("\n=== Exception Details ===")
        print(f"Exception Type: {type(exception).__name__}")
        print(f"Exception Message: {str(exception)}")
        print("\nTraceback:")
        traceback.print_exc()
        print("=====================\n")

        tb = traceback.format_exc()
        error_message = f"ERROR: {str(exception)}\n\n" f"Traceback:\n{tb}\n\n" f"Path: {request.path}"

        if settings.DEBUG:
            context = {
                "error_message": error_message,
                "exception": exception,
                "traceback": tb,
            }
            return render(request, "500.html", context, status=500)
        else:
            send_slack_message(error_message)
            return render(request, "500.html", status=500)

        return None


class WebRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip tracking for static files
        if request.path.startswith("/static/"):
            logger.debug(f"Skipping tracking for static file: {request.path}")
            return self.get_response(request)

        try:
            # Try to resolve the URL to get the view name
            resolver_match = resolve(request.path)
            logger.debug(f"Resolved URL: {request.path} to view: {resolver_match.url_name}")

            # Get client info with default empty strings
            # Get real IP from X-Forwarded-For if available
            ip_address = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get(
                "REMOTE_ADDR", ""
            )
            user = request.user.username if request.user.is_authenticated else ""
            agent = request.META.get("HTTP_USER_AGENT", "")
            referer = request.META.get("HTTP_REFERER", "")

            # Try to get course for course detail pages
            course = None
            if resolver_match.url_name == "course_detail":
                logger.debug(f"Processing course detail page with slug: {resolver_match.kwargs.get('slug')}")
                try:
                    course = Course.objects.get(slug=resolver_match.kwargs["slug"])
                    logger.debug(f"Found course: {course.title}")
                except Course.DoesNotExist:
                    logger.debug("Course not found, will create WebRequest without course association")
                    # Don't return here, continue to create WebRequest without course

            # Get the response first
            response = self.get_response(request)
            logger.debug(f"Response status code: {response.status_code}")

            # Only track successful responses and 404s
            if response.status_code < 500:
                # Create or update web request
                web_request, created = WebRequest.objects.get_or_create(
                    ip_address=ip_address,
                    user=user,
                    agent=agent,
                    path=request.path,
                    course=course,
                    defaults={"referer": referer, "count": 1},
                )

                if not created:
                    web_request.count += 1
                    web_request.referer = referer  # Update referer
                    web_request.save()
                    logger.debug(f"Updated existing web request, new count: {web_request.count}")
                else:
                    logger.debug("Created new web request")

            return response

        except (Http404, Resolver404) as e:
            # Let Django handle 404 errors
            logger.debug(f"Caught 404 error: {str(e)}")
            return self.get_response(request)
        except Exception as e:
            # Log and report unexpected errors before letting Django handle them
            logger.error(f"Unexpected error in middleware: {str(e)}")
            # Report to Sentry
            sentry_sdk.capture_exception(e)
            return self.get_response(request)


class QuizSecurityMiddleware:
    def __init__(self, get_response: Callable[[Any], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip for non-authenticated users, static files, or development tools
        if (
            not request.user.is_authenticated or "/static/" in request.path or "__reload__" in request.path
        ):  # Skip Django Browser Reload
            return self.get_response(request)

        # Check if user has an active quiz in session
        active_quiz_id = request.session.get("active_quiz_id")

        if active_quiz_id:
            # Get current URL details
            resolver_match = resolve(request.path_info)
            current_url_name = resolver_match.url_name

            # Only allowed urls during an active quiz
            allowed_urls = ["take_quiz"]

            # If navigating to a non-allowed URL while quiz is active
            if current_url_name not in allowed_urls:
                # Get the active quiz
                try:
                    user_quiz = UserQuiz.objects.get(id=active_quiz_id, user=request.user, completed=False)
                    # Mark quiz as completed
                    try:
                        user_quiz.complete_quiz()
                        user_quiz.save()
                    except Exception as e:
                        logger.exception("Error completing quiz %s: %s", active_quiz_id, e)

                    # Still clear the session to prevent getting stuck
                    # Clear active quiz from session
                    request.session.pop("active_quiz_id", None)
                    request.session.save()

                    # Notify user
                    messages.warning(request, "Your quiz has been automatically submitted because you navigated away.")

                    # Redirect to results page
                    return redirect("quiz_results", user_quiz_id=active_quiz_id)
                except UserQuiz.DoesNotExist:
                    # If quiz doesn't exist, clear the session variable
                    request.session.pop("active_quiz_id", None)
                    request.session.save()

        # Continue with regular request processing
        return self.get_response(request)
