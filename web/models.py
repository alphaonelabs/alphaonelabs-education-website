import os
import random
import string
import time
import uuid
from io import BytesIO

from allauth.account.signals import user_signed_up
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from markdownx.models import MarkdownxField
from PIL import Image


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("info", "Information"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("error", "Error"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES, default="info")
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.user.username}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    expertise = models.CharField(max_length=200, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, default="")
    is_teacher = models.BooleanField(default=False)
    referral_code = models.CharField(max_length=20, unique=True, blank=True)
    referred_by = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals")
    referral_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stripe_account_id = models.CharField(max_length=100, blank=True)
    stripe_account_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("verified", "Verified"),
            ("rejected", "Rejected"),
        ],
        default="pending",
        blank=True,
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text="Commission rate in percentage (e.g., 10.00 for 10%)",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        if self.avatar:
            img = Image.open(self.avatar)
            if img.mode != "RGB":
                img = img.convert("RGB")
            # Resize to a square avatar
            size = (200, 200)
            img = img.resize(size, Image.Resampling.LANCZOS)
            # Save the resized image
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=90)
            # Update the ImageField
            file_name = self.avatar.name
            self.avatar.delete(save=False)  # Delete old image
            self.avatar.save(file_name, ContentFile(buffer.getvalue()), save=False)
        super().save(*args, **kwargs)

    def generate_referral_code(self):
        """Generate a unique referral code."""
        max_attempts = 10
        attempt = 0

        while attempt < max_attempts:
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Profile.objects.filter(referral_code=code).exists():
                return code
            attempt += 1

        # If we've exhausted our attempts, generate a truly unique code using timestamp
        timestamp = int(time.time())
        code = f"{timestamp:x}".upper()[:8]
        return code

    @property
    def total_referrals(self):
        """Return the total number of successful referrals."""
        return self.referrals.count()

    def add_referral_earnings(self, amount):
        """Add referral earnings to the user's balance."""
        self.referral_earnings = self.referral_earnings + amount
        self.save()

    @property
    def can_receive_payments(self):
        return self.is_teacher and self.stripe_account_id and self.stripe_account_status == "verified"


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, help_text="Font Awesome icon class", blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class WebRequest(models.Model):
    ip_address = models.CharField(max_length=100, blank=True, default="")
    user = models.CharField(max_length=150, blank=True, default="")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    agent = models.TextField(blank=True, default="")
    count = models.BigIntegerField(default=1)
    path = models.CharField(max_length=255, blank=True, default="")
    referer = models.CharField(max_length=255, blank=True, default="")
    course = models.ForeignKey("Course", on_delete=models.CASCADE, related_name="web_requests", null=True, blank=True)

    def __str__(self):
        return f"{self.path} - {self.count} views"


class Course(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    image = models.ImageField(
        upload_to="course_images", help_text="Course image (will be resized to 300x300 pixels)", blank=True
    )
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="courses_teaching")
    description = MarkdownxField()
    learning_objectives = MarkdownxField()
    prerequisites = MarkdownxField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    allow_individual_sessions = models.BooleanField(
        default=False, help_text="Allow students to register for individual sessions"
    )
    invite_only = models.BooleanField(
        default=False, help_text="If enabled, students can only enroll with an invitation"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    max_students = models.IntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="courses",
    )

    level = models.CharField(
        max_length=20,
        choices=[
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ],
        default="beginner",
    )
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    is_featured = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Course.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # Handle image resizing
        if self.image:
            img = Image.open(self.image)
            # Convert to RGB if necessary
            if img.mode != "RGB":
                img = img.convert("RGB")
            # Crop image to a square format
            width, height = img.size
            min_dim = min(width, height)
            left = (width - min_dim) / 2
            top = (height - min_dim) / 2
            right = (width + min_dim) / 2
            bottom = (height + min_dim) / 2
            img = img.crop((left, top, right, bottom))
            # Resize the image to 300x300 pixels
            img = img.resize((500, 500), Image.Resampling.LANCZOS)
            # Save the resized image
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=90)
            # Update the ImageField
            file_name = self.image.name
            self.image.delete(save=False)  # Delete old image
            self.image.save(file_name, ContentFile(buffer.getvalue()), save=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def available_spots(self):
        return self.max_students - self.enrollments.count()

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return 0
        return sum(review.rating for review in reviews) / len(reviews)


class Session(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sessions")
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_virtual = models.BooleanField(default=True)
    meeting_link = models.URLField(blank=True)
    meeting_id = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Price for individual session registration"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Rollover fields
    enable_rollover = models.BooleanField(
        default=False, help_text="Enable automatic date rollover if no students are enrolled"
    )
    rollover_pattern = models.CharField(
        max_length=20,
        choices=[
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
        ],
        default="weekly",
        blank=True,
        help_text="How often to roll over the session dates",
    )
    original_start_time = models.DateTimeField(
        null=True, blank=True, help_text="Original start time before any rollovers"
    )
    original_end_time = models.DateTimeField(null=True, blank=True, help_text="Original end time before any rollovers")
    is_rolled_over = models.BooleanField(default=False, help_text="Whether this session has been rolled over")
    teacher_confirmed = models.BooleanField(
        default=False, help_text="Whether the teacher has confirmed the rolled over dates"
    )

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    def save(self, *args, **kwargs):
        # Store original times when first created
        if not self.pk and not self.original_start_time and not self.original_end_time:
            self.original_start_time = self.start_time
            self.original_end_time = self.end_time

        # Handle virtual meeting creation/updates
        is_new = self._state.adding
        old_instance = None if is_new else Session.objects.get(pk=self.pk)

        # First save to get the ID
        super().save(*args, **kwargs)

        if self.is_virtual:
            from .calendar_sync import create_calendar_event, update_calendar_event

            if is_new:
                event_id = create_calendar_event(self)
                if event_id:
                    self.meeting_id = event_id
                    # Update without triggering save() again
                    Session.objects.filter(pk=self.pk).update(meeting_id=event_id)
            elif old_instance and (
                old_instance.start_time != self.start_time
                or old_instance.end_time != self.end_time
                or old_instance.title != self.title
            ):
                update_calendar_event(self)

    def roll_forward(self):
        """Roll the session forward based on the rollover pattern."""
        if not self.enable_rollover or self.teacher_confirmed:
            return False

        now = timezone.now()
        if self.start_time > now:
            return False  # Don't roll forward future sessions

        # Calculate new dates based on pattern
        if self.rollover_pattern == "daily":
            days_to_add = 1
        elif self.rollover_pattern == "weekly":
            days_to_add = 7
        else:  # monthly
            days_to_add = 30

        # Calculate time difference between start and end
        duration = self.end_time - self.start_time

        # Roll forward until we get a future date
        while self.start_time <= now:
            self.start_time += timezone.timedelta(days=days_to_add)
            self.end_time = self.start_time + duration

        self.is_rolled_over = True
        self.teacher_confirmed = False
        return True

    def delete(self, *args, **kwargs):
        # Delete associated calendar event if exists
        if self.is_virtual and self.meeting_id:
            from .calendar_sync import delete_calendar_event

            delete_calendar_event(self)
        super().delete(*args, **kwargs)


class CourseMaterial(models.Model):
    MATERIAL_TYPES = [
        ("video", "Video"),
        ("image", "Image"),
        ("document", "Document"),
        ("presentation", "Presentation"),
        ("exercise", "Exercise"),
        ("quiz", "Quiz"),
        ("assignment", "Assignment"),  # Add 'assignment' as a valid choice
        ("other", "Other"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="materials")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPES)
    file = models.FileField(upload_to="course_materials/", blank=True)
    external_url = models.URLField(blank=True, help_text="URL for external content like YouTube videos")
    session = models.ForeignKey(
        Session,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materials",
    )
    order = models.PositiveIntegerField(default=0)
    is_downloadable = models.BooleanField(default=True)
    requires_enrollment = models.BooleanField(
        default=True, help_text="If True, only enrolled students can access full content"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    def clean(self):
        if not self.file and not self.external_url:
            raise ValidationError("Either a file or external URL must be provided")
        if self.file and self.external_url:
            raise ValidationError("Cannot have both file and external URL")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def file_extension(self):
        if self.file:
            return os.path.splitext(self.file.name)[1].lower()
        return ""

    @property
    def file_size(self):
        if not self.file:
            return 0
        try:
            return self.file.size
        except FileNotFoundError:
            return 0

    @property
    def preview_content(self):
        """Returns limited content for non-enrolled users"""
        if self.material_type == "video":
            return self.title
        elif self.material_type == "image":
            return self.title
        return self.title


class Enrollment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    enrollment_date = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    payment_intent_id = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        unique_together = ["student", "course"]

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"


class SessionAttendance(models.Model):
    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("excused", "Excused"),
        ("late", "Late"),
    ]

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="attendances")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="session_attendances")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="absent")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["session", "student"]

    def __str__(self):
        return f"{self.student.username} - {self.session.title} ({self.status})"


class CourseProgress(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name="progress")
    completed_sessions = models.ManyToManyField(Session, related_name="completed_by")
    last_accessed = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    @property
    def completion_percentage(self):
        total_sessions = self.enrollment.course.sessions.count()
        if total_sessions == 0:
            return 0
        completed = self.completed_sessions.count()
        return int((completed / total_sessions) * 100)

    @property
    def attendance_rate(self):
        total_past_sessions = self.enrollment.course.sessions.filter(start_time__lt=timezone.now()).count()
        if total_past_sessions == 0:
            return 100
        attended = SessionAttendance.objects.filter(
            student=self.enrollment.student,
            session__course=self.enrollment.course,
            status__in=["present", "late"],
        ).count()
        return int((attended / total_past_sessions) * 100)

    def __str__(self):
        return f"{self.enrollment.student.username}'s progress in {self.enrollment.course.title}"


class Achievement(models.Model):
    TYPES = [
        ("attendance", "Perfect Attendance"),
        ("completion", "Course Completion"),
        ("participation", "Active Participation"),
        ("excellence", "Academic Excellence"),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="achievements")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="achievements")
    achievement_type = models.CharField(max_length=20, choices=TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    awarded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.title}"


class Review(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews_given")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["student", "course"]

    def __str__(self):
        return f"{self.student.username}'s review of {self.course.title}"


class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="payments",
        help_text="The enrollment this payment is associated with",
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        help_text="Specific session this payment is for, if any",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    stripe_payment_intent_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.session:
            return f"Payment for {self.enrollment} - {self.session.title}"
        return f"Payment for {self.enrollment}"


class ForumCategory(models.Model):
    """Categories for organizing forum discussions."""

    name = models.CharField(max_length=100)
    description = models.TextField()
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, help_text="Font Awesome icon class")
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Forum Categories"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ForumTopic(models.Model):
    """Individual forum topics/threads."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.ForeignKey(ForumCategory, on_delete=models.CASCADE, related_name="topics")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_topics")
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title


class ForumReply(models.Model):
    """Replies to forum topics."""

    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_replies")
    content = models.TextField()
    is_solution = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Forum Replies"
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply by {self.author.username} on {self.topic.title}"


class PeerConnection(models.Model):
    """Connections between users for networking."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("blocked", "Blocked"),
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_connections")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_connections")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["sender", "receiver"]

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} ({self.status})"


class PeerMessage(models.Model):
    """Direct messages between connected peers."""

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"


class StudyGroup(models.Model):
    """Study groups for collaborative learning."""

    name = models.CharField(max_length=200)
    description = models.TextField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="study_groups")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_groups")
    members = models.ManyToManyField(User, related_name="joined_groups")
    max_members = models.IntegerField(default=10)
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile instance when a new User is created."""
    if created and not hasattr(instance, "profile"):
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the Profile instance when the User is saved."""
    if hasattr(instance, "profile"):
        instance.profile.save()
    else:
        Profile.objects.create(user=instance)


class BlogPost(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blog_posts")
    content = MarkdownxField()
    excerpt = models.TextField(blank=True)
    featured_image = models.ImageField(
        upload_to="blog/images/", blank=True, help_text="Featured image for the blog post"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    tags = models.CharField(
        max_length=200, blank=True, help_text="Comma-separated tags (e.g., 'python, django, web development')"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.status == "published" and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def reading_time(self):
        """Estimate reading time in minutes."""
        words_per_minute = 200
        word_count = len(self.content.split())
        minutes = word_count / words_per_minute
        return max(1, round(minutes))


class BlogComment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blog_comments")
    content = models.TextField()
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"


@receiver(user_signed_up)
def set_user_type(sender, request, user, **kwargs):
    """Set the user type (teacher/student) when they sign up."""
    is_teacher = request.POST.get("is_teacher") == "on"
    profile = user.profile
    profile.is_teacher = is_teacher
    profile.save()


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=40, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(session_key__gt=""),
                name="cart_user_or_session_key",
            )
        ]

    @property
    def item_count(self):
        return self.items.count()

    @property
    def has_goods(self):
        return self.items.filter(goods__isnull=False).exists()

    @property
    def total(self):
        return sum(item.final_price for item in self.items.all())

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return "Anonymous cart"


class Storefront(models.Model):
    teacher = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="storefront", verbose_name="Teacher Profile"
    )
    name = models.CharField(
        max_length=100, unique=True, help_text="Display name for your store", default="Default Store Name"
    )
    description = models.TextField(blank=True, help_text="Describe your store for customers")
    logo = models.ImageField(upload_to="store_logos/", blank=True, help_text="Recommended size: 200x200px")
    store_slug = models.SlugField(unique=True, blank=True, help_text="Auto-generated URL-friendly identifier")
    is_active = models.BooleanField(default=True, help_text="Enable/disable public visibility of your store")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.store_slug:
            self.store_slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base_slug = slugify(self.name)
        unique_slug = base_slug
        count = 1
        while Storefront.objects.filter(store_slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{count}"
            count += 1
        return unique_slug

    def __str__(self):
        return f"{self.name} (by {self.teacher.username})"


class Goods(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ("physical", "Physical Product"),
        ("digital", "Digital Download"),
    ]

    name = models.CharField(max_length=100, help_text="Product title (e.g., 'Algebra Basics Workbook')")
    description = models.TextField(help_text="Detailed product description")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in USD")
    discount_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, help_text="Discounted price (optional)"
    )
    stock = models.PositiveIntegerField(blank=True, null=True, help_text="Leave blank for digital products")
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPE_CHOICES, default="physical")
    file = models.FileField(upload_to="digital_goods/", blank=True, help_text="Required for digital products")
    category = models.CharField(max_length=100, blank=True, help_text="e.g., 'Books', 'Course Materials'")
    images = models.ManyToManyField("ProductImage", related_name="goods_images", blank=True)
    storefront = models.ForeignKey(Storefront, on_delete=models.CASCADE, related_name="goods")
    is_available = models.BooleanField(default=True, help_text="Show/hide product from store")
    sku = models.CharField(
        max_length=50, unique=True, blank=True, null=True, help_text="Inventory tracking ID (auto-generated)"
    )
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Validate discount logic
        if self.discount_price and self.discount_price >= self.price:
            raise ValidationError("Discount price must be lower than original price.")

        # Validate digital product constraints
        if self.product_type == "digital":
            if self.stock is not None:
                raise ValidationError("Digital products cannot have stock quantities.")
            if not self.file:
                raise ValidationError("Digital products require a file upload.")

        # Validate physical product constraints
        if self.product_type == "physical" and self.stock is None:
            raise ValidationError("Physical products must have a stock quantity.")

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f"{slugify(self.name[:20])}-{self.id}"
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Goods.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (${self.price})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name="cart_items")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, null=True, blank=True, related_name="cart_items")
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, null=True, blank=True, related_name="cart_items")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [
            ("cart", "course"),
            ("cart", "session"),
            ("cart", "goods"),
        ]

    def clean(self):
        if not self.course and not self.session and not self.goods:
            raise ValidationError("Either a course, session, or goods must be selected")
        if (self.course and self.session) or (self.course and self.goods) or (self.session and self.goods):
            raise ValidationError("Cannot select more than one type of item")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def price(self):
        if self.course:
            return self.course.price
        if self.session:
            return self.session.price or 0
        if self.goods:
            return self.goods.price
        return 0

    @property
    def final_price(self):
        if self.goods and self.goods.discount_price:  # Check for discount
            return self.goods.discount_price
        return self.price  # Fallback to original price

    def __str__(self):
        if self.course:
            return f"{self.course.title} in cart for {self.cart}"
        if self.session:
            return f"{self.session.title} in cart for {self.cart}"
        if self.goods:
            return f"{self.goods.name} in cart for {self.cart}"
        return "Unknown item in cart"


# Constants
ENROLLMENT_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("cancelled", "Cancelled"),
]


class SessionEnrollment(models.Model):
    """Model for tracking enrollments in individual sessions."""

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="session_enrollments")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(max_length=20, choices=ENROLLMENT_STATUS_CHOICES, default="pending")
    payment_intent_id = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["student", "session"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.email} - {self.session.title}"


class EventCalendar(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_calendars")
    created_at = models.DateTimeField(auto_now_add=True)
    month = models.IntegerField()  # 0-11 for Jan-Dec
    year = models.IntegerField()
    share_token = models.CharField(max_length=32, unique=True)  # For sharing the calendar

    def save(self, *args, **kwargs):
        if not self.share_token:
            self.share_token = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.month + 1}/{self.year}"

    @property
    def unique_participants_count(self):
        """Count unique participants by name"""
        return self.time_slots.values("name").distinct().count()


class TimeSlot(models.Model):
    calendar = models.ForeignKey(EventCalendar, on_delete=models.CASCADE, related_name="time_slots")
    name = models.CharField(max_length=100)
    day = models.IntegerField()  # 1-31
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["calendar", "name", "day"]  # One slot per person per day

    def __str__(self):
        return f"{self.name} - Day {self.day} ({self.start_time}-{self.end_time})"


class SearchLog(models.Model):
    query = models.CharField(max_length=255)
    results_count = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    filters_applied = models.JSONField(default=dict, blank=True)
    search_type = models.CharField(
        max_length=20,
        choices=[("course", "Course Search"), ("material", "Material Search"), ("forum", "Forum Search")],
        default="course",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.query} ({self.results_count} results)"


class Challenge(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    week_number = models.PositiveIntegerField(unique=True)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"Week {self.week_number}: {self.title}"


class ChallengeSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    submission_text = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s submission for Week {self.challenge.week_number}"
    
# Live challenge models
class Quiz(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    start_time = models.TimeField()
    end_date = models.DateField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.title} (From {self.start_date} {self.start_time} to {self.end_date} {self.end_time})"

class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()

    def __str__(self):
        return self.question_text

class QuizOption(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="options")
    option_text = models.TextField()
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Option: {self.option_text} (Correct: {self.is_correct})"

class QuizSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - Score: {self.score}"


class ProductImage(models.Model):
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, related_name="goods_images")
    image = models.ImageField(upload_to="goods_images/", help_text="Product display image")
    alt_text = models.CharField(max_length=125, blank=True, help_text="Accessibility description for screen readers")

    def __str__(self):
        return f"Image for {self.goods.name}"


class Order(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending Payment"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    storefront = models.ForeignKey(Storefront, on_delete=models.CASCADE, related_name="orders", null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    shipping_address = models.JSONField(blank=True, null=True, help_text="Structured shipping details")
    tracking_number = models.CharField(max_length=100, blank=True)
    terms_accepted = models.BooleanField(default=False, help_text="User accepted terms during checkout")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None  # Check if it's a new order
        super().save(*args, **kwargs)  # Save first to generate an ID

        if is_new and not self.tracking_number:
            self.tracking_number = self.generate_tracking_number()
            super().save(update_fields=["tracking_number"])

    def generate_tracking_number(self):
        return f"TRACK-{self.pk}-{int(time.time())}-{uuid.uuid4().hex[:6].upper()}"

    def __str__(self):
        return f"Order #{self.id} ({self.user.email})"

    def notify_user(self):
        subject = f"Order #{self.id} Status Update"
        message = f"Your order status is now: {self.get_status_display()}"
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.user.email], fail_silently=False)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    goods = models.ForeignKey(Goods, on_delete=models.PROTECT, verbose_name="Product")
    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    discounted_price_at_purchase = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, editable=False
    )

    class Meta:
        unique_together = [("order", "goods")]
        verbose_name = "Order Line Item"

    def __str__(self):
        return f"{self.quantity}x {self.goods.name}"
