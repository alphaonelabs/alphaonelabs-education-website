// web/static/js/analytics_dashboard/learning_patterns.js

document.addEventListener('DOMContentLoaded', function() {
    // Chart.js Configuration
    Chart.defaults.font.family = "'Inter', 'Helvetica', 'Arial', sans-serif";
    Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue('--text-color') || '#4B5563';

    // Hourly Activity Chart
    const hourlyActivityCtx = document.getElementById('hourlyActivityChart').getContext('2d');

    // Sample data - this would come from the backend in production
    const hourlyData = [
        { hour: '12am', activity: 5 },
        { hour: '1am', activity: 3 },
        { hour: '2am', activity: 2 },
        { hour: '3am', activity: 1 },
        { hour: '4am', activity: 1 },
        { hour: '5am', activity: 2 },
        { hour: '6am', activity: 5 },
        { hour: '7am', activity: 10 },
        { hour: '8am', activity: 20 },
        { hour: '9am', activity: 35 },
        { hour: '10am', activity: 45 },
        { hour: '11am', activity: 40 },
        { hour: '12pm', activity: 30 },
        { hour: '1pm', activity: 25 },
        { hour: '2pm', activity: 30 },
        { hour: '3pm', activity: 35 },
        { hour: '4pm', activity: 40 },
        { hour: '5pm', activity: 50 },
        { hour: '6pm', activity: 65 },
        { hour: '7pm', activity: 80 },
        { hour: '8pm', activity: 85 },
        { hour: '9pm', activity: 75 },
        { hour: '10pm', activity: 45 },
        { hour: '11pm', activity: 20 }
    ];

    new Chart(hourlyActivityCtx, {
        type: 'line',
        data: {
            labels: hourlyData.map(hour => hour.hour),
            datasets: [{
                label: 'Student Activity',
                data: hourlyData.map(hour => hour.activity),
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                borderColor: 'rgba(79, 70, 229, 1)',
                borderWidth: 2,
                pointBackgroundColor: 'rgba(79, 70, 229, 1)',
                pointRadius: 3,
                pointHoverRadius: 5,
                tension: 0.3,
                fill: true
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
                            return `Activity level: ${context.parsed.y}`;
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
                        text: 'Activity Level'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Hour of Day'
                    }
                }
            }
        }
    });

    // Weekly Activity Chart
    const weeklyActivityCtx = document.getElementById('weeklyActivityChart').getContext('2d');

    // Sample data - this would come from the backend in production
    const weeklyData = [
        { day: 'Monday', activity: 75 },
        { day: 'Tuesday', activity: 62 },
        { day: 'Wednesday', activity: 68 },
        { day: 'Thursday', activity: 55 },
        { day: 'Friday', activity: 45 },
        { day: 'Saturday', activity: 80 },
        { day: 'Sunday', activity: 85 }
    ];

    new Chart(weeklyActivityCtx, {
        type: 'bar',
        data: {
            labels: weeklyData.map(day => day.day),
            datasets: [{
                label: 'Activity Level',
                data: weeklyData.map(day => day.activity),
                backgroundColor: function(context) {
                    const index = context.dataIndex;
                    const value = context.dataset.data[index];

                    // Weekend days (Saturday and Sunday)
                    if (index >= 5) {
                        return 'rgba(16, 185, 129, 0.7)';  // Green for weekends
                    }

                    // Weekdays with higher intensity
                    if (value >= 70) {
                        return 'rgba(79, 70, 229, 0.7)';  // Indigo
                    }
                    if (value >= 60) {
                        return 'rgba(59, 130, 246, 0.7)';  // Blue
                    }
                    if (value >= 50) {
                        return 'rgba(245, 158, 11, 0.7)';  // Yellow
                    }
                    return 'rgba(239, 68, 68, 0.7)';  // Red
                },
                borderColor: function(context) {
                    const index = context.dataIndex;
                    const value = context.dataset.data[index];

                    // Weekend days (Saturday and Sunday)
                    if (index >= 5) {
                        return 'rgba(16, 185, 129, 1)';  // Green for weekends
                    }

                    // Weekdays with higher intensity
                    if (value >= 70) {
                        return 'rgba(79, 70, 229, 1)';  // Indigo
                    }
                    if (value >= 60) {
                        return 'rgba(59, 130, 246, 1)';  // Blue
                    }
                    if (value >= 50) {
                        return 'rgba(245, 158, 11, 1)';  // Yellow
                    }
                    return 'rgba(239, 68, 68, 1)';  // Red
                },
                borderWidth: 1,
                borderRadius: 4,
                barPercentage: 0.7
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
                            return `Activity: ${context.parsed.y}%`;
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
                    },
                    title: {
                        display: true,
                        text: 'Activity Level (%)'
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

    // Content Type Chart
    const contentTypeCtx = document.getElementById('contentTypeChart').getContext('2d');

    // Sample data - this would come from the backend in production
    const contentTypeData = [
        { type: 'Interactive Exercises', engagement: 92 },
        { type: 'Video Tutorials', engagement: 86 },
        { type: 'Project Tasks', engagement: 78 },
        { type: 'Quizzes', engagement: 72 },
        { type: 'Discussion Forums', engagement: 65 },
        { type: 'Text Articles', engagement: 45 },
        { type: 'PDF Documents', engagement: 38 },
        { type: 'External Links', engagement: 32 }
    ];

    new Chart(contentTypeCtx, {
        type: 'horizontalBar',
        data: {
            labels: contentTypeData.map(item => item.type),
            datasets: [{
                label: 'Engagement Rate (%)',
                data: contentTypeData.map(item => item.engagement),
                backgroundColor: contentTypeData.map(item => {
                    const value = item.engagement;
                    if (value >= 80) return 'rgba(16, 185, 129, 0.7)';  // Green
                    if (value >= 60) return 'rgba(59, 130, 246, 0.7)';  // Blue
                    if (value >= 40) return 'rgba(245, 158, 11, 0.7)';  // Yellow
                    return 'rgba(239, 68, 68, 0.7)';  // Red
                }),
                borderColor: contentTypeData.map(item => {
                    const value = item.engagement;
                    if (value >= 80) return 'rgba(16, 185, 129, 1)';  // Green
                    if (value >= 60) return 'rgba(59, 130, 246, 1)';  // Blue
                    if (value >= 40) return 'rgba(245, 158, 11, 1)';  // Yellow
                    return 'rgba(239, 68, 68, 1)';  // Red
                }),
                borderWidth: 1,
                borderRadius: 4
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
                            return `Engagement: ${context.parsed.x}%`;
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
                    },
                    title: {
                        display: true,
                        text: 'Engagement Rate (%)'
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

    // Study Duration Chart
    const studyDurationCtx = document.getElementById('studyDurationChart').getContext('2d');

    // Sample data - this would come from the backend in production
    const durationData = [
        { range: '< 15 min', percentage: 18 },
        { range: '15-30 min', percentage: 35 },
        { range: '30-60 min', percentage: 32 },
        { range: '1-2 hours', percentage: 12 },
        { range: '> 2 hours', percentage: 3 }
    ];

    new Chart(studyDurationCtx, {
        type: 'pie',
        data: {
            labels: durationData.map(item => item.range),
            datasets: [{
                data: durationData.map(item => item.percentage),
                backgroundColor: [
                    'rgba(239, 68, 68, 0.7)',    // Red
                    'rgba(245, 158, 11, 0.7)',  // Yellow
                    'rgba(59, 130, 246, 0.7)',  // Blue
                    'rgba(16, 185, 129, 0.7)',  // Green
                    'rgba(79, 70, 229, 0.7)'   // Indigo
                ],
                borderColor: [
                    'rgba(239, 68, 68, 1)',
                    'rgba(245, 158, 11, 1)',
                    'rgba(59, 130, 246, 1)',
                    'rgba(16, 185, 129, 1)',
                    'rgba(79, 70, 229, 1)'
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
                            return `${label}: ${value}% of study sessions`;
                        }
                    }
                }
            }
        }
    });

    // Device Usage Chart
    const deviceUsageCtx = document.getElementById('deviceUsageChart').getContext('2d');

    // Sample data - this would come from the backend in production
    const deviceData = [
        { device: 'Desktop', percentage: 48 },
        { device: 'Laptop', percentage: 32 },
        { device: 'Tablet', percentage: 8 },
        { device: 'Smartphone', percentage: 12 }
    ];

    new Chart(deviceUsageCtx, {
        type: 'doughnut',
        data: {
            labels: deviceData.map(item => item.device),
            datasets: [{
                data: deviceData.map(item => item.percentage),
                backgroundColor: [
                    'rgba(79, 70, 229, 0.7)',   // Indigo
                    'rgba(59, 130, 246, 0.7)',  // Blue
                    'rgba(16, 185, 129, 0.7)',  // Green
                    'rgba(245, 158, 11, 0.7)'   // Yellow
                ],
                borderColor: [
                    'rgba(79, 70, 229, 1)',
                    'rgba(59, 130, 246, 1)',
                    'rgba(16, 185, 129, 1)',
                    'rgba(245, 158, 11, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
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
                            return `${label}: ${value}%`;
                        }
                    }
                }
            }
        }
    });

    // Filter handlers
    const courseFilter = document.getElementById('courseFilter');
    const timeRangeFilter = document.getElementById('timeRangeFilter');

    if (courseFilter) {
        courseFilter.addEventListener('change', function() {
            console.log(`Filtering by course: ${this.value}`);
            // In a real implementation, this would trigger an AJAX call to fetch filtered data
            // and update all charts and metrics
        });
    }

    if (timeRangeFilter) {
        timeRangeFilter.addEventListener('change', function() {
            console.log(`Filtering by time range: Last ${this.value} days`);
            // In a real implementation, this would trigger an AJAX call to fetch filtered data
            // and update all charts and metrics
        });
    }
});
