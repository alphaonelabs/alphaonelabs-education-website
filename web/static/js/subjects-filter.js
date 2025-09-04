// web/static/js/subjects-filter.js
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('filterForm');
    const searchInput = document.getElementById('search');
    const resultsContainer = document.getElementById('results'); // <-- add a div for results
    let searchTimeout;

    // Fetch results via AJAX
    function fetchResults() {
        const formData = new FormData(form);
        const params = new URLSearchParams();

        for (let [key, value] of formData.entries()) {
            if (value && value.trim() !== '') {
                params.append(key, value);
            }
        }

        const url = window.location.pathname + (params.toString() ? '?' + params.toString() : '');

        // Update URL without reload
        window.history.replaceState({}, '', url);

        // Show loading state
        if (resultsContainer) {
            resultsContainer.innerHTML = '<p>Loading...</p>';
        }

        // Fetch filtered results
        fetch(url, {
            headers: { "X-Requested-With": "XMLHttpRequest" } // so backend can detect AJAX
        })
        .then(response => response.text())
        .then(html => {
            // Replace results section
            if (resultsContainer) {
                resultsContainer.innerHTML = html;
            }
        })
        .catch(error => {
            console.error("Error fetching results:", error);
        });
    }

    // Debounced search
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(fetchResults, 500);
    });

    // Auto-submit on filter changes
    const filterControls = form.querySelectorAll('select, input[type="checkbox"], input[type="number"]');
    filterControls.forEach(function(element) {
        if (element.id !== 'search') {
            element.addEventListener('change', fetchResults);
        }
    });

    // Clear individual filter
    window.clearFilter = function(filterName) {
        const element = document.querySelector(`[name="${filterName}"]`);
        if (element) {
            if (element.type === 'checkbox') {
                element.checked = false;
            } else {
                element.value = '';
            }
            fetchResults();
        }
    };

    // Reset all filters
    window.resetAllFilters = function() {
        window.history.replaceState({}, '', window.location.pathname);
        form.reset();
        fetchResults();
    };
});
