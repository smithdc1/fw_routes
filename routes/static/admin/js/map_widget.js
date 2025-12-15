django.jQuery(document).ready(function($) {
    // Only run on StartPoint add/change pages
    if ($('#id_latitude').length && $('#id_longitude').length) {
        // Initialize map centered on default location
        const defaultLat = parseFloat($('#id_latitude').val()) || 39.7392;
        const defaultLon = parseFloat($('#id_longitude').val()) || -104.9903;

        const map = L.map('map').setView([defaultLat, defaultLon], 10);

        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        // Add marker
        let marker = L.marker([defaultLat, defaultLon], {
            draggable: true
        }).addTo(map);

        // Update form fields when marker is dragged
        marker.on('dragend', function(e) {
            const position = marker.getLatLng();
            $('#id_latitude').val(position.lat.toFixed(6));
            $('#id_longitude').val(position.lng.toFixed(6));
        });

        // Update marker when clicking on map
        map.on('click', function(e) {
            marker.setLatLng(e.latlng);
            $('#id_latitude').val(e.latlng.lat.toFixed(6));
            $('#id_longitude').val(e.latlng.lng.toFixed(6));
        });

        // Update marker when form fields change
        $('#id_latitude, #id_longitude').on('change', function() {
            const lat = parseFloat($('#id_latitude').val());
            const lon = parseFloat($('#id_longitude').val());
            if (!isNaN(lat) && !isNaN(lon)) {
                marker.setLatLng([lat, lon]);
                map.panTo([lat, lon]);
            }
        });
    }
});
