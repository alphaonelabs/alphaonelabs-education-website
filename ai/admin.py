from django.contrib import admin
from .models import Interaction, ProgressRecord, StudentProfile, StudyPlan

@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'created_at', 'ai_provider', 'feedback_rating')
    list_filter = ('subject', 'ai_provider', 'created_at')
    search_fields = ('question', 'answer', 'user__username')
    date_hierarchy = 'created_at'

@admin.register(ProgressRecord)
class ProgressRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'topic', 'mastery_level', 'updated_at')
    list_filter = ('subject', 'updated_at')
    search_fields = ('user__username', 'subject', 'topic')
    date_hierarchy = 'updated_at'

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'learning_style', 'difficulty_preference', 'created_at')
    list_filter = ('learning_style', 'difficulty_preference')
    search_fields = ('user__username', 'user__email')
    date_hierarchy = 'created_at'

@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'subject', 'start_date', 'end_date')
    list_filter = ('subject', 'created_at')
    search_fields = ('title', 'description', 'user__username')
    date_hierarchy = 'created_at'
