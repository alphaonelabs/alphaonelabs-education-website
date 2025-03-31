from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages

def course_list(request):
    return render(request, 'courses/course_list.html')

def course_detail(request, slug):
    return render(request, 'courses/course_detail.html')

@login_required
def enroll_course(request, slug):
    return redirect('courses:course_detail', slug=slug)

@login_required
def unenroll_course(request, slug):
    return redirect('courses:course_list')

@login_required
def edit_course(request, slug):
    return render(request, 'courses/edit_course.html')

@login_required
def delete_course(request, slug):
    return redirect('courses:course_list')

@login_required
def add_session(request, slug):
    return render(request, 'courses/add_session.html')

def session_detail(request, slug, session_id):
    return render(request, 'courses/session_detail.html')

@login_required
def edit_session(request, slug, session_id):
    return render(request, 'courses/edit_session.html')

@login_required
def delete_session(request, slug, session_id):
    return redirect('courses:course_detail', slug=slug)

@login_required
def course_students(request, slug):
    return render(request, 'courses/course_students.html')

def student_detail(request, slug, student_id):
    return render(request, 'courses/student_detail.html')

def student_progress(request, slug, student_id):
    return render(request, 'courses/student_progress.html')

def course_materials(request, slug):
    return render(request, 'courses/course_materials.html')

@login_required
def upload_material(request, slug):
    return render(request, 'courses/upload_material.html')

@login_required
def delete_material(request, slug, material_id):
    return redirect('courses:course_materials', slug=slug)

def download_material(request, slug, material_id):
    return HttpResponse('Material downloaded')

def course_reviews(request, slug):
    return render(request, 'courses/course_reviews.html')

@login_required
def add_review(request, slug):
    return render(request, 'courses/add_review.html')

@login_required
def edit_review(request, slug, review_id):
    return render(request, 'courses/edit_review.html')

@login_required
def delete_review(request, slug, review_id):
    return redirect('courses:course_reviews', slug=slug)

def course_analytics(request, slug):
    return render(request, 'courses/course_analytics.html')

def course_marketing(request, slug):
    return render(request, 'courses/course_marketing.html') 