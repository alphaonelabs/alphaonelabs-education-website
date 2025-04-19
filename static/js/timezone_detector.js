/**
 * Timezone detector script
 * Automatically detects the user's timezone and sends it to the server
 */

document.addEventListener('DOMContentLoaded', function () {
    // Detect user's timezone using Intl API
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    // Only proceed if we got a valid timezone
    if (timezone) {
        console.log('Detected timezone:', timezone);
        // Check if timezone has changed to avoid unnecessary server requests
        const storedTimezone = localStorage.getItem('userTimezone');
        if (storedTimezone !== timezone) {
            sendTimezoneToServer(timezone);
            localStorage.setItem('userTimezone', timezone);
        }
    } else {
        console.error('Could not detect timezone');
    }
});

/**
 * Send the detected timezone to the server
 * @param {string} timezone - The detected timezone (e.g., 'America/New_York')
 */

function sendTimezoneToServer(timezone) {
    // Create form data for the request
    const formData = new FormData();
    formData.append('timezone', timezone);

    // Get CSRF token from cookie
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');

    // Send the request
    fetch('/set-timezone/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrftoken
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log('Timezone set successfully:', data.timezone);
            } else {
                console.error('Error setting timezone:', data.message);
            }
        })
        .catch(error => {
            console.error('Error sending timezone to server:', error);
        });
}
