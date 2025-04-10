from django.db import models
from django.contrib.auth.models import User
from web.models import Course, Session, Enrollment, CourseProgress

class StudentAnalytics(models.Model):
    """Model for tracking detailed student analytics data for AI-powered insights."""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analytics')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='student_analytics')
    
    # Engagement metrics
    total_time_spent = models.DurationField(default=0, help_text="Total time student spent on course materials")
    last_activity_date = models.DateTimeField(null=True, blank=True)
    login_count = models.PositiveIntegerField(default=0)
    material_view_count = models.PositiveIntegerField(default=0)
    
    # Performance metrics
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    assignments_completed = models.PositiveIntegerField(default=0)
    total_assignments = models.PositiveIntegerField(default=0)
    
    # Participation metrics
    forum_posts = models.PositiveIntegerField(default=0)
    questions_asked = models.PositiveIntegerField(default=0)
    
    # Prediction fields (filled by AI)
    predicted_completion = models.DateField(null=True, blank=True)
    risk_level = models.CharField(
        max_length=10, 
        choices=[
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'),
            ('high', 'High Risk')
        ],
        default='low'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'course']
        verbose_name = "Student Analytics"
        verbose_name_plural = "Student Analytics"
    
    def __str__(self):
        return f"{self.student.username}'s analytics for {self.course.title}"
    
    @property
    def completion_percentage(self):
        progress = CourseProgress.objects.filter(
            enrollment__student=self.student,
            enrollment__course=self.course
        ).first()
        
        if progress:
            return progress.completion_percentage
        return 0
    
    @property
    def engagement_score(self):
        """Calculate an engagement score based on various metrics"""
        # Base score from login frequency and material views
        base_score = min(100, (self.login_count + self.material_view_count) / 2)
        
        # Factor in forum participation
        participation_score = min(100, (self.forum_posts + self.questions_asked) * 5)
        
        # Weighted average (60% base activity, 40% participation)
        return (base_score * 0.6) + (participation_score * 0.4)


class LearningPattern(models.Model):
    """Model for capturing student learning patterns over time."""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_patterns')
    date = models.DateField()
    
    # Daily learning patterns
    study_time = models.DurationField(default=0)
    active_hours_start = models.TimeField(null=True, blank=True)
    active_hours_end = models.TimeField(null=True, blank=True)
    materials_accessed = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['student', 'date']
    
    def __str__(self):
        return f"{self.student.username}'s learning pattern on {self.date}"


class PredictiveModel(models.Model):
    """Model for storing AI prediction model metadata."""
    name = models.CharField(max_length=100)
    description = models.TextField()
    version = models.CharField(max_length=20)
    accuracy = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)
    
    # The actual model will be stored as a pickle file
    model_file = models.FileField(upload_to='prediction_models/')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} v{self.version} (Accuracy: {self.accuracy})"