from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse

from web.models import Quiz, QuizQuestion, QuizOption

User = get_user_model()

class QuizAdminTests(TestCase):
    def setUp(self):
        # Create superuser for admin access
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123"
        )
        self.client = Client()
        self.client.login(username="admin", password="adminpass123")
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        self.captured_queries = CaptureQueriesContext(connection)
        self.quiz = Quiz.objects.create(
            title="Test Admin Quiz",
            description="Test quiz description for admin",
            start_date=timezone.now().date(),
            start_time=timezone.now().time(),
            end_date=(timezone.now() + timedelta(days=7)).date(),
            end_time=timezone.now().time(),
            duration_minutes=60
        )
    
    def test_quiz_admin_list(self):
        """Test that quizzes appear in admin list view"""
        admin_url = reverse('admin:web_quiz_changelist')
        response = self.client.get(admin_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Admin Quiz")

    def test_quiz_admin_add(self):
        """Test adding a quiz through admin"""
        admin_url = reverse('admin:web_quiz_add')
    
        # Use more complete form data
        quiz_data = {
            "title": "New Admin Quiz",
            "description": "Quiz added through admin",
            "start_date": timezone.now().date().strftime("%Y-%m-%d"),
            "start_time": "10:00:00",
            "end_date": (timezone.now() + timedelta(days=7)).date().strftime("%Y-%m-%d"),
            "end_time": "11:00:00",
            "duration_minutes": 30,
            "_save": "Save",  # Important for admin form handling
        }
    
        response = self.client.post(admin_url, quiz_data)

        with self.captured_queries:
            response = self.client.post(admin_url, quiz_data)
    
        if response.status_code != 302:
            print(f"SQL Queries: {len(self.captured_queries.captured_queries)}")
            for i, query in enumerate(self.captured_queries.captured_queries):
                print(f"Query {i}: {query['sql']}")
    
        # Print response details for debugging
        if response.status_code != 302:
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.content.decode()[:500]}...")
    
        # Check for 302 redirect on success
        self.assertEqual(response.status_code, 302)

    def test_quiz_question_admin_add(self):
        """Test adding a quiz question through Django admin"""
        url = reverse("admin:web_quizquestion_add")

        response = self.client.post(url, {
            "quiz": self.quiz.id,
            "question_text": "What is 2 + 2?",
            "order": 1,
        }, follow=True)  # Follow redirects to capture errors
        print("Status Code:", response.status_code)
        print("Redirected to:", response.get("Location", "No Redirect"))


        if response.status_code in [301, 302]:  # If redirected, print the URL
            print("Redirected to:", response["Location"])
            self.fail("Unexpected redirect occurred instead of showing the form errors")


        if "adminform" in response.context:
            print("Errors:", response.context["adminform"].form.errors)
        else:
            print("No adminform found in response context")
        
        

        self.assertEqual(response.status_code, 200)  # Ensure form is processed
        self.assertTrue(QuizQuestion.objects.filter(question_text="What is 2 + 2?").exists())

    def test_quiz_question_admin_add(self):
        """Test adding a quiz question through Django admin"""
        # Get the form to retrieve necessary fields (like CSRF token)
        response = self.client.get(reverse('admin:web_quizquestion_add'))
        self.assertEqual(response.status_code, 200)

        # Prepare form data
        form_data = {
            'quiz': self.quiz.id,  # Assuming self.quiz is defined in setUp()
            'question_text': 'Test question?',
            'order': 1,
            '_save': 'Save',  # Required to submit the form
            'csrfmiddlewaretoken': response.context['csrf_token'],
        }

        # Submit the form
        response = self.client.post(
            reverse('admin:web_quizquestion_add'), 
            data=form_data,
            follow=True  # Follow redirects
        )

        # Debugging: If failure, print relevant details
        if response.status_code != 200 or not QuizQuestion.objects.filter(question_text='Test question?').exists():
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.content[:500]}")  # Show first 500 chars of response

        # Assert that the quiz question was successfully created
        self.assertTrue(QuizQuestion.objects.filter(question_text='Test question?').exists())


        
