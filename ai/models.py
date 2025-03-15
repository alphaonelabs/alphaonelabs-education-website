from django.db import models
from django.conf import settings
from django.utils import timezone

class Interaction(models.Model):
    """Record of student interactions with the AI assistant."""
    AI_PROVIDERS = (
        ('gemini', 'Google Gemini'),
        ('gpt', 'OpenAI GPT'),
        ('claude', 'Anthropic Claude'),
        ('demo', 'Demo Mode'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_interactions')
    question = models.TextField()
    answer = models.TextField(blank=True)
    subject = models.CharField(max_length=100, default='general')
    topic = models.CharField(max_length=255, blank=True)
    ai_provider = models.CharField(max_length=50, choices=AI_PROVIDERS, default='demo')
    created_at = models.DateTimeField(auto_now_add=True)
    feedback_rating = models.IntegerField(null=True, blank=True)
    feedback_comment = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Q: {self.question[:50]}... by {self.user.username}"

class ProgressRecord(models.Model):
    """Tracks student progress in specific subjects and topics."""
    MASTERY_LEVELS = (
        (1, 'Novice'),
        (2, 'Beginner'),
        (3, 'Intermediate'),
        (4, 'Advanced'),
        (5, 'Expert'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='progress_records')
    subject = models.CharField(max_length=100)
    topic = models.CharField(max_length=255)
    mastery_level = models.IntegerField(choices=MASTERY_LEVELS, default=1)
    confidence_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'subject', 'topic')
        ordering = ['subject', 'topic']
        
    def __str__(self):
        return f"{self.user.username} - {self.subject} - {self.topic} ({self.get_mastery_level_display()})"

class StudentProfile(models.Model):
    """Extended AI learning preferences for students."""
    LEARNING_STYLES = (
        ('visual', 'Visual'),
        ('auditory', 'Auditory'),
        ('reading', 'Reading/Writing'),
        ('kinesthetic', 'Kinesthetic'),
    )
    
    DIFFICULTY_PREFERENCES = (
        ('easy', 'Easy'),
        ('moderate', 'Moderate'),
        ('challenging', 'Challenging'),
        ('adaptive', 'Adaptive'),
    )
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_profile')
    learning_style = models.CharField(max_length=20, choices=LEARNING_STYLES, default='visual')
    difficulty_preference = models.CharField(max_length=20, choices=DIFFICULTY_PREFERENCES, default='moderate')
    response_length = models.CharField(
        max_length=20, 
        choices=[('concise', 'Concise'), ('detailed', 'Detailed'), ('comprehensive', 'Comprehensive')],
        default='detailed'
    )
    include_examples = models.BooleanField(default=True)
    include_visuals = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Learning Profile"

class StudyPlan(models.Model):
    """AI-generated study plans for students."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='study_plans')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=100)
    content = models.TextField()
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
