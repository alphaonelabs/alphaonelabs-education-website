// web/static/js/analytics_dashboard/course_insights.js

document.addEventListener('DOMContentLoaded', function() {
    // Chart.js Configuration
    Chart.defaults.font.family = "'Inter', 'Helvetica', 'Arial', sans-serif";
    Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue('--text-color') || '#4B5563';

    // Progress Distribution Chart
    const progressDistributionCtx = document.getElementById('progressDistributionChart').getContext('2d');

    // Sample data - this would come from the backend in production
    const progressBins = [
        { range: '0-10%', count: 3 },
        { range: '11-20%', count: 4 },
        { range: '21-30%', count: 5 },
        { range: '31-40%', count: 7 },
        { range: '41-50%', count: 8 },
        { range: '51-60%', count: 10 },
        { range: '61-70%', count: 12 },
        { range: '71-80%', count: 15 },
        { range: '81-90%', count: 11 },
        { range: '91-100%', count: 8 }
    ];

    new Chart(progressDistributionCtx, {
        type: 'bar',
        data: {
            labels: progressBins.map(bin => bin.range),
            datasets: [{
                label: 'Number of Students',
                data: progressBins.map(bin => bin.count),
                backgroundColor: function(context) {
                    const index = context.dataIndex;
                    const value = index * 10; // 0-10, 10-20, etc.

                    if (value < 30) return 'rgba(239, 68, 68, 0.7)';  // Red
                    if (value < 60) return 'rgba(245, 158, 11, 0.7)';  // Yellow
                    if (value < 80) return 'rgba(59, 130, 246, 0.7)';  // Blue
                    return 'rgba(16, 185, 129, 0.7)';  // Green
                },
                borderColor: function(context) {
                    const index = context.dataIndex;
                    const value = index * 10; // 0-10, 10-20, etc.

                    if (value < 30) return 'rgb(239, 68, 68)';  // Red
                    if (value < 60) return 'rgb(245, 158, 11)';  // Yellow
                    if (value < 80) return 'rgb(59, 130, 246)';  // Blue
                    return 'rgb(16, 185, 129)';  // Green
                },
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
                        label: function(context) {
                            return `${context.parsed.y} students (${Math.round(context.parsed.y / progressBins.reduce((sum, bin) => sum + bin.count, 0) * 100)}%)`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        drawBorder: false,
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    title: {
                        display: true,
                        text: 'Number of Students'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Progress Range'
                    }
                }
            }
        }
    });

    // Module Performance Chart
    const modulePerformanceCtx = document.getElementById('modulePerformanceChart').getContext('2d');

    // Sample data - this would come from the backend in production
    const moduleData = [
        { name: 'Introduction to HTML & CSS', score: 92 },
        { name: 'Responsive Design Principles', score: 88 },
        { name: 'JavaScript Fundamentals', score: 76 },
        { name: 'DOM Manipulation', score: 62 },
        { name: 'Advanced JavaScript Concepts', score: 48 }
    ];

    new Chart(modulePerformanceCtx, {
        type: 'horizontalBar',
        data: {
            labels: moduleData.map(module => module.name),
            datasets: [{
                label: 'Average Score (%)',
                data: moduleData.map(module => module.score),
                backgroundColor: moduleData.map(module => {
                    if (module.score >= 80) return 'rgba(16, 185, 129, 0.7)';  // Green
                    if (module.score >= 70) return 'rgba(59, 130, 246, 0.7)';  // Blue
                    if (module.score >= 60) return 'rgba(245, 158, 11, 0.7)';  // Yellow
                    return 'rgba(239, 68, 68, 0.7)';  // Red
                }),
                borderColor: moduleData.map(module => {
                    if (module.score >= 80) return 'rgb(16, 185, 129)';  // Green
                    if (module.score >= 70) return 'rgb(59, 130, 246)';  // Blue
                    if (module.score >= 60) return 'rgb(245, 158, 11)';  // Yellow
                    return 'rgb(239, 68, 68)';  // Red
                }),
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: {
            indexAxis: 'y',
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
                        label: function(context) {
                            return `Average Score: ${context.parsed.x}%`;
                        }
                    }
                }
            },
            scales: {
                x: {
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
                y: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });

    // Session Attendance Chart
    const sessionAttendanceCtx = document.getElementById('sessionAttendanceChart').getContext('2d');

    // Sample data - this would come from the backend in production
    const sessionData = [
        { title: 'Intro to CSS Grid', date: '2025-01-15', attendance_rate: 88 },
        { title: 'JavaScript Basics', date: '2025-01-22', attendance_rate: 92 },
        { title: 'DOM Manipulation', date: '2025-01-29', attendance_rate: 76 },
        { title: 'Event Handling', date: '2025-02-05', attendance_rate: 82 },
        { title: 'Async JavaScript', date: '2025-02-12', attendance_rate: 68 },
        { title: 'APIs & Fetch', date: '2025-02-19', attendance_rate: 74 },
        { title: 'ES6 Features', date: '2025-02-26', attendance_rate: 80 },
        { title: 'React Intro', date: '2025-03-05', attendance_rate: 94 }
    ];

    new Chart(sessionAttendanceCtx, {
        type: 'line',
        data: {
            labels: sessionData.map(session => {
                const date = new Date(session.date);
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            }),
            datasets: [{
                label: 'Attendance Rate (%)',
                data: sessionData.map(session => session.attendance_rate),
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                borderColor: 'rgba(79, 70, 229, 1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true,
                pointBackgroundColor: sessionData.map(session => {
                    if (session.attendance_rate >= 80) return 'rgba(16, 185, 129, 1)';  // Green
                    if (session.attendance_rate >= 60) return 'rgba(59, 130, 246, 1)';  // Blue
                    if (session.attendance_rate >= 40) return 'rgba(245, 158, 11, 1)';  // Yellow
                    return 'rgba(239, 68, 68, 1)';  // Red
                }),
                pointBorderColor: '#fff',
                pointRadius: 5,
                pointHoverRadius: 7
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
                        title: function(context) {
                            const index = context[0].dataIndex;
                            return sessionData[index].title;
                        },
                        label: function(context) {
                            return `Attendance: ${context.parsed.y}%`;
                        },
                        afterLabel: function(context) {
                            const index = context.dataIndex;
                            return `Date: ${new Date(sessionData[index].date).toLocaleDateString()}`;
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

    // Activity Hours Chart
    const activityHoursCtx = document.getElementById('activityHoursChart').getContext('2d');

    // Sample data - this would come from the backend in production
    const hourlyActivity = [
        { hour: '12am', count: 2 },
        { hour: '1am', count: 1 },
        { hour: '2am', count: 0 },
        { hour: '3am', count: 0 },
        { hour: '4am', count: 1 },
        { hour: '5am', count: 2 },
        { hour: '6am', count: 5 },
        { hour: '7am', count: 8 },
        { hour: '8am', count: 15 },
        { hour: '9am', count: 22 },
        { hour: '10am', count: 28 },
        { hour: '11am', count: 26 },
        { hour: '12pm', count: 20 },
        { hour: '1pm', count: 18 },
        { hour: '2pm', count: 16 },
        { hour: '3pm', count: 22 },
        { hour: '4pm', count: 28 },
        { hour: '5pm', count: 32 },
        { hour: '6pm', count: 36 },
        { hour: '7pm', count: 40 },
        { hour: '8pm', count: 42 },
        { hour: '9pm', count: 38 },
        { hour: '10pm', count: 30 },
        { hour: '11pm', count: 18 }
    ];

    new Chart(activityHoursCtx, {
        type: 'bar',
        data: {
            labels: hourlyActivity.map(item => item.hour),
            datasets: [{
                label: 'Activity Count',
                data: hourlyActivity.map(item => item.count),
                backgroundColor: 'rgba(79, 70, 229, 0.7)',
                borderColor: 'rgba(79, 70, 229, 1)',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
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
                    },
                    ticks: {
                        autoSkip: true,
                        maxRotation: 0,
                        minRotation: 0
                    }
                }
            }
        }
    });

    // Resource Popularity Chart
    const resourcePopularityCtx = document.getElementById('resourcePopularityChart').getContext('2d');

    // Sample data - this would come from the backend in production
    const resourceData = [
        { name: 'Videos', count: 245 },
        { name: 'Exercises', count: 198 },
        { name: 'Articles', count: 87 },
        { name: 'Quizzes', count: 156 },
        { name: 'PDFs', count: 54 }
    ];

    new Chart(resourcePopularityCtx, {
        type: 'pie',
        data: {
            labels: resourceData.map(item => item.name),
            datasets: [{
                data: resourceData.map(item => item.count),
                backgroundColor: [
                    'rgba(79, 70, 229, 0.7)',  // Indigo
                    'rgba(16, 185, 129, 0.7)',  // Green
                    'rgba(245, 158, 11, 0.7)',  // Yellow
                    'rgba(59, 130, 246, 0.7)',  // Blue
                    'rgba(239, 68, 68, 0.7)'    // Red
                ],
                borderColor: [
                    'rgba(79, 70, 229, 1)',
                    'rgba(16, 185, 129, 1)',
                    'rgba(245, 158, 11, 1)',
                    'rgba(59, 130, 246, 1)',
                    'rgba(239, 68, 68, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 15,
                        padding: 15
                    }
                },
                tooltip: {
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

    // Grade Distribution Chart
    const gradeDistributionCtx = document.getElementById('gradeDistributionChart').getContext('2d');

    // Sample data - this would come from the backend in production
    const gradeData = [
        { grade: 'A', percentage: 28 },
        { grade: 'B', percentage: 35 },
        { grade: 'C', percentage: 22 },
        { grade: 'D', percentage: 10 },
        { grade: 'F', percentage: 5 }
    ];

    new Chart(gradeDistributionCtx, {
        type: 'bar',
        data: {
            labels: gradeData.map(item => item.grade),
            datasets: [{
                label: 'Projected Grade Distribution',
                data: gradeData.map(item => item.percentage),
                backgroundColor: [
                    'rgba(16, 185, 129, 0.7)',  // A - Green
                    'rgba(59, 130, 246, 0.7)',  // B - Blue
                    'rgba(245, 158, 11, 0.7)',  // C - Yellow
                    'rgba(249, 115, 22, 0.7)',  // D - Orange
                    'rgba(239, 68, 68, 0.7)'    // F - Red
                ],
                borderColor: [
                    'rgba(16, 185, 129, 1)',
                    'rgba(59, 130, 246, 1)',
                    'rgba(245, 158, 11, 1)',
                    'rgba(249, 115, 22, 1)',
                    'rgba(239, 68, 68, 1)'
                ],
                borderWidth: 1,
                borderRadius: 4
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
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.y}% of students`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
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
});
