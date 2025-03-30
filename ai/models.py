from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone

User = get_user_model()

class Interaction(models.Model):
    """Model for storing AI chat interactions."""
    FEEDBACK_CHOICES = [
        (1, 'Not Helpful'),
        (2, 'Slightly Helpful'),
        (3, 'Neutral'),
        (4, 'Helpful'),
        (5, 'Very Helpful'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_interactions')
    question = models.TextField()
    answer = models.TextField(blank=True)
    subject = models.CharField(max_length=50, default='general')
    topic = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    feedback = models.IntegerField(choices=FEEDBACK_CHOICES, null=True, blank=True)
    ai_provider = models.CharField(max_length=20, default='demo')
    
    # Learning style data
    visual_elements = models.BooleanField(default=False)
    audio_elements = models.BooleanField(default=False)
    text_elements = models.BooleanField(default=True)
    interactive_elements = models.BooleanField(default=False)
    
    # Performance metrics
    time_spent = models.IntegerField(default=0)  # Time spent in seconds
    comprehension_score = models.FloatField(null=True, blank=True)  # 0-1 score
    difficulty_level = models.CharField(max_length=20, choices=[
        ('easy', 'Easy'),
        ('moderate', 'Moderate'),
        ('challenging', 'Challenging'),
    ], default='moderate')
    
    # Learning path data
    is_prerequisite = models.BooleanField(default=False)
    prerequisite_topics = models.ManyToManyField('self', symmetrical=False, blank=True)
    next_topics = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='previous_topics')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.subject} - {self.created_at}"
    
    def update_learning_path(self):
        """Update learning path based on interaction data."""
        # Get user's profile
        profile = self.user.ai_student_profile
        
        # Update difficulty level based on comprehension
        if self.comprehension_score is not None:
            if self.comprehension_score < 0.5:
                self.difficulty_level = 'challenging'
            elif self.comprehension_score > 0.8:
                self.difficulty_level = 'easy'
            else:
                self.difficulty_level = 'moderate'
        
        # Update learning style elements based on profile
        if profile.learning_style == 'visual':
            self.visual_elements = True
        elif profile.learning_style == 'auditory':
            self.audio_elements = True
        elif profile.learning_style == 'reading':
            self.text_elements = True
        elif profile.learning_style == 'kinesthetic':
            self.interactive_elements = True
        else:  # mixed
            self.visual_elements = True
            self.text_elements = True
        
        self.save()

class ProgressRecord(models.Model):
    """Model for tracking student progress in subjects and topics."""
    MASTERY_LEVELS = [
        (1, 'Beginner'),
        (2, 'Novice'),
        (3, 'Intermediate'),
        (4, 'Advanced'),
        (5, 'Expert'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_progress_records')
    subject = models.CharField(max_length=50)
    topic = models.CharField(max_length=100)
    score = models.FloatField(default=0.0)
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Detailed progress metrics
    mastery_level = models.IntegerField(choices=MASTERY_LEVELS, default=1)
    confidence_score = models.FloatField(default=0.0)  # 0-1 score
    time_spent = models.IntegerField(default=0)  # Time spent in seconds
    attempts = models.IntegerField(default=0)
    successful_attempts = models.IntegerField(default=0)
    last_activity = models.DateTimeField(auto_now=True)
    
    # Learning style effectiveness
    visual_effectiveness = models.FloatField(default=0.0)
    auditory_effectiveness = models.FloatField(default=0.0)
    reading_effectiveness = models.FloatField(default=0.0)
    kinesthetic_effectiveness = models.FloatField(default=0.0)
    
    # Performance analytics
    average_response_time = models.FloatField(default=0.0)
    error_rate = models.FloatField(default=0.0)
    improvement_rate = models.FloatField(default=0.0)
    
    class Meta:
        unique_together = ['user', 'subject', 'topic']
    
    def __str__(self):
        return f"{self.user.username}'s progress in {self.topic}"
    
    def update_progress(self, interaction_data):
        """Update progress based on interaction data."""
        # Update basic metrics
        self.score = (self.score * self.attempts + interaction_data.get('score', 0)) / (self.attempts + 1)
        self.attempts += 1
        self.time_spent += interaction_data.get('time_spent', 0)
        
        # Update mastery level
        if self.score >= 0.9:
            self.mastery_level = 5
        elif self.score >= 0.7:
            self.mastery_level = 4
        elif self.score >= 0.5:
            self.mastery_level = 3
        elif self.score >= 0.3:
            self.mastery_level = 2
        else:
            self.mastery_level = 1
        
        # Update confidence score
        self.confidence_score = min(1.0, self.confidence_score + (interaction_data.get('confidence_gain', 0.1)))
        
        # Update learning style effectiveness
        if interaction_data.get('visual_elements'):
            self.visual_effectiveness = (self.visual_effectiveness * self.attempts + interaction_data.get('visual_score', 0)) / (self.attempts + 1)
        if interaction_data.get('audio_elements'):
            self.auditory_effectiveness = (self.auditory_effectiveness * self.attempts + interaction_data.get('audio_score', 0)) / (self.attempts + 1)
        if interaction_data.get('text_elements'):
            self.reading_effectiveness = (self.reading_effectiveness * self.attempts + interaction_data.get('text_score', 0)) / (self.attempts + 1)
        if interaction_data.get('interactive_elements'):
            self.kinesthetic_effectiveness = (self.kinesthetic_effectiveness * self.attempts + interaction_data.get('interactive_score', 0)) / (self.attempts + 1)
        
        # Update performance analytics
        self.average_response_time = (self.average_response_time * self.attempts + interaction_data.get('response_time', 0)) / (self.attempts + 1)
        self.error_rate = (self.error_rate * self.attempts + interaction_data.get('error_rate', 0)) / (self.attempts + 1)
        self.improvement_rate = (self.score - self.score) / max(1, self.attempts)
        
        self.save()

class StudentProfile(models.Model):
    """Model for storing extended student learning preferences."""
    LEARNING_STYLES = [
        ('visual', 'Visual'),
        ('auditory', 'Auditory'),
        ('reading', 'Reading/Writing'),
        ('kinesthetic', 'Kinesthetic'),
        ('mixed', 'Mixed'),
    ]
    
    DIFFICULTY_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('adaptive', 'Adaptive'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ai_student_profile')
    learning_style = models.CharField(max_length=20, choices=LEARNING_STYLES, default='mixed')
    difficulty_preference = models.CharField(max_length=20, choices=DIFFICULTY_LEVELS, default='intermediate')
    subjects_of_interest = models.TextField(default='')
    preferred_response_format = models.CharField(max_length=20, choices=[
        ('text', 'Text'),
        ('visual', 'Visual'),
        ('interactive', 'Interactive'),
        ('mixed', 'Mixed'),
    ], default='mixed')
    preferred_response_length = models.CharField(max_length=20, choices=[
        ('concise', 'Concise'),
        ('detailed', 'Detailed'),
        ('comprehensive', 'Comprehensive'),
    ], default='detailed')
    preferred_explanation_style = models.CharField(max_length=20, choices=[
        ('practical', 'Practical Examples'),
        ('theoretical', 'Theoretical Concepts'),
        ('step-by-step', 'Step-by-Step'),
        ('comparative', 'Comparative Analysis'),
    ], default='practical')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"
    
    def update_learning_style(self, interaction_data):
        """Update learning style based on interaction data."""
        # Analyze interaction patterns
        visual_count = 0
        auditory_count = 0
        reading_count = 0
        kinesthetic_count = 0
        
        # Count different types of interactions
        for interaction in interaction_data:
            if interaction.get('visual_elements'):
                visual_count += 1
            if interaction.get('audio_elements'):
                auditory_count += 1
            if interaction.get('text_elements'):
                reading_count += 1
            if interaction.get('interactive_elements'):
                kinesthetic_count += 1
        
        # Determine dominant learning style
        max_count = max(visual_count, auditory_count, reading_count, kinesthetic_count)
        if max_count == 0:
            return
        
        if max_count == visual_count:
            self.learning_style = 'visual'
        elif max_count == auditory_count:
            self.learning_style = 'auditory'
        elif max_count == reading_count:
            self.learning_style = 'reading'
        elif max_count == kinesthetic_count:
            self.learning_style = 'kinesthetic'
        else:
            self.learning_style = 'mixed'
        
        self.save()

def get_default_end_date():
    return timezone.now() + timezone.timedelta(days=30)

class StudyPlan(models.Model):
    """Model for user study plans."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_study_plans')
    title = models.CharField(max_length=200)
    description = models.TextField()
    subject = models.CharField(max_length=100)
    total_hours = models.IntegerField(default=0)
    completed_hours = models.IntegerField(default=0)  # Track completed study hours
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(default=get_default_end_date)
    progress = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    @property
    def progress_percentage(self):
        """Calculate the progress percentage."""
        if self.total_hours == 0:
            return 0
        return (self.completed_hours / self.total_hours) * 100

class Subject(models.Model):
    """Model for study subjects."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Topic(models.Model):
    """Model for study topics within subjects."""
    subject = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(max_length=20)
    prerequisites = models.ManyToManyField('self', symmetrical=False, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.subject})"

class ChatSession(models.Model):
    """Model for storing chat sessions."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_chat_sessions')
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Chat session for {self.user.username}"

class Message(models.Model):
    """Model for storing chat messages."""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    is_user = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{'User' if self.is_user else 'AI'} message in {self.session}"

class Achievement(models.Model):
    """Model for user achievements."""
    ACHIEVEMENT_TYPES = [
        ('study_time', 'Study Time'),
        ('topics_completed', 'Topics Completed'),
        ('streak', 'Learning Streak'),
        ('discussion', 'Discussion Participation'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    type = models.CharField(max_length=20, choices=ACHIEVEMENT_TYPES)
    icon = models.CharField(max_length=50)  # FontAwesome icon class
    requirement = models.JSONField()  # Stores achievement requirements
    points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UserAchievement(models.Model):
    """Model for tracking user's unlocked achievements."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_user_achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'achievement']

    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"

class StudyGroup(models.Model):
    """Model for study groups."""
    name = models.CharField(max_length=200)
    description = models.TextField()
    subject = models.CharField(max_length=100)
    members = models.ManyToManyField(User, related_name='ai_study_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class GroupDiscussion(models.Model):
    """Model for group discussions."""
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='discussions')
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_group_discussions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(User, related_name='liked_discussions', blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.author.username}"

    @property
    def likes_count(self):
        """Get the number of likes."""
        return self.likes.count()

class DiscussionReply(models.Model):
    """Model for replies to group discussions."""
    discussion = models.ForeignKey(GroupDiscussion, on_delete=models.CASCADE, related_name='replies')
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_discussion_replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(User, related_name='liked_replies', blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Reply by {self.author.username} on {self.discussion.title}"

    @property
    def likes_count(self):
        """Get the number of likes."""
        return self.likes.count()

class LearningStreak(models.Model):
    """Model for tracking user's learning streaks."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_learning_streaks')
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Learning Streak"

    def update_streak(self):
        """Update the learning streak based on activity."""
        today = timezone.now().date()
        
        if not self.last_activity:
            self.current_streak = 1
        else:
            days_difference = (today - self.last_activity.date()).days
            
            if days_difference == 1:  # Consecutive day
                self.current_streak += 1
            elif days_difference == 0:  # Same day
                pass
            else:  # Streak broken
                self.current_streak = 1

        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak

        self.last_activity = today
        self.save()

class UserProgress(models.Model):
    """Model for tracking user's learning progress."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_user_progress')
    subject = models.CharField(max_length=100)
    progress = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s progress in {self.subject}"

    def update_progress(self, new_progress):
        """Update progress based on new assessment score."""
        self.progress = min(100, max(0, new_progress))
        self.save()

class LearningPath(models.Model):
    """Model for personalized learning paths."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_learning_paths')
    title = models.CharField(max_length=200)
    description = models.TextField()
    subject = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start_date = models.DateField()
    target_completion_date = models.DateField()
    actual_completion_date = models.DateField(null=True, blank=True)
    
    # Progress tracking
    total_topics = models.IntegerField(default=0)
    completed_topics = models.IntegerField(default=0)
    current_topic = models.ForeignKey('Topic', on_delete=models.SET_NULL, null=True, blank=True)
    progress_percentage = models.FloatField(default=0.0)
    
    # Learning style adaptation
    preferred_learning_style = models.CharField(max_length=20, choices=StudentProfile.LEARNING_STYLES)
    difficulty_level = models.CharField(max_length=20, choices=StudentProfile.DIFFICULTY_LEVELS)
    
    # Performance metrics
    average_score = models.FloatField(default=0.0)
    time_spent = models.IntegerField(default=0)  # Time spent in seconds
    completion_rate = models.FloatField(default=0.0)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}'s {self.subject} learning path"
    
    def update_progress(self):
        """Update learning path progress."""
        if self.total_topics > 0:
            self.progress_percentage = (self.completed_topics / self.total_topics) * 100
            
            # Calculate completion rate
            if self.time_spent > 0:
                self.completion_rate = self.completed_topics / (self.time_spent / 3600)  # topics per hour
            
            # Check if path is completed
            if self.progress_percentage >= 100:
                self.status = 'completed'
                self.actual_completion_date = timezone.now().date()
        
        self.save()
    
    def get_next_topic(self):
        """Get the next recommended topic based on learning style and progress."""
        from django.db.models import Q
        
        # Get topics that are prerequisites for current topic
        if self.current_topic:
            next_topics = self.current_topic.next_topics.all()
        else:
            # If no current topic, get topics with no prerequisites
            next_topics = Topic.objects.filter(
                subject=self.subject,
                prerequisite_topics__isnull=True
            )
        
        # Filter topics based on difficulty level
        next_topics = next_topics.filter(difficulty=self.difficulty_level)
        
        # Sort topics by effectiveness for user's learning style
        if self.preferred_learning_style == 'visual':
            next_topics = next_topics.order_by('-visual_effectiveness')
        elif self.preferred_learning_style == 'auditory':
            next_topics = next_topics.order_by('-auditory_effectiveness')
        elif self.preferred_learning_style == 'reading':
            next_topics = next_topics.order_by('-reading_effectiveness')
        elif self.preferred_learning_style == 'kinesthetic':
            next_topics = next_topics.order_by('-interactive_effectiveness')
        
        return next_topics.first()
    
    def add_topic(self, topic):
        """Add a topic to the learning path."""
        self.total_topics += 1
        self.save()
    
    def complete_topic(self, topic):
        """Mark a topic as completed and update progress."""
        self.completed_topics += 1
        self.current_topic = self.get_next_topic()
        self.update_progress()

class Feedback(models.Model):
    """Model for storing feedback on student responses."""
    FEEDBACK_TYPES = [
        ('correct', 'Correct'),
        ('partially_correct', 'Partially Correct'),
        ('incorrect', 'Incorrect'),
        ('hint', 'Hint'),
        ('explanation', 'Explanation')
    ]
    
    interaction = models.ForeignKey(
        Interaction,
        on_delete=models.CASCADE,
        related_name='feedback_responses'
    )
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Feedback effectiveness metrics
    helpful = models.BooleanField(default=False)
    clarity_score = models.FloatField(default=0.0)
    relevance_score = models.FloatField(default=0.0)
    
    # Learning style adaptation
    visual_elements = models.BooleanField(default=False)
    audio_elements = models.BooleanField(default=False)
    text_elements = models.BooleanField(default=False)
    interactive_elements = models.BooleanField(default=False)
    
    # Performance impact
    improvement_observed = models.BooleanField(default=False)
    time_to_improvement = models.DurationField(null=True, blank=True)
    
    def __str__(self):
        return f"Feedback for {self.interaction} - {self.feedback_type}"
    
    def update_effectiveness(self, student_response):
        """Update feedback effectiveness based on student's response."""
        # Calculate clarity score based on student's understanding
        self.clarity_score = student_response.get('clarity_score', 0.0)
        
        # Calculate relevance score based on improvement
        self.relevance_score = student_response.get('relevance_score', 0.0)
        
        # Check if improvement was observed
        self.improvement_observed = student_response.get('improvement_observed', False)
        
        # Update time to improvement if applicable
        if self.improvement_observed:
            self.time_to_improvement = student_response.get('time_to_improvement')
        
        self.save()
    
    def adapt_to_learning_style(self, learning_style):
        """Adapt feedback content based on student's learning style."""
        if learning_style == 'visual':
            self.visual_elements = True
            self.content = f"[Visual] {self.content}"
        elif learning_style == 'auditory':
            self.audio_elements = True
            self.content = f"[Audio] {self.content}"
        elif learning_style == 'reading':
            self.text_elements = True
            self.content = f"[Text] {self.content}"
        elif learning_style == 'kinesthetic':
            self.interactive_elements = True
            self.content = f"[Interactive] {self.content}"
        
        self.save()

class Dashboard(models.Model):
    """Model for student progress dashboard."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ai_dashboard')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Overall progress
    total_study_time = models.IntegerField(default=0)  # Time spent in seconds
    total_topics_completed = models.IntegerField(default=0)
    average_score = models.FloatField(default=0.0)
    completion_rate = models.FloatField(default=0.0)
    
    # Learning style effectiveness
    visual_effectiveness = models.FloatField(default=0.0)
    auditory_effectiveness = models.FloatField(default=0.0)
    reading_effectiveness = models.FloatField(default=0.0)
    kinesthetic_effectiveness = models.FloatField(default=0.0)
    
    # Performance metrics
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity = models.DateTimeField(null=True, blank=True)
    average_response_time = models.FloatField(default=0.0)
    error_rate = models.FloatField(default=0.0)
    
    # Achievement tracking
    achievements_unlocked = models.IntegerField(default=0)
    total_achievements = models.IntegerField(default=0)
    recent_achievements = models.ManyToManyField('Achievement', related_name='recent_dashboards')
    
    # Learning paths
    active_paths = models.IntegerField(default=0)
    completed_paths = models.IntegerField(default=0)
    current_path = models.ForeignKey('LearningPath', on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s dashboard"
    
    def update_metrics(self):
        """Update dashboard metrics based on user activity."""
        # Update overall progress
        self.total_study_time = sum(record.time_spent for record in self.user.ai_progress_records.all())
        self.total_topics_completed = self.user.ai_progress_records.filter(score__gte=0.8).count()
        
        # Calculate average score
        scores = [record.score for record in self.user.ai_progress_records.all()]
        self.average_score = sum(scores) / len(scores) if scores else 0.0
        
        # Calculate completion rate
        total_topics = sum(path.total_topics for path in self.user.ai_learning_paths.all())
        completed_topics = sum(path.completed_topics for path in self.user.ai_learning_paths.all())
        self.completion_rate = (completed_topics / total_topics * 100) if total_topics > 0 else 0.0
        
        # Update learning style effectiveness
        records = self.user.ai_progress_records.all()
        self.visual_effectiveness = sum(record.visual_effectiveness for record in records) / len(records) if records else 0.0
        self.auditory_effectiveness = sum(record.auditory_effectiveness for record in records) / len(records) if records else 0.0
        self.reading_effectiveness = sum(record.reading_effectiveness for record in records) / len(records) if records else 0.0
        self.kinesthetic_effectiveness = sum(record.kinesthetic_effectiveness for record in records) / len(records) if records else 0.0
        
        # Update performance metrics
        self.average_response_time = sum(record.average_response_time for record in records) / len(records) if records else 0.0
        self.error_rate = sum(record.error_rate for record in records) / len(records) if records else 0.0
        
        # Update learning paths
        self.active_paths = self.user.ai_learning_paths.filter(status='active').count()
        self.completed_paths = self.user.ai_learning_paths.filter(status='completed').count()
        self.current_path = self.user.ai_learning_paths.filter(status='active').first()
        
        # Update achievements
        self.achievements_unlocked = self.user.ai_user_achievements.count()
        self.total_achievements = Achievement.objects.count()
        self.recent_achievements.set(
            self.user.ai_user_achievements.order_by('-earned_at')[:5].values_list('achievement', flat=True)
        )
        
        self.save()
    
    def get_recommendations(self):
        """Get personalized learning recommendations."""
        recommendations = []
        
        # Get weak areas
        weak_areas = self.user.ai_progress_records.filter(
            score__lt=0.6
        ).order_by('score')[:3]
        
        for area in weak_areas:
            recommendations.append({
                'type': 'weak_area',
                'subject': area.subject,
                'topic': area.topic,
                'score': area.score,
                'suggestion': f"Review {area.topic} in {area.subject} to improve your understanding"
            })
        
        # Get next topics
        if self.current_path:
            next_topic = self.current_path.get_next_topic()
            if next_topic:
                recommendations.append({
                    'type': 'next_topic',
                    'subject': next_topic.subject,
                    'topic': next_topic.name,
                    'suggestion': f"Continue with {next_topic.name} in your learning path"
                })
        
        # Get achievement suggestions
        recent_achievements = self.recent_achievements.all()
        if recent_achievements:
            last_achievement = recent_achievements[0]
            recommendations.append({
                'type': 'achievement',
                'achievement': last_achievement.name,
                'suggestion': f"Keep up the good work! You're making great progress"
            })
        
        return recommendations
    
    def get_progress_summary(self):
        """Get a summary of the user's learning progress."""
        return {
            'total_study_time': self.total_study_time,
            'total_topics_completed': self.total_topics_completed,
            'average_score': self.average_score,
            'completion_rate': self.completion_rate,
            'current_streak': self.current_streak,
            'longest_streak': self.longest_streak,
            'achievements_unlocked': self.achievements_unlocked,
            'total_achievements': self.total_achievements,
            'active_paths': self.active_paths,
            'completed_paths': self.completed_paths,
            'learning_style_effectiveness': {
                'visual': self.visual_effectiveness,
                'auditory': self.auditory_effectiveness,
                'reading': self.reading_effectiveness,
                'kinesthetic': self.kinesthetic_effectiveness
            }
        }

class StudyTask(models.Model):
    """Model for study tasks within a study plan."""
    study_plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField()
    estimated_hours = models.FloatField(default=1.0)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.title} ({self.study_plan.title})"
    
    def save(self, *args, **kwargs):
        # If the task is being completed or uncompleted, update the study plan's completed hours
        if self.pk:  # Only for existing tasks
            old_task = StudyTask.objects.get(pk=self.pk)
            if old_task.completed != self.completed:
                if self.completed:
                    self.study_plan.completed_hours += self.estimated_hours
                else:
                    self.study_plan.completed_hours -= self.estimated_hours
                
                # Update study plan progress
                self.study_plan.progress = round((self.study_plan.completed_hours / self.study_plan.total_hours * 100), 2) if self.study_plan.total_hours > 0 else 0
                self.study_plan.save()
        
        super().save(*args, **kwargs)
