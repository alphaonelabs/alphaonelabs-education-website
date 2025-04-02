import csv
import io
import json
from datetime import datetime

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from web.models import Achievement, Course, CourseProgress, Enrollment, Session, SessionAttendance, User

from .utils import analyze_learning_patterns, calculate_attendance_statistics, calculate_student_progress_statistics


def export_csv(request, analytics_type, obj_id=None):
    """
    Export analytics data as CSV.

    Args:
        request: HttpRequest object
        analytics_type: Type of analytics ('course', 'student', or 'learning_patterns')
        obj_id: ID of the object (course or student)

    Returns:
        HttpResponse with CSV attachment
    """
    response = HttpResponse(content_type="text/csv")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if analytics_type == "course":
        course = Course.objects.get(id=obj_id)
        response["Content-Disposition"] = f'attachment; filename="course_analytics_{course.id}_{timestamp}.csv"'
        writer = csv.writer(response)

        # Write header information
        writer.writerow(["Course Analytics Report"])
        writer.writerow(["Course", course.title])
        writer.writerow(["Instructor", course.teacher.get_full_name() or course.teacher.username])
        writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow([])

        # Write enrollment data
        enrollments = Enrollment.objects.filter(course=course)
        writer.writerow(["Total Enrollments", enrollments.count()])
        writer.writerow([])

        # Write progress statistics
        progress_stats = calculate_student_progress_statistics(course)
        writer.writerow(["Progress Statistics"])
        writer.writerow(["Average Progress", f"{progress_stats['avg_progress']:.2f}%"])
        writer.writerow(["Median Progress", f"{progress_stats['median_progress']:.2f}%"])
        writer.writerow(["Standard Deviation", f"{progress_stats['stddev_progress']:.2f}%"])
        writer.writerow([])

        # Write progress distribution
        writer.writerow(["Progress Distribution"])
        writer.writerow(["Range", "Number of Students"])
        for bin_range, count in progress_stats["distribution"].items():
            writer.writerow([bin_range, count])
        writer.writerow([])

        # Write student progress data
        writer.writerow(["Student Progress"])
        writer.writerow(["Student", "Progress", "Last Activity", "Attendance Rate"])

        for enrollment in enrollments:
            progress = CourseProgress.objects.filter(enrollment=enrollment).first()
            attendance_count = SessionAttendance.objects.filter(
                student=enrollment.student, session__course=course, status__in=["present", "late"]
            ).count()

            total_sessions = Session.objects.filter(course=course).count()
            attendance_rate = (attendance_count / total_sessions * 100) if total_sessions > 0 else 0

            writer.writerow(
                [
                    enrollment.student.username,
                    f"{progress.completion_percentage:.2f}%" if progress else "0%",
                    progress.last_accessed.strftime("%Y-%m-%d") if progress and progress.last_accessed else "N/A",
                    f"{attendance_rate:.2f}%",
                ]
            )

    elif analytics_type == "student":
        student = User.objects.get(id=obj_id)
        response["Content-Disposition"] = f'attachment; filename="student_analytics_{student.username}_{timestamp}.csv"'
        writer = csv.writer(response)

        # Write header information
        writer.writerow(["Student Analytics Report"])
        writer.writerow(["Student", student.get_full_name() or student.username])
        writer.writerow(["Email", student.email])
        writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow([])

        # Write course enrollment data
        enrollments = Enrollment.objects.filter(student=student)
        writer.writerow(["Course Enrollments"])
        writer.writerow(["Course", "Enrollment Date", "Progress", "Last Activity"])

        for enrollment in enrollments:
            progress = CourseProgress.objects.filter(enrollment=enrollment).first()
            writer.writerow(
                [
                    enrollment.course.title,
                    enrollment.enrollment_date.strftime("%Y-%m-%d"),
                    f"{progress.completion_percentage:.2f}%" if progress else "0%",
                    progress.last_accessed.strftime("%Y-%m-%d") if progress and progress.last_accessed else "N/A",
                ]
            )
        writer.writerow([])

        # Write attendance data
        writer.writerow(["Attendance Statistics"])
        writer.writerow(["Course", "Present", "Late", "Excused", "Absent", "Attendance Rate"])

        for enrollment in enrollments:
            course = enrollment.course
            attendances = SessionAttendance.objects.filter(student=student, session__course=course)

            present = attendances.filter(status="present").count()
            late = attendances.filter(status="late").count()
            excused = attendances.filter(status="excused").count()
            absent = attendances.filter(status="absent").count()

            total_sessions = Session.objects.filter(course=course).count()
            attendance_rate = ((present + late) / total_sessions * 100) if total_sessions > 0 else 0

            writer.writerow([course.title, present, late, excused, absent, f"{attendance_rate:.2f}%"])

    elif analytics_type == "learning_patterns":
        # Handle optional filtering
        course_id = request.GET.get("course_id")
        days = int(request.GET.get("days", 30))

        filename = "learning_patterns"
        if course_id:
            course = Course.objects.get(id=course_id)
            filename += f"_{course.id}"

        response["Content-Disposition"] = f'attachment; filename="{filename}_{timestamp}.csv"'
        writer = csv.writer(response)

        # Write header information
        writer.writerow(["Learning Patterns Analytics Report"])
        writer.writerow(["Period", f"Last {days} days"])
        if course_id:
            writer.writerow(["Course", course.title])
        writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow([])

        # Get learning patterns data
        patterns_data = analyze_learning_patterns(course_id=course_id, days=days)

        # Write key insights
        writer.writerow(["Key Insights"])
        writer.writerow(["Peak Activity Hour", f"{patterns_data['peak_activity_hour']}:00"])
        writer.writerow(["Average Study Duration", f"{patterns_data['avg_study_duration']} minutes"])
        writer.writerow(["Most Popular Days", ", ".join(patterns_data["popular_days"])])
        writer.writerow([])

        # Write hourly activity distribution
        writer.writerow(["Hourly Activity Distribution"])
        writer.writerow(["Hour", "Activity Level"])

        for hour, count in patterns_data["hourly_distribution"].items():
            writer.writerow([f"{hour}:00", count])
        writer.writerow([])

        # Write weekly activity distribution
        writer.writerow(["Weekly Activity Distribution"])
        writer.writerow(["Day", "Activity Percentage"])

        for day, percentage in patterns_data["weekly_activity"].items():
            writer.writerow([day, f"{percentage:.2f}%"])

    return response


def export_pdf(request, analytics_type, obj_id=None):
    """
    Export analytics data as PDF report.

    Args:
        request: HttpRequest object
        analytics_type: Type of analytics ('course', 'student', or 'learning_patterns')
        obj_id: ID of the object (course or student)

    Returns:
        HttpResponse with PDF attachment
    """
    buffer = io.BytesIO()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create the PDF document
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Define styles
    title_style = styles["Title"]
    heading1_style = styles["Heading1"]
    heading2_style = styles["Heading2"]
    normal_style = styles["Normal"]

    # Define table style
    table_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
            ("ALIGN", (0, 1), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
    )

    if analytics_type == "course":
        course = Course.objects.get(id=obj_id)

        # Add title
        elements.append(Paragraph(f"Course Analytics Report: {course.title}", title_style))
        elements.append(Spacer(1, 0.25 * inch))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        elements.append(Spacer(1, 0.5 * inch))

        # Course Information
        elements.append(Paragraph("Course Information", heading1_style))
        course_info = [
            ["Course", course.title],
            ["Instructor", course.teacher.get_full_name() or course.teacher.username],
            ["Total Enrollments", str(Enrollment.objects.filter(course=course).count())],
        ]

        info_table = Table(course_info, colWidths=[2 * inch, 4 * inch])
        info_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("ALIGNMENT", (0, 0), (0, -1), "LEFT"),
                    ("ALIGNMENT", (1, 0), (1, -1), "LEFT"),
                ]
            )
        )
        elements.append(info_table)
        elements.append(Spacer(1, 0.25 * inch))

        # Progress Statistics
        progress_stats = calculate_student_progress_statistics(course)
        elements.append(Paragraph("Progress Statistics", heading1_style))

        elements.append(Paragraph(f"Average Progress: {progress_stats['avg_progress']:.2f}%", normal_style))
        elements.append(Paragraph(f"Median Progress: {progress_stats['median_progress']:.2f}%", normal_style))
        elements.append(Paragraph(f"Standard Deviation: {progress_stats['stddev_progress']:.2f}%", normal_style))
        elements.append(Spacer(1, 0.25 * inch))

        # Student Progress Table
        elements.append(Paragraph("Student Progress", heading1_style))

        students_data = [["Student", "Progress", "Last Activity", "Attendance Rate"]]
        enrollments = Enrollment.objects.filter(course=course)

        for enrollment in enrollments:
            progress = CourseProgress.objects.filter(enrollment=enrollment).first()
            attendance_count = SessionAttendance.objects.filter(
                student=enrollment.student, session__course=course, status__in=["present", "late"]
            ).count()

            total_sessions = Session.objects.filter(course=course).count()
            attendance_rate = (attendance_count / total_sessions * 100) if total_sessions > 0 else 0

            students_data.append(
                [
                    enrollment.student.username,
                    f"{progress.completion_percentage:.2f}%" if progress else "0%",
                    progress.last_accessed.strftime("%Y-%m-%d") if progress and progress.last_accessed else "N/A",
                    f"{attendance_rate:.2f}%",
                ]
            )

        students_table = Table(students_data, colWidths=[1.5 * inch, 1.5 * inch, 2 * inch, 1.5 * inch])
        students_table.setStyle(table_style)
        elements.append(students_table)

    elif analytics_type == "student":
        student = User.objects.get(id=obj_id)

        # Add title
        elements.append(
            Paragraph(f"Student Analytics Report: {student.get_full_name() or student.username}", title_style)
        )
        elements.append(Spacer(1, 0.25 * inch))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        elements.append(Spacer(1, 0.5 * inch))

        # Student Information
        elements.append(Paragraph("Student Information", heading1_style))
        student_info = [
            ["Name", student.get_full_name() or student.username],
            ["Email", student.email],
            ["Total Courses", str(Enrollment.objects.filter(student=student).count())],
        ]

        info_table = Table(student_info, colWidths=[2 * inch, 4 * inch])
        info_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("ALIGNMENT", (0, 0), (0, -1), "LEFT"),
                    ("ALIGNMENT", (1, 0), (1, -1), "LEFT"),
                ]
            )
        )
        elements.append(info_table)
        elements.append(Spacer(1, 0.25 * inch))

        # Course Progress
        elements.append(Paragraph("Course Progress", heading1_style))

        course_data = [["Course", "Enrollment Date", "Progress", "Last Activity"]]
        enrollments = Enrollment.objects.filter(student=student)

        for enrollment in enrollments:
            progress = CourseProgress.objects.filter(enrollment=enrollment).first()
            course_data.append(
                [
                    enrollment.course.title,
                    enrollment.enrollment_date.strftime("%Y-%m-%d"),
                    f"{progress.completion_percentage:.2f}%" if progress else "0%",
                    progress.last_accessed.strftime("%Y-%m-%d") if progress and progress.last_accessed else "N/A",
                ]
            )

        if len(course_data) > 1:  # Only add table if there are courses
            course_table = Table(course_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
            course_table.setStyle(table_style)
            elements.append(course_table)
        else:
            elements.append(Paragraph("No courses enrolled.", normal_style))

        elements.append(Spacer(1, 0.25 * inch))

        # Attendance Statistics
        elements.append(Paragraph("Attendance Statistics", heading1_style))

        if enrollments:
            attendance_data = [["Course", "Present", "Late", "Excused", "Absent", "Rate"]]

            for enrollment in enrollments:
                course = enrollment.course
                attendances = SessionAttendance.objects.filter(student=student, session__course=course)

                present = attendances.filter(status="present").count()
                late = attendances.filter(status="late").count()
                excused = attendances.filter(status="excused").count()
                absent = attendances.filter(status="absent").count()

                total_sessions = Session.objects.filter(course=course).count()
                attendance_rate = ((present + late) / total_sessions * 100) if total_sessions > 0 else 0

                attendance_data.append(
                    [course.title, str(present), str(late), str(excused), str(absent), f"{attendance_rate:.2f}%"]
                )

            attendance_table = Table(
                attendance_data, colWidths=[1.5 * inch, 0.75 * inch, 0.75 * inch, 0.75 * inch, 0.75 * inch, 1 * inch]
            )
            attendance_table.setStyle(table_style)
            elements.append(attendance_table)
        else:
            elements.append(Paragraph("No attendance data available.", normal_style))

    elif analytics_type == "learning_patterns":
        # Handle optional filtering
        course_id = request.GET.get("course_id")
        days = int(request.GET.get("days", 30))

        # Add title
        title = "Learning Patterns Analytics Report"
        if course_id:
            course = Course.objects.get(id=course_id)
            title += f": {course.title}"

        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 0.25 * inch))
        elements.append(Paragraph(f"Analysis Period: Last {days} days", normal_style))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        elements.append(Spacer(1, 0.5 * inch))

        # Get learning patterns data
        patterns_data = analyze_learning_patterns(course_id=course_id, days=days)

        # Key Insights
        elements.append(Paragraph("Key Insights", heading1_style))
        key_insights = [
            ["Peak Activity Hour", f"{patterns_data['peak_activity_hour']}:00"],
            ["Average Study Duration", f"{patterns_data['avg_study_duration']} minutes"],
            ["Most Popular Days", ", ".join(patterns_data["popular_days"])],
        ]

        insights_table = Table(key_insights, colWidths=[2 * inch, 4 * inch])
        insights_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("ALIGNMENT", (0, 0), (0, -1), "LEFT"),
                    ("ALIGNMENT", (1, 0), (1, -1), "LEFT"),
                ]
            )
        )
        elements.append(insights_table)
        elements.append(Spacer(1, 0.25 * inch))

        # Hourly Activity Distribution
        elements.append(Paragraph("Hourly Activity Distribution", heading1_style))

        hourly_data = [["Hour", "Activity Level"]]
        for hour, count in patterns_data["hourly_distribution"].items():
            hourly_data.append([f"{hour}:00", str(count)])

        hourly_table = Table(hourly_data, colWidths=[2 * inch, 4 * inch])
        hourly_table.setStyle(table_style)
        elements.append(hourly_table)
        elements.append(Spacer(1, 0.25 * inch))

        # Weekly Activity Distribution
        elements.append(Paragraph("Weekly Activity Distribution", heading1_style))

        weekly_data = [["Day", "Activity Percentage"]]
        for day, percentage in patterns_data["weekly_activity"].items():
            weekly_data.append([day, f"{percentage:.2f}%"])

        weekly_table = Table(weekly_data, colWidths=[2 * inch, 4 * inch])
        weekly_table.setStyle(table_style)
        elements.append(weekly_table)

    # Build the PDF
    doc.build(elements)

    # Get PDF content and create response
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    filename = f"{analytics_type}_analytics_{timestamp}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write(pdf)

    return response


def export_json(request, analytics_type, obj_id=None):
    """
    Export analytics data as JSON.

    Args:
        request: HttpRequest object
        analytics_type: Type of analytics ('course', 'student', or 'learning_patterns')
        obj_id: ID of the object (course or student)

    Returns:
        HttpResponse with JSON attachment
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data = {}

    if analytics_type == "course":
        course = Course.objects.get(id=obj_id)

        # Course information
        data["course"] = {
            "id": course.id,
            "title": course.title,
            "instructor": course.teacher.get_full_name() or course.teacher.username,
            "enrollments_count": Enrollment.objects.filter(course=course).count(),
        }

        # Progress statistics
        progress_stats = calculate_student_progress_statistics(course)
        data["progress_statistics"] = {
            "avg_progress": progress_stats["avg_progress"],
            "median_progress": progress_stats["median_progress"],
            "stddev_progress": progress_stats["stddev_progress"],
            "distribution": progress_stats["distribution"],
        }

        # Student progress data
        students_data = []
        enrollments = Enrollment.objects.filter(course=course)

        for enrollment in enrollments:
            progress = CourseProgress.objects.filter(enrollment=enrollment).first()
            attendance_count = SessionAttendance.objects.filter(
                student=enrollment.student, session__course=course, status__in=["present", "late"]
            ).count()

            total_sessions = Session.objects.filter(course=course).count()
            attendance_rate = (attendance_count / total_sessions * 100) if total_sessions > 0 else 0

            students_data.append(
                {
                    "id": enrollment.student.id,
                    "username": enrollment.student.username,
                    "progress": progress.completion_percentage if progress else 0,
                    "last_accessed": (
                        progress.last_accessed.isoformat() if progress and progress.last_accessed else None
                    ),
                    "attendance_rate": attendance_rate,
                }
            )

        data["students"] = students_data

    elif analytics_type == "student":
        student = User.objects.get(id=obj_id)

        # Student information
        data["student"] = {
            "id": student.id,
            "username": student.username,
            "full_name": student.get_full_name(),
            "email": student.email,
            "courses_count": Enrollment.objects.filter(student=student).count(),
        }

        # Course progress data
        courses_data = []
        enrollments = Enrollment.objects.filter(student=student)

        for enrollment in enrollments:
            progress = CourseProgress.objects.filter(enrollment=enrollment).first()

            # Calculate attendance statistics
            attendances = SessionAttendance.objects.filter(student=student, session__course=enrollment.course)

            present = attendances.filter(status="present").count()
            late = attendances.filter(status="late").count()
            excused = attendances.filter(status="excused").count()
            absent = attendances.filter(status="absent").count()

            total_sessions = Session.objects.filter(course=enrollment.course).count()
            attendance_rate = ((present + late) / total_sessions * 100) if total_sessions > 0 else 0

            courses_data.append(
                {
                    "id": enrollment.course.id,
                    "title": enrollment.course.title,
                    "enrollment_date": enrollment.enrollment_date.isoformat(),
                    "progress": progress.completion_percentage if progress else 0,
                    "last_accessed": (
                        progress.last_accessed.isoformat() if progress and progress.last_accessed else None
                    ),
                    "attendance": {
                        "present": present,
                        "late": late,
                        "excused": excused,
                        "absent": absent,
                        "attendance_rate": attendance_rate,
                    },
                }
            )

        data["courses"] = courses_data

        # Achievements data
        achievements_data = []
        achievements = Achievement.objects.filter(student=student)

        for achievement in achievements:
            achievements_data.append(
                {
                    "id": achievement.id,
                    "title": achievement.title,
                    "description": achievement.description,
                    "date_earned": achievement.date_earned.isoformat(),
                }
            )

        data["achievements"] = achievements_data

    elif analytics_type == "learning_patterns":
        # Handle optional filtering
        course_id = request.GET.get("course_id")
        days = int(request.GET.get("days", 30))

        # Get learning patterns data
        patterns_data = analyze_learning_patterns(course_id=course_id, days=days)

        data = {
            "analysis_period": f"Last {days} days",
            "generated_at": datetime.now().isoformat(),
            "key_insights": {
                "peak_activity_hour": patterns_data["peak_activity_hour"],
                "avg_study_duration": patterns_data["avg_study_duration"],
                "popular_days": patterns_data["popular_days"],
            },
            "hourly_distribution": patterns_data["hourly_distribution"],
            "weekly_activity": patterns_data["weekly_activity"],
        }

        if course_id:
            course = Course.objects.get(id=course_id)
            data["course"] = {"id": course.id, "title": course.title}

    # Create JSON response
    response = HttpResponse(json.dumps(data, indent=4), content_type="application/json")
    filename = f"{analytics_type}_analytics_{timestamp}.json"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response
