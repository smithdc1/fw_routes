/**
 * FreeWheeler Routes - Route Detail Page JavaScript
 */

/**
 * Enable route name editing mode
 */
function enableEditMode() {
    document.getElementById('routeTitle').style.display = 'none';
    document.getElementById('editNameBtn').style.display = 'none';
    document.getElementById('renameForm').style.display = 'block';
    document.getElementById('newNameInput').focus();
    document.getElementById('newNameInput').select();
}

/**
 * Cancel route name editing and restore title view
 */
function cancelEditMode() {
    document.getElementById('routeTitle').style.display = 'block';
    document.getElementById('editNameBtn').style.display = 'inline-block';
    document.getElementById('renameForm').style.display = 'none';
}

/**
 * Copy share URL to clipboard
 */
function copyShareUrl() {
    const shareUrl = document.getElementById('shareUrl');
    const feedback = document.getElementById('copyFeedback');

    shareUrl.select();
    shareUrl.setSelectionRange(0, 99999); // For mobile devices
    navigator.clipboard.writeText(shareUrl.value).then(() => {
        // Show feedback message
        feedback.style.display = 'block';

        // Hide after 3 seconds
        setTimeout(() => {
            feedback.style.display = 'none';
        }, 3000);
    });
}

/**
 * Initialize Leaflet map for route visualization
 * @param {Array} coordinates - Array of [lat, lon] coordinate pairs
 */
function initializeRouteMap(coordinates) {
    if (!coordinates || coordinates.length === 0) {
        return;
    }

    // Calculate center
    const centerLat = coordinates.reduce((sum, p) => sum + p[0], 0) / coordinates.length;
    const centerLon = coordinates.reduce((sum, p) => sum + p[1], 0) / coordinates.length;

    // Create map
    const map = L.map('routeMap').setView([centerLat, centerLon], 13);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Add route line
    L.polyline(coordinates, {
        color: '#0d6efd',
        weight: 4,
        opacity: 0.8
    }).addTo(map).bindPopup('Route Path');

    // Add start marker
    L.circleMarker(coordinates[0], {
        radius: 10,
        color: 'green',
        fillColor: 'lightgreen',
        fillOpacity: 0.9,
        weight: 3
    }).addTo(map).bindPopup('<b>Start Point</b>').bindTooltip('Start');

    // Add end marker
    L.circleMarker(coordinates[coordinates.length - 1], {
        radius: 10,
        color: 'red',
        fillColor: 'lightcoral',
        fillOpacity: 0.9,
        weight: 3
    }).addTo(map).bindPopup('<b>End Point</b>').bindTooltip('End');

    // Fit bounds to show entire route
    map.fitBounds(L.polyline(coordinates).getBounds(), {
        padding: [50, 50]
    });
}

/**
 * Auto-initialize map on page load
 * Reads route coordinates from json_script tag if present
 */
document.addEventListener('DOMContentLoaded', function() {
    const coordinatesElement = document.getElementById('route-coordinates-data');
    if (coordinatesElement) {
        try {
            const coordinates = JSON.parse(coordinatesElement.textContent);
            initializeRouteMap(coordinates);
        } catch (error) {
            console.error('Error parsing route coordinates:', error);
        }
    }
});
