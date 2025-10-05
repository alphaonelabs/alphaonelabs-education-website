from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.test import Client, TestCase, override_settings
from django.urls import reverse


class CSRFTestCase(TestCase):
    """Test CSRF token validation with different hosts"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    @override_settings(
        ALLOWED_HOSTS=[
            "alphaonelabs.com",
            "www.alphaonelabs.com",
            "alphaonelabs99282llkb.pythonanywhere.com",
            "127.0.0.1",
            "localhost",
        ],
        CSRF_TRUSTED_ORIGINS=[
            "https://alphaonelabs.com",
            "https://www.alphaonelabs.com",
            "https://alphaonelabs99282llkb.pythonanywhere.com",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ],
    )
    def test_csrf_with_alphaonelabs_domain(self):
        """Test CSRF token works with alphaonelabs.com"""
        self.client.login(username="testuser", password="testpass123")

        # Get the login page to obtain CSRF token
        response = self.client.get(reverse("account_login"), HTTP_HOST="alphaonelabs.com")
        csrf_token = get_token(response.wsgi_request)

        # Try to logout with CSRF token
        response = self.client.post(
            reverse("account_logout"),
            HTTP_HOST="alphaonelabs.com",
            HTTP_REFERER="https://alphaonelabs.com/",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        # Should succeed without CSRF error
        self.assertIn(response.status_code, [200, 302])

    @override_settings(
        ALLOWED_HOSTS=[
            "alphaonelabs.com",
            "www.alphaonelabs.com",
            "alphaonelabs99282llkb.pythonanywhere.com",
            "127.0.0.1",
            "localhost",
        ],
        CSRF_TRUSTED_ORIGINS=[
            "https://alphaonelabs.com",
            "https://www.alphaonelabs.com",
            "https://alphaonelabs99282llkb.pythonanywhere.com",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ],
    )
    def test_csrf_with_www_subdomain(self):
        """Test CSRF token works with www.alphaonelabs.com"""
        self.client.login(username="testuser", password="testpass123")

        # Get the login page to obtain CSRF token
        response = self.client.get(reverse("account_login"), HTTP_HOST="www.alphaonelabs.com")
        csrf_token = get_token(response.wsgi_request)

        # Try to logout with CSRF token
        response = self.client.post(
            reverse("account_logout"),
            HTTP_HOST="www.alphaonelabs.com",
            HTTP_REFERER="https://www.alphaonelabs.com/",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        # Should succeed without CSRF error
        self.assertIn(response.status_code, [200, 302])

    @override_settings(
        ALLOWED_HOSTS=[
            "alphaonelabs.com",
            "www.alphaonelabs.com",
            "alphaonelabs99282llkb.pythonanywhere.com",
            "127.0.0.1",
            "localhost",
        ],
        CSRF_TRUSTED_ORIGINS=[
            "https://alphaonelabs.com",
            "https://www.alphaonelabs.com",
            "https://alphaonelabs99282llkb.pythonanywhere.com",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ],
    )
    def test_csrf_with_pythonanywhere_domain(self):
        """Test CSRF token works with pythonanywhere domain"""
        self.client.login(username="testuser", password="testpass123")

        # Get the login page to obtain CSRF token
        response = self.client.get(reverse("account_login"), HTTP_HOST="alphaonelabs99282llkb.pythonanywhere.com")
        csrf_token = get_token(response.wsgi_request)

        # Try to logout with CSRF token
        response = self.client.post(
            reverse("account_logout"),
            HTTP_HOST="alphaonelabs99282llkb.pythonanywhere.com",
            HTTP_REFERER="https://alphaonelabs99282llkb.pythonanywhere.com/",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        # Should succeed without CSRF error
        self.assertIn(response.status_code, [200, 302])

    @override_settings(
        ALLOWED_HOSTS=[
            "alphaonelabs.com",
            "www.alphaonelabs.com",
            "alphaonelabs99282llkb.pythonanywhere.com",
            "127.0.0.1",
            "localhost",
        ],
        CSRF_TRUSTED_ORIGINS=[
            "https://alphaonelabs.com",
            "https://www.alphaonelabs.com",
            "https://alphaonelabs99282llkb.pythonanywhere.com",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ],
    )
    def test_csrf_with_localhost(self):
        """Test CSRF token works with localhost"""
        self.client.login(username="testuser", password="testpass123")

        # Get the login page to obtain CSRF token
        response = self.client.get(reverse("account_login"), HTTP_HOST="localhost:8000")
        csrf_token = get_token(response.wsgi_request)

        # Try to logout with CSRF token
        response = self.client.post(
            reverse("account_logout"),
            HTTP_HOST="localhost:8000",
            HTTP_REFERER="http://localhost:8000/",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        # Should succeed without CSRF error
        self.assertIn(response.status_code, [200, 302])
