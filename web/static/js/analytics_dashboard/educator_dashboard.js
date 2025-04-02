// web/static/js/analytics_dashboard/educator_dashboard.js

document.addEventListener('DOMContentLoaded', function() {
    // Chart.js Configuration
    Chart.defaults.font.family = "'Inter', 'Helvetica', 'Arial', sans-serif";
    Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue('--text-color') || '#4B5563';

    // Sample course data - this would come from the backend in production
    const courseData = [
        { name: 'Introduction to Python', students: 32, completion: 78 },
        { name: 'Web Development Basics', students: 28, completion: 65 },
        { name: 'Data Science Fundamentals', students: 24, completion: 42 },
        { name: 'Machine Learning', students: 18, completion: 55 },
        { name: 'Advanced JavaScript', students: 15, completion: 80 },
    ];

    // Progress Chart
    const progressCtx = document.getElementById('progressChart').getContext('2d');
    new Chart(progressCtx, {
        type: 'bar',
        data: {
            labels: courseData.map(course => course.name),
            datasets: [
                {
                    label: 'Completion Rate (%)',
                    data: courseData.map(course => course.completion),
                    backgroundColor: 'rgba(79, 70, 229, 0.7)',
                    borderColor: 'rgba(79, 70, 229, 1)',
                    borderWidth: 1,
                    borderRadius: 4,
                    barPercentage: 0.6,
                    categoryPercentage: 0.8
                },
                {
                    label: 'Students Enrolled',
                    data: courseData.map(course => course.students),
                    backgroundColor: 'rgba(59, 130, 246, 0.7)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 1,
                    borderRadius: 4,
                    barPercentage: 0.6,
                    categoryPercentage: 0.8
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    titleColor: '#000',
                    bodyColor: '#000',
                    borderColor: 'rgba(0, 0, 0, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    boxPadding: 6,
                    usePointStyle: true,
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        drawBorder: false,
                        color: 'rgba(0, 0, 0, 0.05)'
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

    // Student Engagement Chart
    const engagementCtx = document.getElementById('engagementChart').getContext('2d');
    new Chart(engagementCtx, {
        type: 'radar',
        data: {
            labels: ['Active Participation', 'Assignment Completion', 'Video Viewing', 'Quiz Performance', 'Forum Activity', 'Attendance'],
            datasets: [{
                label: 'Average Engagement',
                data: [65, 75, 85, 70, 55, 80],
                backgroundColor: 'rgba(79, 70, 229, 0.2)',
                borderColor: 'rgba(79, 70, 229, 1)',
                pointBackgroundColor: 'rgba(79, 70, 229, 1)',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: 'rgba(79, 70, 229, 1)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            elements: {
                line: {
                    borderWidth: 2
                }
            },
            scales: {
                r: {
                    angleLines: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    suggestedMin: 0,
                    suggestedMax: 100,
                    ticks: {
                        stepSize: 20,
                        backdropColor: 'transparent'
                    }
                }
            }
        }
    });

    // Export PDF functionality
    document.getElementById('exportPdfBtn').addEventListener('click', function() {
        alert('Generating PDF report... This would download a comprehensive analytics report PDF in a real implementation.');
    });

    // Export CSV functionality
    document.getElementById('exportCsvBtn').addEventListener('click', function() {
        alert('Exporting CSV data... This would download raw analytics data as CSV in a real implementation.');
    });
});
