from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Sum, F, Q, Max, Case, When, Value, IntegerField
from django.utils import timezone
from datetime import timedelta

from web.models import (
    Course, Enrollment, CourseProgress, Session, SessionAttendance,
    Achievement, Profile
)
from .utils import (
    calculate_student_progress_statistics, 
    calculate_attendance_statistics,
    analyze_learning_patterns
)
from .export import export_csv, export_pdf, export_json

# Function to check if a user is an educator
def is_educator(user):
    return Course.objects.filter(teacher=user).exists()

@login_required
@user_passes_test(is_educator)
def export_analytics(request, export_format, analytics_type, obj_id=None):
    """
    Route to appropriate export function based on requested format.
    
    Args:
        request: HttpRequest object
        export_format: Format to export ('csv', 'pdf', or 'json')
        analytics_type: Type of analytics ('course', 'student', or 'learning_patterns')
        obj_id: ID of the object (course or student)
        
    Returns:
        HttpResponse with the requested export format
    """
    # Verify that the user has permission to export this data
    if analytics_type == 'course' and obj_id:
        course = get_object_or_404(Course, id=obj_id)
        if course.teacher != request.user:
            return HttpResponse("Permission denied", status=403)
    
    # For student analytics, check if the student is enrolled in any of the educator's courses
    if analytics_type == 'student' and obj_id:
        student = get_object_or_404(User, id=obj_id)
        has_access = Enrollment.objects.filter(
            student=student,
            course__teacher=request.user
        ).exists()
        
        if not has_access:
            return HttpResponse("Permission denied", status=403)
    
    # Route to appropriate export function
    if export_format == 'csv':
        return export_csv(request, analytics_type, obj_id)
    elif export_format == 'pdf':
        return export_pdf(request, analytics_type, obj_id)
    elif export_format == 'json':
        return export_json(request, analytics_type, obj_id)
    else:
        return HttpResponse("Unsupported export format", status=400)

@login_required
@user_passes_test(is_educator)
def educator_analytics_dashboard(request):
    """
    Main analytics dashboard for educators showing comprehensive data and insights.
    """
    # Get the teacher's courses
    courses = Course.objects.filter(teacher=request.user)
    course_ids = courses.values_list('id', flat=True)
    
    # Get overall stats
    total_students = Enrollment.objects.filter(course__in=courses).values('student').distinct().count()
    total_sessions = Session.objects.filter(course__in=courses).count()
    
    # Get student engagement metrics - modified approach to fix the error
    enrolled_students = Enrollment.objects.filter(
        course__in=courses
    ).values('student').distinct()
    
    student_engagement = []
    for student_dict in enrolled_students:
        student_id = student_dict['student']
        student_obj = User.objects.get(id=student_id)
        
        # Get attendance data
        total_attendances = SessionAttendance.objects.filter(
            student_id=student_id, 
            session__course__in=courses
        ).count()
        
        if total_attendances > 0:
            present_count = SessionAttendance.objects.filter(
                student_id=student_id,
                session__course__in=courses,
                status__in=['present', 'late']
            ).count()
            attendance_rate = (present_count / total_attendances) * 100
        else:
            attendance_rate = 0
        
        # Get progress data
        enrollments = Enrollment.objects.filter(
            student_id=student_id,
            course__in=courses
        )
        
        progress_sum = 0
        progress_count = 0
        last_active = None
        
        for enrollment in enrollments:
            try:
                progress = CourseProgress.objects.get(enrollment=enrollment)
                progress_sum += progress.completion_percentage
                progress_count += 1
                
                if last_active is None or (progress.last_accessed and progress.last_accessed > last_active):
                    last_active = progress.last_accessed
            except CourseProgress.DoesNotExist:
                pass
        
        avg_progress = progress_sum / max(progress_count, 1)
        
        student_engagement.append({
            'student': student_id,
            'student__username': student_obj.username,
            'attendance_rate': attendance_rate,
            'progress': avg_progress,
            'last_active': last_active
        })
    
    # Sort by progress (descending)
    student_engagement = sorted(student_engagement, key=lambda x: x['progress'], reverse=True)
    
    # Calculate average metrics
    if student_engagement:
        avg_attendance = sum(item['attendance_rate'] for item in student_engagement) / len(student_engagement)
        avg_progress = sum(item['progress'] for item in student_engagement) / len(student_engagement)
    else:
        avg_attendance = 0
        avg_progress = 0
    
    # Get trending courses based on enrollment growth
    now = timezone.now()
    month_ago = now - timedelta(days=30)
    
    trending_courses = []
    for course in courses:
        new_enrollments = Enrollment.objects.filter(
            course=course,
            enrollment_date__gte=month_ago
        ).count()
        
        trending_courses.append({
            'id': course.id,
            'title': course.title,
            'new_enrollments': new_enrollments
        })
    
    # Sort by new enrollments (descending)
    trending_courses = sorted(trending_courses, key=lambda x: x['new_enrollments'], reverse=True)[:5]
    
    # Get at-risk students (low progress, low attendance)
    at_risk_students = []
    for item in student_engagement:
        if item['progress'] < 30 or item['attendance_rate'] < 60:
            at_risk_students.append(item)
    
    at_risk_students = at_risk_students[:10]  # Limit to top 10
    
    # Prepare data for charts
    course_stats = []
    for course in courses:
        enrollments = Enrollment.objects.filter(course=course).count()
        
        # Calculate completion rate manually
        completion_sum = 0
        completion_count = 0
        
        for enrollment in Enrollment.objects.filter(course=course):
            try:
                progress = CourseProgress.objects.get(enrollment=enrollment)
                completion_sum += progress.completion_percentage
                completion_count += 1
            except CourseProgress.DoesNotExist:
                pass
        
        completion_rate = completion_sum / max(completion_count, 1)
        
        course_stats.append({
            'title': course.title,
            'students': enrollments,
            'completion_rate': completion_rate,
            'sessions': Session.objects.filter(course=course).count()
        })
    
    context = {
        'total_students': total_students,
        'total_courses': courses.count(),
        'total_sessions': total_sessions,
        'avg_attendance': avg_attendance,
        'avg_progress': avg_progress,
        'trending_courses': trending_courses,
        'at_risk_students': at_risk_students,
        'course_stats': course_stats
    }
    
    return render(request, 'analytics/educator_dashboard/main.html', context)

@login_required
@user_passes_test(is_educator)
def student_performance_analysis(request, student_id=None):
    """
    Detailed analysis of an individual student's performance across all courses.
    """
    # Verify the teacher has access to this student
    if student_id:
        student = get_object_or_404(User, id=student_id)
        # Ensure the teacher has this student in one of their courses
        has_access = Enrollment.objects.filter(
            student=student,
            course__teacher=request.user
        ).exists()
        
        if not has_access:
            return redirect('educator_analytics_dashboard')
    else:
        # Get the first student from teacher's courses
        enrollment = Enrollment.objects.filter(
            course__teacher=request.user
        ).first()
        
        if enrollment:
            student = enrollment.student
        else:
            return redirect('educator_analytics_dashboard')
    
    # Get student's profile information
    try:
        profile = Profile.objects.get(user=student)
    except Profile.DoesNotExist:
        profile = None
    except NameError:
        # Profile model might not exist
        profile = None
    
    # Get enrollment data for courses taught by this teacher
    enrollments = Enrollment.objects.filter(
        student=student,
        course__teacher=request.user
    ).select_related('course')
    
    # Get attendance data
    attendance = SessionAttendance.objects.filter(
        student=student,
        session__course__teacher=request.user
    ).values('status').annotate(count=Count('status'))
    
    # Calculate attendance statistics
    attendance_stats = {
        'present': 0,
        'absent': 0,
        'excused': 0,
        'late': 0,
    }
    
    for item in attendance:
        status = item['status']
        if status in attendance_stats:
            attendance_stats[status] = item['count']
    
    total_sessions = sum(attendance_stats.values())
    attendance_rate = 0
    if total_sessions > 0:
        attendance_rate = (attendance_stats['present'] + attendance_stats['late']) / total_sessions * 100
    
    # Get achievements
    try:
        achievements = Achievement.objects.filter(student=student)
    except NameError:
        # Achievement model might not exist
        achievements = []
    
    # Prepare enrollment data for charts
    courses_data = []
    for enrollment in enrollments:
        try:
            progress = CourseProgress.objects.get(enrollment=enrollment)
            completion = progress.completion_percentage
            last_accessed = progress.last_accessed
        except CourseProgress.DoesNotExist:
            completion = 0
            last_accessed = None
        
        courses_data.append({
            'course': enrollment.course.title,
            'progress': completion,
            'enrollment_date': enrollment.enrollment_date,
            'last_accessed': last_accessed
        })
    
    context = {
        'student': student,
        'profile': profile,
        'enrollments': enrollments,
        'attendance_stats': attendance_stats,
        'attendance_rate': attendance_rate,
        'achievements': achievements,
        'courses_data': courses_data
    }
    
    return render(request, 'analytics/educator_dashboard/student_performance.html', context)

@login_required
@user_passes_test(is_educator)
def course_insights(request, course_id):
    """
    Detailed insights for a specific course, including student performance and engagement.
    """
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    
    # Get enrollments for this course
    enrollments = Enrollment.objects.filter(course=course).select_related('student')
    
    # Calculate average progress manually
    progress_sum = 0
    progress_count = 0
    
    for enrollment in enrollments:
        try:
            progress = CourseProgress.objects.get(enrollment=enrollment)
            progress_sum += progress.completion_percentage
            progress_count += 1
        except CourseProgress.DoesNotExist:
            pass
    
    avg_progress = progress_sum / max(progress_count, 1)
    
    # Get session attendance statistics
    session_data = []
    for session in course.sessions.all():
        attendances = SessionAttendance.objects.filter(session=session)
        total = attendances.count()
        present = attendances.filter(status__in=['present', 'late']).count()
        attendance_rate = (present / total * 100) if total > 0 else 0
        
        session_data.append({
            'title': session.title,
            'date': session.start_time,
            'attendance_rate': attendance_rate,
            'total_students': total,
            'present_count': present
        })
    
    # Get student performance data
    student_progress = []
    for enrollment in enrollments:
        try:
            progress = CourseProgress.objects.get(enrollment=enrollment)
            completion = progress.completion_percentage
            last_accessed = progress.last_accessed
        except CourseProgress.DoesNotExist:
            completion = 0
            last_accessed = None
        
        student_progress.append({
            'student': enrollment.student,
            'progress': completion,
            'last_accessed': last_accessed
        })
    
    # Sort by progress
    student_progress.sort(key=lambda x: x['progress'])
    
    # Identify quartiles if we have enough students
    quartiles = {}
    if len(student_progress) >= 4:
        q_size = len(student_progress) // 4
        quartiles = {
            'q1': student_progress[:q_size],  # Bottom 25%
            'q2': student_progress[q_size:q_size*2],
            'q3': student_progress[q_size*2:q_size*3],
            'q4': student_progress[q_size*3:]  # Top 25%
        }
    
    context = {
        'course': course,
        'enrollments': enrollments,
        'avg_progress': avg_progress,
        'session_data': session_data,
        'student_progress': student_progress,
        'quartiles': quartiles
    }
    
    return render(request, 'analytics/educator_dashboard/course_insights.html', context)

@login_required
@user_passes_test(is_educator)
def learning_patterns_analysis(request):
    """
    Analysis of student learning patterns across courses.
    """
    # Get all courses taught by this educator
    courses = Course.objects.filter(teacher=request.user)
    
    # Get filter parameters
    course_id = request.GET.get('course_id')
    days = int(request.GET.get('days', 30))
    
    # Get learning patterns data
    patterns_data = analyze_learning_patterns(course_id=course_id, days=days)
    
    context = {
        'courses': courses,
        'peak_activity_hour': patterns_data['peak_activity_hour'],
        'avg_study_duration': patterns_data['avg_study_duration'],
        'popular_days': patterns_data['popular_days'],
        'hourly_distribution': patterns_data['hourly_distribution'],
        'weekly_activity': patterns_data['weekly_activity']
    }
    
    return render(request, 'analytics/educator_dashboard/learning_patterns.html', context)