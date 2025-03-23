# /tests/conftest.py and /web/tests/conftest.py
import pytest
from django.contrib.auth.models import User

from web.models import Course, Profile, Subject


# @pytest.fixture
@pytest.fixture(scope="class")
def test_user():
    user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
    yield user
    # No need to delete due to transaction rollback


@pytest.fixture
def test_teacher():
    teacher = User.objects.create_user(
        username="teacher",
        email="teacher@example.com",
        password="teacherpass123",
    )
    Profile.objects.get_or_create(user=teacher, defaults={"is_teacher": True})
    return teacher


@pytest.fixture
def test_subject():
    return Subject.objects.create(
        name="Test Subject", slug="test-subject", description="Test description", icon="fas fa-code"
    )


@pytest.fixture
def test_course(test_teacher, test_subject):
    return Course.objects.create(
        title="Test Course",
        description="Test Description",
        teacher=test_teacher,
        price=99.99,
        max_students=50,
        subject=test_subject,
        level="beginner",
    )


# Add a fixture for authenticated client to avoid repeated logins
@pytest.fixture(scope="function")
def authenticated_client(client, test_user):
    """Returns a client logged in as test_user."""
    client.login(username="testuser", password="testpass123")
    return client
