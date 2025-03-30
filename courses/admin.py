from django.contrib import admin
from .models import Course, Lesson, Enrollment

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'created_at')
    list_filter = ('instructor', 'created_at')
    search_fields = ('title', 'description', 'instructor__username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'created_at')
    list_filter = ('course', 'created_at')
    search_fields = ('title', 'content', 'course__title')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('course', 'order')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'enrolled_at', 'completed')
    list_filter = ('completed', 'enrolled_at')
    search_fields = ('user__username', 'course__title')
    readonly_fields = ('enrolled_at',)
    ordering = ('-enrolled_at',)
