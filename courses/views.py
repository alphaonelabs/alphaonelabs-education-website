from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Course, Session, Enrollment

def course_list(request):
    courses = Course.objects.filter(is_active=True)
    return render(request, 'courses/course_list.html', {'courses': courses})

def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug, is_active=True)
    return render(request, 'courses/course_detail.html', {'course': course})

@login_required
def enroll_course(request, slug):
    course = get_object_or_404(Course, slug=slug, is_active=True)
    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course,
        defaults={'is_active': True}
    )
    if created:
        messages.success(request, f'Successfully enrolled in {course.title}')
    else:
        messages.info(request, f'You are already enrolled in {course.title}')
    return redirect('courses:course_detail', slug=slug)

def session_list(request, slug):
    course = get_object_or_404(Course, slug=slug, is_active=True)
    sessions = course.sessions.all()
    return render(request, 'courses/session_list.html', {
        'course': course,
        'sessions': sessions
    })

def session_detail(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    return render(request, 'courses/session_detail.html', {'session': session})
