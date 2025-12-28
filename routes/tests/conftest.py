"""
Pytest fixtures and configuration for route tests.
"""

import os
from pathlib import Path
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
import pytest


@pytest.fixture
def test_user(db):
    """Create a test user for authentication tests."""
    return User.objects.create_user(
        username="testuser", password="testpass123", email="test@example.com"
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user for admin tests."""
    return User.objects.create_superuser(
        username="admin", password="adminpass123", email="admin@example.com"
    )


@pytest.fixture
def sample_tag(db):
    """Create a sample tag."""
    from routes.models import Tag

    return Tag.objects.create(name="Hiking")


@pytest.fixture
def sample_tags(db):
    """Create multiple sample tags."""
    from routes.models import Tag

    return [
        Tag.objects.create(name="Hiking"),
        Tag.objects.create(name="Mountain"),
        Tag.objects.create(name="Scenic"),
    ]


@pytest.fixture
def sample_start_point(db):
    """Create a sample start point."""
    from routes.models import StartPoint

    return StartPoint.objects.create(
        name="Test Start Location",
        latitude=52.4603,
        longitude=-2.1638,
        description="A test start point",
    )


@pytest.fixture
def sample_route(db):
    """Create a sample route with test data."""
    from routes.models import Route

    route = Route.objects.create(
        name="Test Route",
        distance_km=10.5,
        elevation_gain=250.0,
        start_lat=52.4603,
        start_lon=-2.1638,
        start_location="Test Location",
        route_coordinates=[[52.4603, -2.1638], [52.4613, -2.1628]],
    )
    # Share token is auto-generated
    return route


@pytest.fixture
def sample_route_with_tags(db, sample_tags):
    """Create a sample route with tags attached."""
    from routes.models import Route

    route = Route.objects.create(
        name="Tagged Route",
        distance_km=15.0,
        elevation_gain=300.0,
        start_lat=52.4603,
        start_lon=-2.1638,
        route_coordinates=[[52.4603, -2.1638], [52.4613, -2.1628]],
    )
    route.tags.set(sample_tags)
    return route


def get_fixture_path(filename):
    """Get the full path to a test fixture file."""
    return Path(__file__).parent / "fixtures" / filename


@pytest.fixture
def sample_gpx_track():
    """Load the sample track GPX file."""
    path = get_fixture_path("sample_track.gpx")
    with open(path, "rb") as f:
        return SimpleUploadedFile(
            "sample_track.gpx", f.read(), content_type="application/gpx+xml"
        )


@pytest.fixture
def sample_gpx_route():
    """Load the sample route GPX file."""
    path = get_fixture_path("sample_route.gpx")
    with open(path, "rb") as f:
        return SimpleUploadedFile(
            "sample_route.gpx", f.read(), content_type="application/gpx+xml"
        )


@pytest.fixture
def sample_gpx_waypoints():
    """Load the waypoints-only GPX file."""
    path = get_fixture_path("waypoints_only.gpx")
    with open(path, "rb") as f:
        return SimpleUploadedFile(
            "waypoints_only.gpx", f.read(), content_type="application/gpx+xml"
        )


@pytest.fixture
def invalid_gpx():
    """Load the invalid GPX file."""
    path = get_fixture_path("invalid.gpx")
    with open(path, "rb") as f:
        return SimpleUploadedFile(
            "invalid.gpx", f.read(), content_type="application/gpx+xml"
        )


@pytest.fixture
def oversized_gpx():
    """Create an oversized GPX file (>10MB)."""
    # Create a GPX file larger than 10MB
    large_content = b'<?xml version="1.0"?><gpx version="1.1">'
    large_content += b"<trk><trkseg>" + (b"<trkpt lat='0' lon='0'></trkpt>" * 500000)
    large_content += b"</trkseg></trk></gpx>"

    return SimpleUploadedFile(
        "oversized.gpx", large_content, content_type="application/gpx+xml"
    )


@pytest.fixture
def non_gpx_file():
    """Create a non-GPX file."""
    return SimpleUploadedFile(
        "test.txt", b"This is not a GPX file", content_type="text/plain"
    )
