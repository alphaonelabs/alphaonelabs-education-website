from django.contrib.auth.models import User
from django.test import TestCase

from web.models import Profile


class NotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user(
            username="teacher", email="teacher@example.com", password="teacherpass123"
        )
        cls.student = User.objects.create_user(
            username="student", email="student@example.com", password="studentpass123"
        )
        cls.teacher_profile, _ = Profile.objects.get_or_create(user=cls.teacher, defaults={"is_teacher": True})
        cls.student_profile, _ = Profile.objects.get_or_create(user=cls.student, defaults={"is_teacher": False})


class RecommendationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user(
            username="teacher", email="teacher@example.com", password="teacherpass123"
        )
        cls.student = User.objects.create_user(
            username="student", email="student@example.com", password="studentpass123"
        )
        cls.teacher_profile, _ = Profile.objects.get_or_create(user=cls.teacher, defaults={"is_teacher": True})
        cls.student_profile, _ = Profile.objects.get_or_create(user=cls.student, defaults={"is_teacher": False})


class CalendarSyncTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user(
            username="teacher", email="teacher@example.com", password="teacherpass123"
        )
        cls.student = User.objects.create_user(
            username="student", email="student@example.com", password="studentpass123"
        )
        cls.teacher_profile, _ = Profile.objects.get_or_create(user=cls.teacher, defaults={"is_teacher": True})
        cls.student_profile, _ = Profile.objects.get_or_create(user=cls.student, defaults={"is_teacher": False})


class ForumTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user(
            username="teacher", email="teacher@example.com", password="teacherpass123"
        )
        cls.student = User.objects.create_user(
            username="student", email="student@example.com", password="studentpass123"
        )
        cls.teacher_profile, _ = Profile.objects.get_or_create(user=cls.teacher, defaults={"is_teacher": True})
        cls.student_profile, _ = Profile.objects.get_or_create(user=cls.student, defaults={"is_teacher": False})
