// web/static/js/analytics_dashboard/student_performance.js

document.addEventListener('DOMContentLoaded', function() {
    // Chart.js Configuration
    Chart.defaults.font.family = "'Inter', 'Helvetica', 'Arial', sans-serif";
    Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue('--text-color') || '#4B5563';

    // Course Progress Chart
    const progressCtx = document.getElementById('courseProgressChart').getContext('2d');

    // Get data from Django template or use sample data
    const courseData = window.coursesData || [
        { course: 'Web Development', progress: 85, enrollment_date: '2025-01-15' },
        { course: 'Data Science', progress: 62, enrollment_date: '2025-02-08' },
        { course: 'Machine Learning', progress: 45, enrollment_date: '2025-03-10' },
        { course: 'Python Programming', progress: 90, enrollment_date: '2024-12-05' },
    ];

    new Chart(progressCtx, {
        type: 'bar',
        data: {
            labels: courseData.map(course => course.course),
            datasets: [{
                label: 'Course Progress (%)',
                data: courseData.map(course => course.progress),
                backgroundColor: courseData.map(progress => {
                    if (progress > 75) return 'rgba(16, 185, 129, 0.7)';  // Green
                    if (progress > 50) return 'rgba(59, 130, 246, 0.7)';  // Blue
                    if (progress > 25) return 'rgba(245, 158, 11, 0.7)';  // Yellow
                    return 'rgba(239, 68, 68, 0.7)';  // Red
                }),
                borderColor: courseData.map(progress => {
                    if (progress > 75) return 'rgb(16, 185, 129)';  // Green
                    if (progress > 50) return 'rgb(59, 130, 246)';  // Blue
                    if (progress > 25) return 'rgb(245, 158, 11)';  // Yellow
                    return 'rgb(239, 68, 68)';  // Red
                }),
                borderWidth: 1,
                borderRadius: 4,
                barPercentage: 0.7,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    titleColor: '#000',
                    bodyColor: '#000',
                    borderColor: 'rgba(0, 0, 0, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    boxPadding: 6,
                    usePointStyle: true,
                    callbacks: {
                        afterLabel: function(context) {
                            const index = context.dataIndex;
                            return `Enrolled: ${new Date(courseData[index].enrollment_date).toLocaleDateString()}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: {
                        drawBorder: false,
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });

    // Attendance Chart
    const attendanceCtx = document.getElementById('attendanceChart').getContext('2d');

    // Get data from Django template or use sample data
    const attendanceData = window.attendanceData || {
        present: 15,
        late: 3,
        excused: 2,
        absent: 4
    };

    new Chart(attendanceCtx, {
        type: 'doughnut',
        data: {
            labels: ['Present', 'Late', 'Excused', 'Absent'],
            datasets: [{
                data: [
                    attendanceData.present,
                    attendanceData.late,
                    attendanceData.excused,
                    attendanceData.absent
                ],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.7)',  // Green - Present
                    'rgba(59, 130, 246, 0.7)',  // Blue - Late
                    'rgba(245, 158, 11, 0.7)',  // Yellow - Excused
                    'rgba(239, 68, 68, 0.7)'    // Red - Absent
                ],
                borderColor: [
                    'rgb(16, 185, 129)',
                    'rgb(59, 130, 246)',
                    'rgb(245, 158, 11)',
                    'rgb(239, 68, 68)'
                ],
                borderWidth: 1,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    titleColor: '#000',
                    bodyColor: '#000',
                    borderColor: 'rgba(0, 0, 0, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    boxPadding: 6,
                    usePointStyle: true,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((acc, val) => acc + val, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });

    // Engagement Circle
    const engagementCircle = document.getElementById('engagementCircle');
    const engagementText = document.getElementById('engagementText');

    // Sample engagement score (0-100) - would come from backend
    const engagementScore = 85;

    if (engagementCircle && engagementText) {
        const radius = 50;
        const circumference = radius * 2 * Math.PI;
        const offset = circumference - (engagementScore / 100) * circumference;

        engagementCircle.style.strokeDasharray = `${circumference} ${circumference}`;
        engagementCircle.style.strokeDashoffset = offset;
        engagementText.textContent = `${engagementScore}%`;
    }

    // Contact Student button
    const contactButton = document.getElementById('contactStudent');
    if (contactButton) {
        contactButton.addEventListener('click', function() {
            alert('In a real implementation, this would open a messaging interface to contact the student.');
        });
    }
});
