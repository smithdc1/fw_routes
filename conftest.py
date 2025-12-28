"""
Pytest configuration and fixtures for the GPX Routes project.

This file provides pytest-django configuration and common fixtures
used across all tests.
"""

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="adminpass123"
    )


@pytest.fixture
def sample_gpx_content():
    """
    Provide a minimal valid GPX file content for testing.

    This GPX file contains a simple track with 3 points.
    """
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
    <metadata>
        <name>Test Route</name>
    </metadata>
    <trk>
        <name>Sample Track</name>
        <trkseg>
            <trkpt lat="51.5074" lon="-0.1278">
                <ele>50</ele>
            </trkpt>
            <trkpt lat="51.5084" lon="-0.1268">
                <ele>60</ele>
            </trkpt>
            <trkpt lat="51.5094" lon="-0.1258">
                <ele>55</ele>
            </trkpt>
        </trkseg>
    </trk>
</gpx>
"""


@pytest.fixture
def sample_gpx_file(sample_gpx_content):
    """Create a SimpleUploadedFile with GPX content."""
    return SimpleUploadedFile(
        "test_route.gpx", sample_gpx_content, content_type="application/gpx+xml"
    )


@pytest.fixture
def complex_gpx_content():
    """
    Provide a more complex GPX file with elevation data for testing.
    """
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
    <metadata>
        <name>Complex Route</name>
    </metadata>
    <trk>
        <name>Mountain Trail</name>
        <trkseg>
            <trkpt lat="37.7749" lon="-122.4194">
                <ele>100</ele>
            </trkpt>
            <trkpt lat="37.7759" lon="-122.4184">
                <ele>150</ele>
            </trkpt>
            <trkpt lat="37.7769" lon="-122.4174">
                <ele>200</ele>
            </trkpt>
            <trkpt lat="37.7779" lon="-122.4164">
                <ele>180</ele>
            </trkpt>
            <trkpt lat="37.7789" lon="-122.4154">
                <ele>250</ele>
            </trkpt>
        </trkseg>
    </trk>
</gpx>
"""


@pytest.fixture
def invalid_gpx_content():
    """Provide invalid GPX content for testing error handling."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
    <invalid>This is not valid GPX</invalid>
</gpx>
"""


@pytest.fixture
def gpx_with_route_content():
    """
    GPX file using route instead of track (alternative GPX structure).
    """
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
    <rte>
        <name>Route Example</name>
        <rtept lat="40.7128" lon="-74.0060">
            <ele>10</ele>
        </rtept>
        <rtept lat="40.7138" lon="-74.0050">
            <ele>15</ele>
        </rtept>
        <rtept lat="40.7148" lon="-74.0040">
            <ele>12</ele>
        </rtept>
    </rte>
</gpx>
"""


@pytest.fixture
def gpx_with_waypoints_content():
    """
    GPX file with only waypoints (edge case).
    """
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
    <wpt lat="34.0522" lon="-118.2437">
        <name>Point 1</name>
    </wpt>
    <wpt lat="34.0532" lon="-118.2427">
        <name>Point 2</name>
    </wpt>
</gpx>
"""


@pytest.fixture
def empty_gpx_content():
    """
    Empty GPX file with no tracks, routes, or waypoints (edge case).
    """
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
    <metadata>
        <name>Empty Route</name>
    </metadata>
</gpx>
"""
