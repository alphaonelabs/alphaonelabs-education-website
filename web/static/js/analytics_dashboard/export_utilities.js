// web/static/js/analytics_dashboard/export_utilities.js

/**
 * Utility functions for exporting analytics data from the dashboard
 */

/**
 * Export analytics data in the specified format
 *
 * @param {string} format - 'csv', 'pdf', or 'json'
 * @param {string} analyticsType - 'course', 'student', or 'patterns'
 * @param {number} objId - The ID of the object (course or student)
 * @param {Object} filters - Optional filters to apply
 */
function exportAnalytics(format, analyticsType, objId = null, filters = {}) {
    // Build the URL
    let url = `/analytics/export/${format}/${analyticsType}/`;
    if (objId) {
        url += `${objId}/`;
    }

    // Add query parameters for filters
    const queryParams = new URLSearchParams();
    Object.keys(filters).forEach(key => {
        if (filters[key]) {
            queryParams.append(key, filters[key]);
        }
    });

    if (queryParams.toString()) {
        url += `?${queryParams.toString()}`;
    }

    // Trigger the download
    window.location.href = url;
}

/**
 * Export course analytics
 *
 * @param {string} format - 'csv', 'pdf', or 'json'
 * @param {number} courseId - The course ID
 */
function exportCourseAnalytics(format, courseId) {
    exportAnalytics(format, 'course', courseId);
}

/**
 * Export student analytics
 *
 * @param {string} format - 'csv', 'pdf', or 'json'
 * @param {number} studentId - The student ID
 */
function exportStudentAnalytics(format, studentId) {
    exportAnalytics(format, 'student', studentId);
}

/**
 * Export learning patterns analytics
 *
 * @param {string} format - 'csv', 'pdf', or 'json'
 * @param {Object} filters - Filters to apply (course_id, days)
 */
function exportLearningPatternsAnalytics(format, filters = {}) {
    exportAnalytics(format, 'patterns', null, filters);
}

/**
 * Set up export buttons on the dashboard
 */
document.addEventListener('DOMContentLoaded', function() {
    // PDF export button
    const exportPdfBtn = document.getElementById('exportPdfBtn');
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', function() {
            // Determine the current page type and ID
            const pageType = document.body.dataset.pageType;
            const objectId = document.body.dataset.objectId;

            switch (pageType) {
                case 'course-insights':
                    exportCourseAnalytics('pdf', objectId);
                    break;
                case 'student-performance':
                    exportStudentAnalytics('pdf', objectId);
                    break;
                case 'learning-patterns':
                    const courseFilter = document.getElementById('courseFilter');
                    const timeRangeFilter = document.getElementById('timeRangeFilter');

                    const filters = {
                        course_id: courseFilter ? courseFilter.value : null,
                        days: timeRangeFilter ? timeRangeFilter.value : 30
                    };

                    exportLearningPatternsAnalytics('pdf', filters);
                    break;
                default:
                    // Default to educator dashboard overview
                    alert('Select a specific report to export');
                    break;
            }
        });
    }

    // CSV export button
    const exportCsvBtn = document.getElementById('exportCsvBtn');
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', function() {
            // Determine the current page type and ID
            const pageType = document.body.dataset.pageType;
            const objectId = document.body.dataset.objectId;

            switch (pageType) {
                case 'course-insights':
                    exportCourseAnalytics('csv', objectId);
                    break;
                case 'student-performance':
                    exportStudentAnalytics('csv', objectId);
                    break;
                case 'learning-patterns':
                    const courseFilter = document.getElementById('courseFilter');
                    const timeRangeFilter = document.getElementById('timeRangeFilter');

                    const filters = {
                        course_id: courseFilter ? courseFilter.value : null,
                        days: timeRangeFilter ? timeRangeFilter.value : 30
                    };

                    exportLearningPatternsAnalytics('csv', filters);
                    break;
                default:
                    // Default to educator dashboard overview
                    alert('Select a specific report to export');
                    break;
            }
        });
    }
});
