# web/analytics/prediction.py

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from django.contrib.auth.models import User
from django.utils import timezone

from web.models import Course, CourseProgress, Enrollment, Session, SessionAttendance


class StudentPerformancePredictor:
    """
    AI-based predictor for student performance and completion probability.
    In a real implementation, this would use trained ML models.
    """

    def __init__(self):
        """Initialize the predictor with default parameters."""
        # These would be loaded from a trained model in production
        self.attendance_weight = 0.4
        self.progress_weight = 0.3
        self.engagement_weight = 0.2
        self.time_spent_weight = 0.1

    def predict_completion_date(self, student, course):
        """
        Predict when a student will complete a course based on their current progress rate.

        Args:
            student: User object
            course: Course object

        Returns:
            predicted_date: datetime object representing estimated completion date
            confidence: float between 0-1 indicating prediction confidence
        """
        # Get enrollment and progress data
        try:
            enrollment = Enrollment.objects.get(student=student, course=course)
            progress = CourseProgress.objects.get(enrollment=enrollment)

            # If no progress yet, return None
            if progress.completion_percentage == 0:
                return None, 0.0

            # Calculate average progress per day
            days_enrolled = (timezone.now() - enrollment.enrollment_date).days
            if days_enrolled < 1:
                days_enrolled = 1

            progress_per_day = progress.completion_percentage / days_enrolled

            # Estimate remaining days
            remaining_progress = 100 - progress.completion_percentage
            if progress_per_day > 0:
                days_remaining = remaining_progress / progress_per_day
            else:
                # If no progress yet, estimate based on course average
                avg_progress_per_day = 1.5  # Default assumption
                days_remaining = remaining_progress / avg_progress_per_day

            predicted_date = timezone.now() + timedelta(days=days_remaining)

            # Calculate confidence based on consistency of progress
            # In a real implementation, this would use more sophisticated methods
            consistency_score = min(days_enrolled / 14, 1.0)  # Higher for students enrolled longer
            progress_variability = 0.8  # Placeholder - would be calculated from actual data
            confidence = consistency_score * progress_variability

            return predicted_date, confidence

        except (Enrollment.DoesNotExist, CourseProgress.DoesNotExist):
            return None, 0.0

    def predict_risk_level(self, student, course):
        """
        Predict the risk level of a student not completing a course.

        Args:
            student: User object
            course: Course object

        Returns:
            risk_level: string ('low', 'medium', 'high')
            risk_factors: list of contributing factors
        """
        risk_factors = []
        risk_score = 50  # Neutral starting point

        try:
            # Get enrollment data
            enrollment = Enrollment.objects.get(student=student, course=course)

            # Check progress
            progress = CourseProgress.objects.get(enrollment=enrollment)
            if progress.completion_percentage < 30:
                risk_score += 20
                risk_factors.append("Low completion progress")
            elif progress.completion_percentage > 70:
                risk_score -= 20

            # Check attendance
            attendance_count = SessionAttendance.objects.filter(
                student=student, session__course=course, status__in=["present", "late"]
            ).count()

            total_past_sessions = Session.objects.filter(course=course, start_time__lt=timezone.now()).count()

            if total_past_sessions > 0:
                attendance_rate = (attendance_count / total_past_sessions) * 100
                if attendance_rate < 60:
                    risk_score += 15
                    risk_factors.append("Poor attendance")
                elif attendance_rate > 80:
                    risk_score -= 15

            # Check last activity
            if progress.last_accessed:
                days_since_access = (timezone.now() - progress.last_accessed).days
                if days_since_access > 14:
                    risk_score += 15
                    risk_factors.append("Inactive for 2+ weeks")
                elif days_since_access < 3:
                    risk_score -= 10

            # Determine risk level based on score
            if risk_score >= 70:
                return "high", risk_factors
            elif risk_score >= 40:
                return "medium", risk_factors
            else:
                return "low", risk_factors

        except (Enrollment.DoesNotExist, CourseProgress.DoesNotExist):
            return "high", ["No enrollment or progress data"]

    def generate_personalized_recommendations(self, student, courses=None):
        """
        Generate personalized recommendations for a student based on their performance.

        Args:
            student: User object
            courses: Optional list of Course objects to limit recommendations

        Returns:
            recommendations: list of recommendation dictionaries
        """
        recommendations = []

        # Get student's enrollments
        if courses:
            enrollments = Enrollment.objects.filter(student=student, course__in=courses)
        else:
            enrollments = Enrollment.objects.filter(student=student)

        for enrollment in enrollments:
            course = enrollment.course

            # Get progress data
            try:
                progress = CourseProgress.objects.get(enrollment=enrollment)

                # Recommendation for low progress
                if progress.completion_percentage < 30:
                    recommendations.append(
                        {
                            "type": "progress",
                            "course": course.title,
                            "message": f"Your progress in {course.title} is below 30%. Consider setting aside dedicated time to catch up.",
                            "priority": "high",
                        }
                    )

                # Recommendation for inactive students
                if progress.last_accessed and (timezone.now() - progress.last_accessed).days > 7:
                    recommendations.append(
                        {
                            "type": "engagement",
                            "course": course.title,
                            "message": f"You haven't accessed {course.title} in over a week. Regular engagement helps with retention.",
                            "priority": "medium",
                        }
                    )

            except CourseProgress.DoesNotExist:
                continue

            # Attendance recommendations
            attendance_count = SessionAttendance.objects.filter(
                student=student, session__course=course, status__in=["present", "late"]
            ).count()

            total_past_sessions = Session.objects.filter(course=course, start_time__lt=timezone.now()).count()

            if total_past_sessions > 0:
                attendance_rate = (attendance_count / total_past_sessions) * 100
                if attendance_rate < 70:
                    recommendations.append(
                        {
                            "type": "attendance",
                            "course": course.title,
                            "message": f"Your attendance in {course.title} is {attendance_rate:.0f}%. Try to attend more sessions to improve understanding.",
                            "priority": "high" if attendance_rate < 50 else "medium",
                        }
                    )

        # Limit to top 5 recommendations
        return sorted(recommendations, key=lambda x: x["priority"] == "high", reverse=True)[:5]


def predict_student_outcomes(course):
    """
    Predict outcomes for all students enrolled in a course.

    Args:
        course: Course object

    Returns:
        predictions: dict mapping student IDs to prediction results
    """
    predictor = StudentPerformancePredictor()
    predictions = {}

    enrollments = Enrollment.objects.filter(course=course)

    for enrollment in enrollments:
        student = enrollment.student

        # Predict completion date
        completion_date, completion_confidence = predictor.predict_completion_date(student, course)

        # Predict risk level
        risk_level, risk_factors = predictor.predict_risk_level(student, course)

        # Generate recommendations
        recommendations = predictor.generate_personalized_recommendations(student, [course])

        predictions[student.id] = {
            "student_name": student.get_full_name() or student.username,
            "completion_date": completion_date,
            "confidence": completion_confidence,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "recommendations": recommendations,
        }

    return predictions
