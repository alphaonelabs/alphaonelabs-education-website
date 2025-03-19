import re

from allauth.account.forms import LoginForm, SignupForm
from captcha.fields import CaptchaField
from django import forms
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from markdownx.fields import MarkdownxFormField

from .models import (
    BlogPost,
    ChallengeSubmission,
    Course,
    CourseMaterial,
    EducationalVideo,
    ForumCategory,
    Goods,
    Meetup,
    Meme,
    ProductImage,
    Profile,
    ProgressTracker,
    Review,
    Session,
    Storefront,
    Subject,
    SuccessStory,
)
from .referrals import handle_referral
from .widgets import (
    TailwindCaptchaTextInput,
    TailwindCheckboxInput,
    TailwindDateTimeInput,
    TailwindEmailInput,
    TailwindFileInput,
    TailwindInput,
    TailwindNumberInput,
    TailwindSelect,
    TailwindTextarea,
)

__all__ = [
    "UserRegistrationForm",
    "ProfileForm",
    "ChallengeSubmissionForm",
    "CourseCreationForm",
    "CourseForm",
    "SessionForm",
    "ReviewForm",
    "CourseMaterialForm",
    "TeacherSignupForm",
    "ProfileUpdateForm",
    "CustomLoginForm",
    "LearnForm",
    "TeachForm",
    "InviteStudentForm",
    "ForumCategoryForm",
    "ForumTopicForm",
    "BlogPostForm",
    "MessageTeacherForm",
    "FeedbackForm",
    "GoodsForm",
    "StorefrontForm",
    "MeetupForm",
    "EducationalVideoForm",
    "ProgressTrackerForm",
    "SuccessStoryForm",
    "MemeForm",
]


class UserRegistrationForm(SignupForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=TailwindInput(attrs={"placeholder": "First Name"}),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=TailwindInput(attrs={"placeholder": "Last Name"}),
    )
    is_teacher = forms.BooleanField(
        required=False,
        label="Register as a teacher",
        widget=TailwindCheckboxInput(),
    )
    referral_code = forms.CharField(
        max_length=20,
        required=False,
        widget=TailwindInput(attrs={"placeholder": "Enter referral code"}),
        help_text="Optional - Enter a referral code if you have one",
    )
    captcha = CaptchaField(widget=TailwindCaptchaTextInput)

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Update email field
        self.fields["email"].widget = TailwindEmailInput(
            attrs={
                "placeholder": "your.email@example.com",
                "value": self.initial.get("email", ""),
            }
        )
        # Update password field
        self.fields["password1"].widget = TailwindInput(
            attrs={
                "type": "password",
                "placeholder": "Choose a secure password",
                "class": (
                    "block w-full border rounded p-2 focus:outline-none focus:ring-2 "
                    "focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800 "
                    "border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white"
                ),
            }
        )

        # Handle referral code from session or POST data
        if self.data:  # If form was submitted (POST)
            referral_code = self.data.get("referral_code")
            if referral_code:
                self.fields["referral_code"].initial = referral_code
        elif request and request.session.get("referral_code"):  # If new form (GET) with session data
            referral_code = request.session.get("referral_code")
            self.fields["referral_code"].initial = referral_code
            self.initial["referral_code"] = referral_code

        # Preserve values on form errors
        if self.data:
            for field_name in ["first_name", "last_name", "email", "referral_code", "username"]:
                if field_name in self.data and field_name in self.fields:
                    self.fields[field_name].widget.attrs["value"] = self.data[field_name]

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username:
            try:
                User.objects.get(username=username)
                raise forms.ValidationError("This username is already taken. Please choose a different one.")
            except User.DoesNotExist:
                return username
        return username

    def clean_referral_code(self):
        referral_code = self.cleaned_data.get("referral_code")
        if referral_code:
            if not Profile.objects.filter(referral_code=referral_code).exists():
                raise forms.ValidationError("Invalid referral code. Please check and try again.")
        return referral_code

    def save(self, request):
        # First call parent's save to create the user and send verification email
        try:
            user = super().save(request)
        except IntegrityError:
            raise forms.ValidationError("This username is already taken. Please choose a different one.")

        # Then update the additional fields
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save()

        # Update the user's profile
        if self.cleaned_data.get("is_teacher"):
            user.profile.is_teacher = True
            user.profile.save()

        # Handle the referral
        referral_code = self.cleaned_data.get("referral_code")
        if referral_code:
            handle_referral(user, referral_code)

        # Return the user object
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("bio", "expertise")
        widgets = {
            "bio": TailwindTextarea(attrs={"rows": 4}),
            "expertise": TailwindInput(attrs={"placeholder": "Your areas of expertise"}),
        }


class CourseCreationForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = (
            "title",
            "description",
            "image",
            "learning_objectives",
            "prerequisites",
            "price",
            "allow_individual_sessions",
            "max_students",
            "subject",
            "level",
            "tags",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "image": TailwindFileInput(
                attrs={
                    "accept": "image/*",
                    "help_text": "Course image must be 300x150 pixels",
                }
            ),
            "learning_objectives": forms.Textarea(attrs={"rows": 4}),
            "prerequisites": forms.Textarea(attrs={"rows": 4}),
            "allow_individual_sessions": TailwindCheckboxInput(
                attrs={"help_text": ("Allow students to register for individual sessions")}
            ),
            "tags": forms.TextInput(attrs={"placeholder": "Enter comma-separated tags"}),
        }

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price <= 0:
            raise forms.ValidationError("Price must be greater than zero")
        return price

    def clean_max_students(self):
        max_students = self.cleaned_data.get("max_students")
        if max_students <= 0:
            msg = "Maximum number of students must be greater than zero"
            raise forms.ValidationError(msg)
        return max_students


class CourseForm(forms.ModelForm):
    description = MarkdownxFormField(
        label="Description", help_text="Use markdown for formatting. You can use **bold**, *italic*, lists, etc."
    )
    learning_objectives = MarkdownxFormField(
        label="Learning Objectives",
        help_text="Use markdown for formatting. List your objectives using - or * for bullet points.",
    )
    prerequisites = MarkdownxFormField(
        label="Prerequisites",
        help_text="Use markdown for formatting. List prerequisites using - or * for bullet points.",
        required=False,
    )

    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "image",
            "learning_objectives",
            "prerequisites",
            "price",
            "allow_individual_sessions",
            "invite_only",
            "max_students",
            "subject",
            "level",
            "tags",
        ]
        widgets = {
            "title": TailwindInput(),
            "description": TailwindTextarea(attrs={"rows": 4}),
            "image": TailwindFileInput(
                attrs={
                    "accept": "image/*",
                    "help_text": "Course image must be 300x150 pixels",
                }
            ),
            "learning_objectives": TailwindTextarea(attrs={"rows": 4}),
            "prerequisites": TailwindTextarea(attrs={"rows": 4}),
            "price": TailwindNumberInput(attrs={"min": "0", "step": "0.01"}),
            "allow_individual_sessions": TailwindCheckboxInput(
                attrs={"help_text": ("Allow students to register for individual sessions")}
            ),
            "invite_only": TailwindCheckboxInput(
                attrs={"help_text": ("If enabled, students can only enroll with an invitation")}
            ),
            "max_students": TailwindNumberInput(attrs={"min": "1"}),
            "subject": TailwindSelect(),
            "level": TailwindSelect(),
            "tags": TailwindInput(attrs={"placeholder": "Enter comma-separated tags"}),
        }

    def clean_max_students(self):
        max_students = self.cleaned_data.get("max_students")
        if max_students <= 0:
            msg = "Maximum number of students must be greater than zero"
            raise forms.ValidationError(msg)
        return max_students


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = [
            "title",
            "description",
            "start_time",
            "end_time",
            "is_virtual",
            "meeting_link",
            "location",
            "price",
            "enable_rollover",
            "rollover_pattern",
        ]
        widgets = {
            "title": TailwindInput(),
            "description": TailwindTextarea(attrs={"rows": 4}),
            "start_time": TailwindDateTimeInput(),
            "end_time": TailwindDateTimeInput(),
            "is_virtual": TailwindCheckboxInput(),
            "meeting_link": TailwindInput(attrs={"type": "url"}),
            "location": TailwindInput(),
            "price": TailwindNumberInput(
                attrs={
                    "min": "0",
                    "step": "0.01",
                    "help_text": ("Price for individual session registration"),
                }
            ),
            "enable_rollover": TailwindCheckboxInput(),
            "rollover_pattern": TailwindSelect(),
        }
        help_texts = {
            "start_time": "Click to select the session start date and time",
            "end_time": "Click to select the session end date and time",
            "enable_rollover": "Enable automatic date rollover if no students are enrolled",
            "rollover_pattern": "How often to roll over the session dates",
        }

    def clean(self):
        cleaned_data = super().clean()
        is_virtual = cleaned_data.get("is_virtual")
        meeting_link = cleaned_data.get("meeting_link")
        location = cleaned_data.get("location")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        price = cleaned_data.get("price")

        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "End time must be after start time.")

        if is_virtual and not meeting_link:
            msg = "Meeting link is required for virtual sessions."
            self.add_error("meeting_link", msg)
        elif not is_virtual and not location:
            msg = "Location is required for in-person sessions."
            self.add_error("location", msg)

        if price is not None and price < 0:
            self.add_error("price", "Price cannot be negative.")

        return cleaned_data


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "comment")
        widgets = {
            "rating": TailwindNumberInput(attrs={"min": "1", "max": "5"}),
            "comment": TailwindTextarea(attrs={"rows": 4}),
        }


class CourseMaterialForm(forms.ModelForm):
    class Meta:
        model = CourseMaterial
        fields = (
            "title",
            "description",
            "material_type",
            "file",
            "external_url",
            "session",
            "is_downloadable",
            "order",
        )
        widgets = {
            "title": TailwindInput(),
            "description": TailwindTextarea(attrs={"rows": 3}),
            "material_type": TailwindSelect(),
            "file": TailwindFileInput(),
            "external_url": TailwindInput(attrs={"placeholder": "Enter video URL"}),  # Add widget for external_url
            "session": TailwindSelect(),
            "is_downloadable": TailwindCheckboxInput(),
            "order": TailwindNumberInput(attrs={"min": 0}),
        }
        labels = {
            "external_url": "External URL",  # Update label
        }

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        if course:
            self.fields["session"].queryset = course.sessions.all()


class TeacherSignupForm(forms.Form):
    email = forms.EmailField(widget=TailwindEmailInput())
    username = forms.CharField(
        max_length=150,
        widget=TailwindInput(attrs={"placeholder": "Choose a username"}),
        help_text="This will be your unique identifier on the platform.",
    )
    subject = forms.CharField(max_length=100, widget=TailwindInput())
    captcha = CaptchaField(widget=TailwindCaptchaTextInput)

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose a different one.")
        return username

    def save(self):
        email = self.cleaned_data["email"]
        username = self.cleaned_data["username"]
        subject_name = self.cleaned_data["subject"]

        random_password = get_random_string(length=30)
        try:
            user = User.objects.create_user(username=username, email=email, password=random_password)
        except IntegrityError:
            raise forms.ValidationError("This username is already taken. Please try again with a different username.")

        # Set user as teacher
        profile = user.profile
        profile.is_teacher = True
        profile.save()

        # Create subject
        subject, created = Subject.objects.get_or_create(
            name=subject_name,
            defaults={
                "slug": slugify(subject_name),
                "description": f"Courses about {subject_name}",
            },
        )

        return user, subject


class ProfileUpdateForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=TailwindInput(),
        help_text="This is your public username that will be visible to other users",
    )
    first_name = forms.CharField(
        max_length=30, required=False, widget=TailwindInput(), help_text="Your real name will not be shown publicly"
    )
    last_name = forms.CharField(
        max_length=30, required=False, widget=TailwindInput(), help_text="Your real name will not be shown publicly"
    )
    email = forms.EmailField(
        required=True, widget=TailwindEmailInput(), help_text="Your email will not be shown publicly"
    )
    bio = forms.CharField(
        required=False,
        widget=TailwindTextarea(attrs={"rows": 4}),
        help_text="Tell us about yourself - this will be visible on your public profile",
    )
    expertise = forms.CharField(
        max_length=200,
        required=False,
        widget=TailwindInput(),
        help_text=(
            "List your areas of expertise (e.g. Python, Machine Learning, Web Development) - "
            "this will be visible on your public profile"
        ),
    )
    avatar = forms.ImageField(
        required=False,
        widget=TailwindFileInput(),
        help_text="Upload a profile picture (will be cropped to a square and resized to 200x200 pixels)",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            try:
                profile = self.instance.profile
                self.fields["bio"].initial = profile.bio
                self.fields["expertise"].initial = profile.expertise
            except Profile.DoesNotExist:
                pass

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.exclude(pk=self.instance.pk).filter(username=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose a different one.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile, created = Profile.objects.get_or_create(user=user)
            profile.bio = self.cleaned_data["bio"]
            profile.expertise = self.cleaned_data["expertise"]
            if self.cleaned_data.get("avatar"):
                profile.avatar = self.cleaned_data["avatar"]
            profile.save()
        return user


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].widget.attrs.update(
            {
                "class": (
                    "block w-full rounded-md border-0 py-2 px-4 "
                    "text-gray-900 dark:text-white shadow-sm "
                    "ring-1 ring-inset ring-gray-300 "
                    "dark:ring-gray-600 "
                    "placeholder:text-gray-400 "
                    "focus:ring-2 focus:ring-inset "
                    "focus:ring-orange-500 dark:bg-gray-700 "
                    "sm:text-base sm:leading-6"
                )
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "class": (
                    "block w-full rounded-md border-0 py-2 px-4 "
                    "text-gray-900 dark:text-white shadow-sm "
                    "ring-1 ring-inset ring-gray-300 "
                    "dark:ring-gray-600 "
                    "placeholder:text-gray-400 "
                    "focus:ring-2 focus:ring-inset "
                    "focus:ring-orange-500 dark:bg-gray-700 "
                    "sm:text-base sm:leading-6 pr-10"
                )
            }
        )
        self.fields["remember"].widget.attrs.update(
            {
                "class": (
                    "h-4 w-4 text-orange-500 "
                    "focus:ring-orange-500 "
                    "border-gray-300 dark:border-gray-600 "
                    "rounded cursor-pointer"
                )
            }
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data is None:
            return {}

        # Check if user exists and can log in
        if "login" in cleaned_data:
            email = cleaned_data["login"]
            try:
                User.objects.get(email=email)
            except User.DoesNotExist:
                raise forms.ValidationError(
                    "No account found with this email address. Please check the email or sign up."
                )

        return cleaned_data


class EducationalVideoForm(forms.ModelForm):
    """
    Form for creating and editing educational videos.
    Validates that video URLs are from YouTube or Vimeo with proper video ID formats.
    """

    class Meta:
        model = EducationalVideo
        fields = ["title", "description", "video_url", "category"]
        widgets = {
            "title": TailwindInput(attrs={"placeholder": "Video title"}),
            "description": TailwindTextarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Describe what viewers will learn from this video",
                }
            ),
            "video_url": TailwindInput(attrs={"placeholder": "YouTube or Vimeo URL", "type": "url"}),
            "category": TailwindSelect(
                attrs={
                    "class": (
                        "w-full px-4 py-2 border border-gray-300 dark:border-gray-600"
                        " rounded-lg focus:ring-2 focus:ring-blue-500"
                    )
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order subjects by name
        self.fields["category"].queryset = Subject.objects.all().order_by("order", "name")

    def clean_video_url(self):
        url = self.cleaned_data.get("video_url")
        if url:
            # More robust validation with regex
            youtube_pattern = r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]{11}.*$"
            vimeo_pattern = r"^(https?://)?(www\.)?vimeo\.com/[0-9]{8,}.*$"
            if not (re.match(youtube_pattern, url) or re.match(vimeo_pattern, url)):
                raise forms.ValidationError("Please enter a valid YouTube or Vimeo URL")
        return url


class SuccessStoryForm(forms.ModelForm):
    content = MarkdownxFormField(
        label="Content", help_text="Use markdown for formatting. You can use **bold**, *italic*, lists, etc."
    )

    class Meta:
        model = SuccessStory
        fields = ["title", "content", "excerpt", "featured_image", "status"]
        widgets = {
            "title": TailwindInput(attrs={"placeholder": "Your success story title"}),
            "excerpt": TailwindTextarea(
                attrs={"rows": 3, "placeholder": "A brief summary of your success story (optional)"}
            ),
            "featured_image": TailwindFileInput(
                attrs={"accept": "image/*", "help_text": "Featured image for your success story (optional)"}
            ),
            "status": TailwindSelect(),
        }


class LearnForm(forms.Form):
    subject = forms.CharField(
        max_length=100,
        widget=TailwindInput(
            attrs={
                "placeholder": "What would you like to learn?",
                "class": "block w-full border rounded p-2 focus:outline-none focus:ring-2 focus:ring-orange-500",
            }
        ),
    )
    email = forms.EmailField(
        widget=TailwindEmailInput(
            attrs={
                "placeholder": "Your email address",
                "class": "block w-full border rounded p-2 focus:outline-none focus:ring-2 focus:ring-orange-500",
            }
        )
    )
    message = forms.CharField(
        widget=TailwindTextarea(
            attrs={
                "placeholder": "Tell us more about what you want to learn...",
                "rows": 4,
                "class": "block w-full border rounded p-2 focus:outline-none focus:ring-2 focus:ring-orange-500",
            }
        ),
        required=False,
    )
    captcha = CaptchaField(
        widget=TailwindCaptchaTextInput(
            attrs={"class": "block w-full border rounded p-2 focus:outline-none focus:ring-2 focus:ring-orange-500"}
        )
    )


class TeachForm(forms.Form):
    subject = forms.CharField(
        max_length=100,
        widget=TailwindInput(
            attrs={
                "placeholder": "What would you like to teach?",
                "class": "block w-full border rounded p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500",
            }
        ),
    )
    email = forms.EmailField(
        widget=TailwindEmailInput(
            attrs={
                "placeholder": "Your email address",
                "class": "block w-full border rounded p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500",
            }
        )
    )
    expertise = forms.CharField(
        widget=TailwindTextarea(
            attrs={
                "placeholder": "Tell us about your expertise and teaching experience...",
                "rows": 4,
                "class": "block w-full border rounded p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500",
            }
        )
    )
    captcha = CaptchaField(
        widget=TailwindCaptchaTextInput(
            attrs={"class": "block w-full border rounded p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"}
        )
    )


class InviteStudentForm(forms.Form):
    email = forms.EmailField(
        label="Student's Email",
        widget=forms.EmailInput(
            attrs={
                "class": (
                    "w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 "
                    "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 "
                    "focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 focus:border-transparent"
                ),
                "placeholder": "Enter student's email address",
            }
        ),
    )
    message = forms.CharField(
        required=False,
        label="Personal Message (optional)",
        widget=forms.Textarea(
            attrs={
                "class": (
                    "w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 "
                    "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 "
                    "focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 focus:border-transparent"
                ),
                "placeholder": "Add a personal message to your invitation",
                "rows": 3,
            }
        ),
    )


class ForumCategoryForm(forms.ModelForm):
    """Form for creating and editing forum categories."""

    class Meta:
        model = ForumCategory
        fields = ["name", "description", "icon", "slug"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": (
                        "w-full border border-gray-300 dark:border-gray-600 rounded p-2 "
                        "focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 "
                        "dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-800"
                    )
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": (
                        "w-full border border-gray-300 dark:border-gray-600 rounded p-2 "
                        "focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 "
                        "dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-800"
                    ),
                    "rows": 4,
                }
            ),
            "icon": forms.TextInput(
                attrs={
                    "class": (
                        "w-full border border-gray-300 dark:border-gray-600 rounded p-2 "
                        "focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 "
                        "dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-800"
                    ),
                    "placeholder": "fa-folder",
                }
            ),
            "slug": forms.HiddenInput(),
        }
        help_texts = {
            "icon": "Enter a Font Awesome icon class (e.g., fa-folder, fa-book, fa-code)",
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        if name:
            cleaned_data["slug"] = slugify(name)
        return cleaned_data


class ForumTopicForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        required=True,
        widget=TailwindInput(
            attrs={
                "class": (
                    "w-full border border-gray-300 dark:border-gray-600 rounded p-2 "
                    "focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 "
                    "dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-800"
                ),
                "placeholder": "Enter your topic title",
            }
        ),
    )
    content = forms.CharField(
        required=True,
        widget=TailwindTextarea(
            attrs={
                "class": (
                    "w-full border border-gray-300 dark:border-gray-600 rounded p-2 "
                    "focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 "
                    "dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-800"
                ),
                "rows": 6,
                "placeholder": "Write your topic content here...",
            }
        ),
    )


class BlogPostForm(forms.ModelForm):
    """Form for creating and editing blog posts."""

    class Meta:
        model = BlogPost
        fields = ["title", "content", "excerpt", "featured_image", "status", "tags"]

        input_classes = (
            "w-full border border-gray-300 dark:border-gray-600 rounded p-2 "
            "focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 "
            "dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-800"
        )

        widgets = {
            "title": forms.TextInput(attrs={"class": input_classes}),
            "content": forms.Textarea(attrs={"class": input_classes, "rows": 10}),
            "excerpt": forms.Textarea(attrs={"class": input_classes, "rows": 3}),
            "tags": forms.TextInput(
                attrs={
                    "class": input_classes,
                    "placeholder": "Enter comma-separated tags",
                }
            ),
            "status": forms.Select(attrs={"class": input_classes}),
        }


class MessageTeacherForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        required=True,
        widget=TailwindInput(
            attrs={
                "class": (
                    "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                    "rounded-lg focus:ring-2 focus:ring-blue-500"
                )
            }
        ),
    )
    email = forms.EmailField(
        required=True,
        widget=TailwindEmailInput(
            attrs={
                "class": (
                    "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                    "rounded-lg focus:ring-2 focus:ring-blue-500"
                )
            }
        ),
    )
    message = forms.CharField(
        widget=TailwindTextarea(
            attrs={
                "class": (
                    "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                    "rounded-lg focus:ring-2 focus:ring-blue-500"
                ),
                "rows": 5,
            }
        ),
        required=True,
    )
    captcha = CaptchaField(
        required=False,
        widget=TailwindCaptchaTextInput(
            attrs={
                "class": (
                    "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                    "rounded-lg focus:ring-2 focus:ring-blue-500"
                )
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # If user is authenticated, remove name, email and captcha fields
        if user and user.is_authenticated:
            del self.fields["name"]
            del self.fields["email"]
            del self.fields["captcha"]


class FeedbackForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        required=False,
        widget=TailwindInput(
            attrs={
                "placeholder": "Your name (optional)",
                "class": (
                    "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                    "rounded-lg focus:ring-2 focus:ring-blue-500"
                ),
            }
        ),
    )
    email = forms.EmailField(
        required=False,
        widget=TailwindEmailInput(
            attrs={
                "placeholder": "Your email (optional)",
                "class": (
                    "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                    "rounded-lg focus:ring-2 focus:ring-blue-500"
                ),
            }
        ),
    )
    description = forms.CharField(
        widget=TailwindTextarea(
            attrs={
                "placeholder": "Your feedback...",
                "rows": 4,
                "class": (
                    "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                    "rounded-lg focus:ring-2 focus:ring-blue-500"
                ),
            }
        ),
        required=True,
    )
    captcha = CaptchaField(widget=TailwindCaptchaTextInput)


class ChallengeSubmissionForm(forms.ModelForm):
    class Meta:
        model = ChallengeSubmission
        fields = ["submission_text"]
        widgets = {
            "submission_text": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Describe your results or reflections..."}
            ),
        }


class TailwindInput(forms.widgets.Input):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {}).update(
            {"class": "w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"}
        )
        super().__init__(*args, **kwargs)


class TailwindTextarea(forms.widgets.Textarea):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {}).update(
            {"class": "w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"}
        )
        super().__init__(*args, **kwargs)


class GoodsForm(forms.ModelForm):
    """Form for creating/updating goods with full validation"""

    class Meta:
        model = Goods
        fields = [
            "name",
            "description",
            "price",
            "discount_price",
            "product_type",
            "stock",
            "file",
            "category",
            "is_available",
        ]
        widgets = {
            "name": TailwindInput(attrs={"placeholder": "Algebra Basics Workbook"}),
            "description": TailwindTextarea(attrs={"rows": 4, "placeholder": "Detailed product description"}),
            "price": forms.NumberInput(attrs={"class": "tailwind-input-class", "min": "0", "step": "0.01"}),
            "discount_price": forms.NumberInput(attrs={"class": "tailwind-input-class", "min": "0", "step": "0.01"}),
            "product_type": forms.Select(attrs={"onchange": "toggleDigitalFields(this.value)"}),
            "stock": forms.NumberInput(attrs={"data-product-type": "physical"}),
            "file": forms.FileInput(attrs={"accept": ".pdf,.zip,.mp4,.docx", "data-product-type": "digital"}),
            "category": forms.TextInput(attrs={"placeholder": "Educational Materials"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product_type"].initial = "physical"

        if self.instance and self.instance.pk:
            if self.instance.product_type == "digital":
                self.fields["file"].required = True
                self.fields["stock"].required = False
            else:
                self.fields["stock"].required = True

    def clean(self):
        cleaned_data = super().clean()
        product_type = cleaned_data.get("product_type")
        price = cleaned_data.get("price")
        discount_price = cleaned_data.get("discount_price")
        stock = cleaned_data.get("stock")
        file = cleaned_data.get("file")

        if discount_price and discount_price >= price:
            self.add_error("discount_price", "Discount must be lower than base price")

        if product_type == "digital":
            if stock is not None:
                self.add_error("stock", "Digital products can't have stock")
            if not file and not self.instance.file:
                self.add_error("file", "File required for digital products")
        else:
            if stock is None:
                self.add_error("stock", "Stock required for physical products")
            if file:
                self.add_error("file", "Files only for digital products")

        return cleaned_data

    def save(self, commit=True):
        goods = super().save(commit=False)

        # Handle product type specific fields
        if goods.product_type == "digital":
            goods.stock = None
        else:
            goods.file = None

        if commit:
            goods.save()
            self.save_images(goods)

        return goods

    def save_images(self, goods):
        # Delete existing images if replacing
        if "images" in self.changed_data:
            goods.images.all().delete()

        # Create new ProductImage instances
        for img in self.files.getlist("images"):
            ProductImage.objects.create(goods=goods, image=img)


class StorefrontForm(forms.ModelForm):
    class Meta:
        model = Storefront
        fields = [
            "name",
            "description",
            "store_slug",
            "logo",
            "is_active",
        ]


class ProgressTrackerForm(forms.ModelForm):
    class Meta:
        model = ProgressTracker
        fields = ["title", "description", "current_value", "target_value", "color", "public"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class MemeForm(forms.ModelForm):
    new_subject = forms.CharField(
        max_length=100,
        required=False,
        widget=TailwindInput(
            attrs={
                "placeholder": "Enter a new subject name",
                "class": "w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500",
            }
        ),
        help_text="If your subject isn't listed, enter a new one here",
    )

    class Meta:
        model = Meme
        fields = ["title", "subject", "new_subject", "caption", "image"]
        widgets = {
            "title": TailwindInput(
                attrs={
                    "placeholder": "Enter a descriptive title",
                    "required": True,
                }
            ),
            "subject": TailwindSelect(
                attrs={
                    "class": "w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                }
            ),
            "caption": TailwindTextarea(
                attrs={
                    "placeholder": "Add a caption for your meme",
                    "rows": 3,
                }
            ),
            "image": TailwindFileInput(
                attrs={
                    "accept": "image/png,image/jpeg,image/gif",
                    "required": True,
                    "help_text": "Upload a meme image (JPG, PNG, or GIF, max 2MB)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subject"].required = False
        self.fields["subject"].help_text = "Select an existing subject"

        # Improve error messages
        self.fields["image"].error_messages = {
            "required": "Please select an image file.",
            "invalid": "Please upload a valid image file.",
        }

    def clean(self):
        cleaned_data = super().clean()
        subject = cleaned_data.get("subject")
        new_subject = cleaned_data.get("new_subject")

        if not subject and not new_subject:
            raise forms.ValidationError("You must either select an existing subject or create a new one.")

        return cleaned_data

    def save(self, commit=True):
        meme = super().save(commit=False)

        # Create new subject if provided
        new_subject_name = self.cleaned_data.get("new_subject")
        if new_subject_name and not self.cleaned_data.get("subject"):
            from django.utils.text import slugify

            subject, created = Subject.objects.get_or_create(
                name=new_subject_name, defaults={"slug": slugify(new_subject_name)}
            )
            meme.subject = subject

        if commit:
            meme.save()
        return meme


class StudentEnrollmentForm(forms.Form):
    first_name = forms.CharField(
        max_length=30, required=True, widget=TailwindInput(attrs={"placeholder": "First Name"}), label="First Name"
    )
    last_name = forms.CharField(
        max_length=30, required=True, widget=TailwindInput(attrs={"placeholder": "Last Name"}), label="Last Name"
    )
    email = forms.EmailField(
        required=True, widget=TailwindEmailInput(attrs={"placeholder": "Student Email"}), label="Student Email"
    )


class MeetupForm(forms.ModelForm):
    class Meta:
        model = Meetup
        fields = ["title", "description", "date", "link", "location", "event_type"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "block w-full border border-gray-300 dark:border-gray-600 rounded p-2 "
                    "focus:outline-none focus:ring-2 focus:ring-teal-300 dark:focus:ring-teal-800 "
                    "bg-white dark:bg-gray-800",
                    "required": True,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "block w-full border border-gray-300 dark:border-gray-600 rounded p-2 "
                    "focus:outline-none focus:ring-2 focus:ring-teal-300 dark:focus:ring-teal-800 "
                    "bg-white dark:bg-gray-800",
                    "required": True,
                }
            ),
            "date": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "block w-full border border-gray-300 dark:border-gray-600 rounded p-2 focus:outline-none "
                    "focus:ring-2 focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800",
                    "required": True,
                }
            ),
            "link": forms.URLInput(
                attrs={
                    "class": "block w-full border border-gray-300 dark:border-gray-600 rounded p-2 focus:outline-none "
                    "focus:ring-2 focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800",
                }
            ),
            "location": forms.TextInput(
                attrs={
                    "class": "block w-full border border-gray-300 dark:border-gray-600 rounded p-2 focus:outline-none "
                    "focus:ring-2 focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800",
                }
            ),
            "event_type": forms.Select(
                attrs={
                    "class": "block w-full border border-gray-300 dark:border-gray-600 rounded p-2 focus:outline-none "
                    "focus:ring-2 focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800",
                    "required": True,
                },
                choices=[("online", "Online"), ("in_person", "In Person")],
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        event_type = cleaned_data.get("event_type")
        location = cleaned_data.get("location")
        link = cleaned_data.get("link")

        if event_type == "in_person" and not location:
            self.add_error("location", "Location is required for in-person events.")

        if event_type == "online" and not link:
            self.add_error("link", "Link is required for online events.")

        return cleaned_data
