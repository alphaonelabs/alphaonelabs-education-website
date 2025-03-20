from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from web.models import AdminQuiz, AdminQuizQuestion, AdminQuizOption, AdminQuizSubmission

User = get_user_model()


class QuizViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="testuser@example.com", password="testpass123")
        self.start_date = timezone.now().date()
        self.end_date = (timezone.now() + timedelta(days=7)).date()
        
        self.quiz = AdminQuiz.objects.create(
            title="Test Quiz", description="Test quiz description", start_date=self.start_date,
            start_time=timezone.now().time(), end_date=self.end_date, end_time=timezone.now().time(),
            duration_minutes=60,
        )

        self.question = AdminQuizQuestion.objects.create(quiz=self.quiz, question_text="What is the capital of France?")
        self.correct_option = AdminQuizOption.objects.create(question=self.question, option_text="Paris", is_correct=True)
        self.incorrect_option = AdminQuizOption.objects.create(question=self.question, option_text="London", is_correct=False)

    def test_current_live_quiz_redirects_when_not_logged_in(self):
        url = reverse("current_live_quiz", args=[self.quiz.id])
        response = self.client.get(url)
        self.assertRedirects(response, f"/en/accounts/login/?next=/en/quiz/{self.quiz.id}/")

    def test_current_live_quiz_view_already_submitted(self):
        self.client.login(username="testuser", password="testpass123")
        AdminQuizSubmission.objects.create(user=self.user, quiz=self.quiz, score=80)
        response = self.client.get(reverse("current_live_quiz", args=[self.quiz.id]))
        self.assertContains(response, "You have already submitted this quiz.")

    def test_current_live_quiz_view_invalid_quiz_id(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("current_live_quiz", args=[999]))
        self.assertRedirects(response, reverse("index"))

    def test_submit_quiz_without_login_redirects(self):
        response = self.client.post(reverse("submit_quiz", args=[self.quiz.id]), {f"question_{self.question.id}": self.correct_option.id})
        self.assertEqual(response.status_code, 302)

    def test_submit_quiz_with_correct_answer(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(reverse("submit_quiz", args=[self.quiz.id]), {f"question_{self.question.id}": self.correct_option.id})
        self.assertRedirects(response, reverse("leaderboard", args=[self.quiz.id]))
        self.assertEqual(AdminQuizSubmission.objects.get(user=self.user, quiz=self.quiz).score, self.question.points)

    def test_submit_quiz_with_incorrect_answer(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(reverse("submit_quiz", args=[self.quiz.id]), {f"question_{self.question.id}": self.incorrect_option.id})
        self.assertRedirects(response, reverse("leaderboard", args=[self.quiz.id]))
        self.assertEqual(AdminQuizSubmission.objects.get(user=self.user, quiz=self.quiz).score, 0)

    def test_submit_quiz_twice_score_remains_same(self):
        self.client.login(username="testuser", password="testpass123")
        AdminQuizSubmission.objects.create(user=self.user, quiz=self.quiz, score=80)
        response = self.client.post(reverse("submit_quiz", args=[self.quiz.id]), {f"question_{self.question.id}": self.correct_option.id})
        self.assertRedirects(response, reverse("leaderboard", args=[self.quiz.id]))
        self.assertEqual(AdminQuizSubmission.objects.get(user=self.user, quiz=self.quiz).score, 80)

    def test_submit_quiz_with_missing_answer(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(reverse("submit_quiz", args=[self.quiz.id]), {})
        self.assertRedirects(response, reverse("leaderboard", args=[self.quiz.id]))
        self.assertEqual(AdminQuizSubmission.objects.get(user=self.user, quiz=self.quiz).score, 0)

    def test_leaderboard_view(self):
        user1, user2, user3 = [User.objects.create_user(username=f"user{i}", email=f"user{i}@example.com", password="pass123") for i in range(1, 4)]
        scores = {user1: 90, user2: 80, user3: 100}
        [AdminQuizSubmission.objects.create(user=user, quiz=self.quiz, score=score) for user, score in scores.items()]
        self.client.login(username="user1", password="pass123")
        response = self.client.get(reverse("leaderboard", args=[self.quiz.id]))
        self.assertContains(response, "Test Quiz")
        sorted_scores = [sub.score for sub in response.context["submissions"]]
        self.assertEqual(sorted_scores, [100, 90, 80])

    def test_leaderboard_quiz_ended_flag(self):
        past_quiz = AdminQuiz.objects.create(
            title="Past Quiz", description="Quiz that already ended",
            start_date=(timezone.now() - timedelta(days=14)).date(),
            start_time=timezone.now().time(),
            end_date=(timezone.now() - timedelta(days=7)).date(),
            end_time=timezone.now().time(), duration_minutes=60,
        )
        self.client.login(username="testuser", password="testpass123")
        self.assertTrue(self.client.get(reverse("leaderboard", args=[past_quiz.id])).context["quiz_ended"])
        self.assertFalse(self.client.get(reverse("leaderboard", args=[self.quiz.id])).context["quiz_ended"])
