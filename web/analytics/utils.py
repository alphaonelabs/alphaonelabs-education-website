# web/analytics/utils.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Sum, F, ExpressionWrapper, fields
from django.db.models.functions import TruncHour, TruncDay, TruncWeek
from web.models import (
    Course, Session, Enrollment, CourseProgress, 
    SessionAttendance, User
)

def calculate_student_progress_statistics(course):
    """
    Calculate statistics about student progress for a specific course.
    
    Args:
        course: Course object
        
    Returns:
        Dictionary containing various statistics
    """
    progress_data = CourseProgress.objects.filter(
        enrollment__course=course
    ).values('completion_percentage')
    
    if not progress_data:
        return {
            'avg_progress': 0,
            'median_progress': 0,
            'stddev_progress': 0,
            'quartiles': [],
            'distribution': []
        }
    
    # Convert to pandas DataFrame for easier statistical analysis
    df = pd.DataFrame(progress_data)
    
    # Calculate statistics
    avg_progress = df['completion_percentage'].mean()
    median_progress = df['completion_percentage'].median()
    stddev_progress = df['completion_percentage'].std()
    
    # Calculate quartiles
    quartiles = [
        df['completion_percentage'].quantile(0.25),
        df['completion_percentage'].quantile(0.5),
        df['completion_percentage'].quantile(0.75)
    ]
    
    # Create distribution bins
    bins = list(range(0, 101, 10))  # 0-10, 10-20, ..., 90-100
    bin_labels = [f"{i}-{i+10}%" for i in range(0, 100, 10)]
    
    df['bin'] = pd.cut(df['completion_percentage'], bins=bins, labels=bin_labels, right=False)
    distribution = df.groupby('bin').size().reset_index(name='count')
    distribution = {row['bin']: row['count'] for _, row in distribution.iterrows()}
    
    return {
        'avg_progress': avg_progress,
        'median_progress': median_progress,
        'stddev_progress': stddev_progress,
        'quartiles': quartiles,
        'distribution': distribution
    }

def calculate_attendance_statistics(course):
    """
    Calculate statistics about attendance for a specific course.
    
    Args:
        course: Course object
        
    Returns:
        Dictionary containing various attendance statistics
    """
    sessions = Session.objects.filter(course=course)
    
    if not sessions:
        return {
            'avg_attendance_rate': 0,
            'sessions_data': [],
            'attendance_trend': []
        }
    
    sessions_data = []
    for session in sessions:
        total_students = Enrollment.objects.filter(course=course).count()
        attendances = SessionAttendance.objects.filter(session=session)
        present_count = attendances.filter(status__in=['present', 'late']).count()
        
        if total_students > 0:
            attendance_rate = (present_count / total_students) * 100
        else:
            attendance_rate = 0
            
        sessions_data.append({
            'id': session.id,
            'title': session.title,
            'date': session.start_time,
            'total_students': total_students,
            'present_count': present_count,
            'attendance_rate': attendance_rate
        })
    
    # Calculate average attendance rate
    if sessions_data:
        avg_attendance_rate = sum(s['attendance_rate'] for s in sessions_data) / len(sessions_data)
    else:
        avg_attendance_rate = 0
    
    # Sort sessions by date for trend analysis
    sessions_data.sort(key=lambda x: x['date'])
    attendance_trend = [(s['date'], s['attendance_rate']) for s in sessions_data]
    
    return {
        'avg_attendance_rate': avg_attendance_rate,
        'sessions_data': sessions_data,
        'attendance_trend': attendance_trend
    }

def analyze_learning_patterns(user_ids=None, course_id=None, days=30):
    """
    Analyze learning patterns for students.
    
    Args:
        user_ids: Optional list of user IDs to filter by
        course_id: Optional course ID to filter by
        days: Number of days to look back
        
    Returns:
        Dictionary containing various learning pattern insights
    """
    # This is a simplified implementation that would use actual tracking data in production
    # In a real implementation, you would have a user activity tracking model
    
    start_date = timezone.now() - timedelta(days=days)
    
    # Filter by users if provided
    user_filter = {}
    if user_ids:
        user_filter['student__in'] = user_ids
    
    # Filter by course if provided
    course_filter = {}
    if course_id:
        course_filter['enrollment__course__id'] = course_id
    
    # Get progress updates as proxy for activity
    activity_logs = CourseProgress.objects.filter(
        updated_at__gte=start_date,
        **user_filter,
        **course_filter
    )
    
    # Analyze activity by hour of day
    hourly_activity = (
        activity_logs
        .annotate(hour=TruncHour('updated_at'))
        .values('hour')
        .annotate(count=Count('id'))
        .order_by('hour')
    )
    
    hourly_distribution = {}
    for entry in hourly_activity:
        hour = entry['hour'].hour
        hourly_distribution[hour] = entry['count']
    
    # Fill in missing hours
    for hour in range(24):
        if hour not in hourly_distribution:
            hourly_distribution[hour] = 0
    
    # Find peak activity hour
    if hourly_distribution:
        peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])[0]
    else:
        peak_hour = None
    
    # Analyze activity by day of week
    daily_activity = (
        activity_logs
        .annotate(day=TruncDay('updated_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    
    day_of_week_map = {
        0: 'Monday',
        1: 'Tuesday',
        2: 'Wednesday',
        3: 'Thursday',
        4: 'Friday',
        5: 'Saturday',
        6: 'Sunday'
    }
    
    day_distribution = {day: 0 for day in range(7)}
    for entry in daily_activity:
        day = entry['day'].weekday()
        day_distribution[day] = entry['count']
    
    # Find most active days
    if day_distribution:
        # Get the top 2 most active days
        sorted_days = sorted(day_distribution.items(), key=lambda x: x[1], reverse=True)
        popular_days = [day_of_week_map[day] for day, _ in sorted_days[:2]]
    else:
        popular_days = []
    
    # Calculate average study session duration
    # This is a placeholder - in a real implementation you would track session start/end times
    avg_study_duration = 45  # minutes, placeholder value
    
    # Calculate weekly pattern
    weekly_activity = {}
    for day, count in day_distribution.items():
        weekly_activity[day_of_week_map[day]] = count
    
    # Calculate total activity percentage by day of week
    total_activity = sum(weekly_activity.values())
    if total_activity > 0:
        for day in weekly_activity:
            weekly_activity[day] = (weekly_activity[day] / total_activity) * 100
    
    return {
        'hourly_distribution': hourly_distribution,
        'peak_activity_hour': peak_hour,
        'popular_days': popular_days,
        'avg_study_duration': avg_study_duration,
        'weekly_activity': weekly_activity
    }

def analyze_content_engagement(course_id=None, days=30):
    """
    Analyze engagement levels with different types of content.
    
    Args:
        course_id: Optional course ID to filter by
        days: Number of days to look back
        
    Returns:
        Dictionary containing engagement metrics by content type
    """
    # This is a simplified implementation - in a real app you would track content views
    # Placeholder data - would be replaced with real metrics in production
    
    content_types = [
        {'type': 'Video Tutorials', 'engagement': 86, 'avg_time': 8.2},
        {'type': 'Interactive Exercises', 'engagement': 92, 'avg_time': 12.5},
        {'type': 'Quizzes', 'engagement': 72, 'avg_time': 6.8},
        {'type': 'Text Articles', 'engagement': 45, 'avg_time': 4.2},
        {'type': 'PDF Documents', 'engagement': 38, 'avg_time': 3.5},
        {'type': 'Discussion Forums', 'engagement': 65, 'avg_time': 7.3},
        {'type': 'Project Tasks', 'engagement': 78, 'avg_time': 15.6},
        {'type': 'External Links', 'engagement': 32, 'avg_time': 2.8}
    ]
    
    # Sort by engagement level
    most_engaging = sorted(content_types, key=lambda x: x['engagement'], reverse=True)
    least_engaging = sorted(content_types, key=lambda x: x['engagement'])
    
    return {
        'content_types': content_types,
        'most_engaging': most_engaging[:3],  # Top 3
        'least_engaging': least_engaging[:3]  # Bottom 3
    }

def get_student_segmentation(course_id=None):
    """
    Segment students based on their learning patterns and performance.
    
    Args:
        course_id: Optional course ID to filter by
        
    Returns:
        Dictionary containing student segments
    """
    # In a real implementation, you would analyze actual student data
    # This is a simplified placeholder implementation
    
    # Filter by course if provided
    course_filter = {}
    if course_id:
        course_filter['enrollment__course__id'] = course_id
    
    # Get all progress data
    progress_data = CourseProgress.objects.filter(**course_filter)
    
    # Calculate segments
    if not progress_data:
        return {
            'segments': []
        }
    
    # Would use clustering algorithms in a real implementation
    # Simplified manual segmentation based on completion percentage
    segments = [
        {
            'name': 'Top Performers',
            'criteria': 'completion_percentage__gte',
            'value': 80,
            'count': progress_data.filter(completion_percentage__gte=80).count(),
            'avg_progress': progress_data.filter(completion_percentage__gte=80).aggregate(avg=Avg('completion_percentage'))['avg'] or 0,
            'avg_weekly_hours': 5.2  # Placeholder
        },
        {
            'name': 'Average Students',
            'criteria': 'completion_percentage__range',
            'value': [50, 79],
            'count': progress_data.filter(completion_percentage__range=[50, 79]).count(),
            'avg_progress': progress_data.filter(completion_percentage__range=[50, 79]).aggregate(avg=Avg('completion_percentage'))['avg'] or 0,
            'avg_weekly_hours': 3.5  # Placeholder
        },
        {
            'name': 'Struggling Students',
            'criteria': 'completion_percentage__lt',
            'value': 50,
            'count': progress_data.filter(completion_percentage__lt=50).count(),
            'avg_progress': progress_data.filter(completion_percentage__lt=50).aggregate(avg=Avg('completion_percentage'))['avg'] or 0,
            'avg_weekly_hours': 1.8  # Placeholder
        }
    ]
    
    return {
        'segments': segments
    }