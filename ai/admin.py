from django.contrib import admin
from .models import (
    LearningStreak, ProgressRecord, UserProgress, Achievement,
    UserAchievement, StudyPlan, StudyGroup, GroupDiscussion,
    DiscussionReply, Topic, StudentProfile, ChatSession, Message,
    Interaction
)

@admin.register(LearningStreak)
class LearningStreakAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_streak', 'longest_streak', 'last_activity']
    list_filter = ['last_activity']
    search_fields = ['user__username']

@admin.register(ProgressRecord)
class ProgressRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'topic', 'score', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['user__username', 'topic']

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject', 'progress', 'last_updated']
    list_filter = ['subject', 'last_updated']
    search_fields = ['user__username', 'subject']
    date_hierarchy = 'last_updated'

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'points']
    search_fields = ['name', 'description']

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ['user', 'achievement', 'earned_at']
    list_filter = ['achievement', 'earned_at']
    search_fields = ['user__username', 'achievement__name']
    date_hierarchy = 'earned_at'

@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'subject', 'start_date', 'end_date', 'progress']
    list_filter = ['subject', 'start_date', 'end_date']
    search_fields = ['user__username', 'title', 'subject']
    date_hierarchy = 'start_date'

@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'created_at']
    list_filter = ['subject']
    search_fields = ['name', 'description']
    filter_horizontal = ['members']

@admin.register(GroupDiscussion)
class GroupDiscussionAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'group', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'content', 'author__username']

@admin.register(DiscussionReply)
class DiscussionReplyAdmin(admin.ModelAdmin):
    list_display = ['discussion', 'author', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'author__username']

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'difficulty']
    list_filter = ['subject', 'difficulty']
    search_fields = ['name', 'description']
    filter_horizontal = ['prerequisites']

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'learning_style', 'difficulty_preference']
    list_filter = ['learning_style', 'difficulty_preference']
    search_fields = ['user__username']

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'title']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'is_user', 'timestamp']
    list_filter = ['is_user', 'timestamp']
    search_fields = ['content']

@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject', 'created_at']
    list_filter = ['subject', 'created_at']
    search_fields = ['user__username', 'question', 'answer']
    date_hierarchy = 'created_at'
