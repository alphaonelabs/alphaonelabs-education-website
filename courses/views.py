from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Course, Lesson, Enrollment

def course_list(request):
    """Display a list of all available courses."""
    courses = Course.objects.all()
    return render(request, 'courses/course_list.html', {'courses': courses})

def course_detail(request, course_id):
    """Display details of a specific course."""
    course = get_object_or_404(Course, id=course_id)
    lessons = course.lessons.all()
    is_enrolled = False
    
    if request.user.is_authenticated:
        is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    
    context = {
        'course': course,
        'lessons': lessons,
        'is_enrolled': is_enrolled,
    }
    
    return render(request, 'courses/course_detail.html', context)

@login_required
@require_POST
def course_enroll(request, course_id):
    """Enroll a user in a course."""
    course = get_object_or_404(Course, id=course_id)
    
    # Check if already enrolled
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.warning(request, _('You are already enrolled in this course.'))
        return redirect('courses:course_detail', course_id=course.id)
    
    # Create enrollment
    Enrollment.objects.create(user=request.user, course=course)
    messages.success(request, _('Successfully enrolled in the course.'))
    
    return redirect('courses:course_detail', course_id=course.id)

@login_required
def lesson_detail(request, course_id, lesson_id):
    """Display details of a specific lesson."""
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    
    # Check if user is enrolled
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.warning(request, _('You must be enrolled in the course to view lessons.'))
        return redirect('courses:course_detail', course_id=course.id)
    
    context = {
        'course': course,
        'lesson': lesson,
    }
    
    return render(request, 'courses/lesson_detail.html', context)
