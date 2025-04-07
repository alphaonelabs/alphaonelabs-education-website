from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from web.models import Profile, Course, Enrollment, CourseProgress, Achievement

class UsersViewTests(TestCase):
    def setUp(self):
        # Create teacher user and profile with is_profile_public enabled
        self.teacher_user = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="password"
        )
        self.teacher_profile = Profile.objects.create(
            user=self.teacher_user,
            role="teacher",  # Assuming the Profile model has a 'role' field
            is_profile_public=True
        )
        
        # Create student user and profile with is_profile_public enabled
        self.student_user = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="password"
        )
        self.student_profile = Profile.objects.create(
            user=self.student_user,
            role="student",  # Assuming the Profile model has a 'role' field
            is_profile_public=True
        )

    def test_users_list_view(self):
        client = Client()
        url = reverse("users_list")  # Use the URL name "users_list"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("page_obj", response.context)
        
        page_obj = response.context["page_obj"]
        for user in page_obj:
            # Check based on the user's role attribute
            if hasattr(user, "role") and user.role == "teacher":
                self.assertTrue(
                    hasattr(user, "total_courses"),
                    "Teacher missing total_courses"
                )
                self.assertTrue(
                    hasattr(user, "total_students"),
                    "Teacher missing total_students"
                )
                self.assertTrue(
                    hasattr(user, "avg_rating"),
                    "Teacher missing avg_rating"
                )
            elif hasattr(user, "role") and user.role == "student":
                self.assertTrue(
                    hasattr(user, "total_courses"),
                    "Student missing total_courses"
                )
                self.assertTrue(
                    hasattr(user, "total_completed"),
                    "Student missing total_completed"
                )
                self.assertTrue(
                    hasattr(user, "avg_progress"),
                    "Student missing avg_progress"
                )
                self.assertTrue(
                    hasattr(user, "achievements_count"),
                    "Student missing achievements_count"
                )