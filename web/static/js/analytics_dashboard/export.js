/**
 * Utility functions for exporting analytics data
 */

/**
 * Export analytics data in the specified format
 *
 * @param {string} format - Export format ('csv', 'pdf', or 'json')
 * @param {string} type - Analytics type ('course', 'student', or 'learning_patterns')
 * @param {number|null} id - Optional ID of the object to export
 * @param {Object} filters - Optional filters to apply
 */
function exportAnalytics(format, type, id = null, filters = {}) {
    // Build the URL
    let url = `/analytics/export/${format}/${type}/`;
    if (id) {
        url += `${id}/`;
    }

    // Add any filter parameters
    const queryParams = [];
    for (const key in filters) {
        if (filters[key]) {
            queryParams.push(`${key}=${encodeURIComponent(filters[key])}`);
        }
    }

    if (queryParams.length > 0) {
        url += `?${queryParams.join('&')}`;
    }

    // Trigger the download
    window.location.href = url;
}

// Set up event listeners when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Handle export buttons
    const exportPdfBtn = document.getElementById('exportPdfBtn');
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', function() {
            const pageType = document.body.dataset.pageType;
            const objectId = document.body.dataset.objectId;

            // Determine what to export based on current page
            switch (pageType) {
                case 'course-insights':
                    exportAnalytics('pdf', 'course', objectId);
                    break;

                case 'student-performance':
                    exportAnalytics('pdf', 'student', objectId);
                    break;

                case 'learning-patterns':
                    // Get filter values
                    const courseFilter = document.getElementById('courseFilter');
                    const timeRangeFilter = document.getElementById('timeRangeFilter');

                    const filters = {
                        course_id: courseFilter ? courseFilter.value : null,
                        days: timeRangeFilter ? timeRangeFilter.value : 30
                    };

                    exportAnalytics('pdf', 'learning_patterns', null, filters);
                    break;

                default:
                    alert('Please navigate to a specific report to export.');
            }
        });
    }

    // Handle CSV export button
    const exportCsvBtn = document.getElementById('exportCsvBtn');
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', function() {
            const pageType = document.body.dataset.pageType;
            const objectId = document.body.dataset.objectId;

            // Determine what to export based on current page
            switch (pageType) {
                case 'course-insights':
                    exportAnalytics('csv', 'course', objectId);
                    break;

                case 'student-performance':
                    exportAnalytics('csv', 'student', objectId);
                    break;

                case 'learning-patterns':
                    // Get filter values
                    const courseFilter = document.getElementById('courseFilter');
                    const timeRangeFilter = document.getElementById('timeRangeFilter');

                    const filters = {
                        course_id: courseFilter ? courseFilter.value : null,
                        days: timeRangeFilter ? timeRangeFilter.value : 30
                    };

                    exportAnalytics('csv', 'learning_patterns', null, filters);
                    break;

                default:
                    alert('Please navigate to a specific report to export.');
            }
        });
    }

    // Handle JSON export button (if present)
    const exportJsonBtn = document.getElementById('exportJsonBtn');
    if (exportJsonBtn) {
        exportJsonBtn.addEventListener('click', function() {
            const pageType = document.body.dataset.pageType;
            const objectId = document.body.dataset.objectId;

            // Similar switch statement as above
            switch (pageType) {
                case 'course-insights':
                    exportAnalytics('json', 'course', objectId);
                    break;

                // Other cases similar to PDF and CSV
            }
        });
    }
});
