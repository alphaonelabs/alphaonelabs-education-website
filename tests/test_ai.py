from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from ai.models import (
    StudyPlan,
    Subject,
    Topic,
    Achievement,
    UserAchievement,
    GroupDiscussion,
    DiscussionReply,
    LearningStreak,
    UserProgress
)
import json
from datetime import date, timedelta

User = get_user_model()

class AIFeatureTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

        # Create test subject and topic
        self.subject = Subject.objects.create(
            name='Mathematics',
            description='Advanced mathematics topics'
        )
        self.topic = Topic.objects.create(
            subject=self.subject,
            name='Calculus',
            description='Introduction to calculus'
        )

        # Create test achievement
        self.achievement = Achievement.objects.create(
            title='Study Champion',
            description='Complete 10 hours of study',
            type='study_time',
            icon='fa-trophy',
            requirement={'hours': 10},
            points=100
        )

        # Create test study plan
        self.study_plan = StudyPlan.objects.create(
            user=self.user,
            subject=self.subject,
            title='Master Calculus',
            description='Study plan for calculus',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_hours=20
        )

        # Create test discussion
        self.discussion = GroupDiscussion.objects.create(
            user=self.user,
            title='Help with Calculus',
            content='I need help understanding derivatives'
        )

    def test_chat_view(self):
        """Test the chat interface view."""
        response = self.client.get(reverse('ai:chat'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ai/chat.html')

    def test_send_message(self):
        """Test sending a message to the AI assistant."""
        data = {
            'message': 'What is calculus?',
            'subject_id': self.subject.id
        }
        response = self.client.post(
            reverse('ai:send_message'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('response', response.json())

    def test_study_planner(self):
        """Test the study planner functionality."""
        # Test viewing study planner
        response = self.client.get(reverse('ai:study_planner'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ai/study_planner.html')

        # Test creating study plan
        data = {
            'title': 'New Study Plan',
            'description': 'Test plan',
            'subject_id': self.subject.id,
            'start_date': date.today().isoformat(),
            'end_date': (date.today() + timedelta(days=7)).isoformat(),
            'total_hours': 10
        }
        response = self.client.post(
            reverse('ai:create_study_plan'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(StudyPlan.objects.filter(title='New Study Plan').exists())

    def test_progress_tracking(self):
        """Test progress tracking functionality."""
        # Create user progress
        progress = UserProgress.objects.create(
            user=self.user,
            topic=self.topic,
            mastery_level=75
        )

        # Test updating progress
        data = {
            'topic_id': self.topic.id,
            'mastery_level': 85,
            'study_time': 60
        }
        response = self.client.post(
            reverse('ai:update_progress'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        # Test progress dashboard
        response = self.client.get(reverse('ai:progress_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ai/progress_dashboard.html')

    def test_achievements(self):
        """Test achievements functionality."""
        # Test viewing achievements
        response = self.client.get(reverse('ai:achievements'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ai/achievements.html')

        # Test unlocking achievement
        data = {
            'achievement_id': self.achievement.id
        }
        response = self.client.post(
            reverse('ai:unlock_achievement'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            UserAchievement.objects.filter(
                user=self.user,
                achievement=self.achievement
            ).exists()
        )

    def test_group_discussions(self):
        """Test group discussions functionality."""
        # Test viewing discussions
        response = self.client.get(reverse('ai:group_discussions'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ai/group_discussions.html')

        # Test creating discussion
        data = {
            'title': 'New Discussion',
            'content': 'Test content'
        }
        response = self.client.post(
            reverse('ai:create_discussion'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            GroupDiscussion.objects.filter(title='New Discussion').exists()
        )

        # Test creating reply
        data = {
            'content': 'Test reply'
        }
        response = self.client.post(
            reverse('ai:create_discussion_reply', args=[self.discussion.id]),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            DiscussionReply.objects.filter(
                discussion=self.discussion,
                content='Test reply'
            ).exists()
        )

    def test_learning_streak(self):
        """Test learning streak functionality."""
        streak = LearningStreak.objects.create(user=self.user)

        # Test initial streak
        self.assertEqual(streak.current_streak, 0)
        self.assertEqual(streak.longest_streak, 0)

        # Test updating streak
        streak.update_streak()
        self.assertEqual(streak.current_streak, 1)

        # Test consecutive days
        streak.last_activity_date = timezone.now().date() - timedelta(days=1)
        streak.update_streak()
        self.assertEqual(streak.current_streak, 2)
        self.assertEqual(streak.longest_streak, 2)

        # Test broken streak
        streak.last_activity_date = timezone.now().date() - timedelta(days=3)
        streak.update_streak()
        self.assertEqual(streak.current_streak, 1)
        self.assertEqual(streak.longest_streak, 2)

    def test_user_progress(self):
        """Test user progress functionality."""
        progress = UserProgress.objects.create(
            user=self.user,
            topic=self.topic
        )

        # Test initial state
        self.assertEqual(progress.mastery_level, 0)
        self.assertFalse(progress.completed)

        # Test updating mastery level
        progress.update_mastery(85)
        self.assertEqual(progress.mastery_level, 85)
        self.assertTrue(progress.completed)

        # Test mastery level bounds
        progress.update_mastery(120)
        self.assertEqual(progress.mastery_level, 100)
        progress.update_mastery(-10)
        self.assertEqual(progress.mastery_level, 0) 