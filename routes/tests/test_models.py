"""
Tests for routes models: Tag, StartPoint, and Route.

These tests cover normal operations and edge cases including:
- Tag normalization with various whitespace patterns
- Unique constraints and duplicate handling
- Route share token generation
- Property calculations (distance conversions, estimated time)
- Model string representations
"""

import pytest
from django.db import IntegrityError

from routes.models import Route, StartPoint, Tag


class TestTag:
    """Tests for the Tag model."""

    def test_tag_creation(self, db):
        """Test basic tag creation."""
        tag = Tag.objects.create(name="Hiking")
        assert tag.name == "Hiking"
        assert str(tag) == "Hiking"
        assert tag.created_at is not None

    def test_tag_normalize_name_basic(self, db):
        """Test basic tag name normalization to titlecase."""
        tag = Tag.objects.create(name="mountain biking")
        assert tag.name == "Mountain Biking"

    def test_tag_normalize_name_whitespace(self, db):
        """Test tag normalization removes extra whitespace."""
        tag = Tag.objects.create(name="  hiking   trail  ")
        assert tag.name == "Hiking Trail"

    def test_tag_normalize_name_multiple_spaces(self, db):
        """Test tag normalization collapses multiple spaces."""
        tag = Tag.objects.create(name="mountain    bike    trail")
        assert tag.name == "Mountain Bike Trail"

    def test_tag_normalize_name_tabs_and_newlines(self, db):
        """Test tag normalization handles tabs and newlines."""
        tag = Tag.objects.create(name="hiking\t\ntrail")
        assert tag.name == "Hiking Trail"

    def test_tag_normalize_name_empty_string(self, db):
        """Test tag normalization handles empty strings."""
        result = Tag.normalize_name("")
        assert result == ""

    def test_tag_normalize_name_none(self, db):
        """Test tag normalization handles None."""
        result = Tag.normalize_name(None)
        assert result == ""

    def test_tag_normalize_name_only_whitespace(self, db):
        """Test tag normalization handles strings with only whitespace."""
        result = Tag.normalize_name("   ")
        assert result == ""

    def test_tag_unique_constraint(self, db):
        """Test that tag names must be unique."""
        Tag.objects.create(name="Hiking")
        with pytest.raises(IntegrityError):
            Tag.objects.create(name="Hiking")

    def test_tag_case_insensitive_duplicates(self, db):
        """Test that normalized names prevent duplicates regardless of case."""
        Tag.objects.create(name="hiking")
        # This should fail because "hiking" normalizes to "Hiking"
        with pytest.raises(IntegrityError):
            Tag.objects.create(name="HIKING")

    def test_tag_whitespace_duplicates(self, db):
        """Test that whitespace differences don't create duplicates."""
        Tag.objects.create(name="mountain biking")
        # This should fail because whitespace is normalized
        with pytest.raises(IntegrityError):
            Tag.objects.create(name="  mountain   biking  ")

    def test_tag_ordering(self, db):
        """Test that tags are ordered by name."""
        Tag.objects.create(name="Zebra")
        Tag.objects.create(name="Apple")
        Tag.objects.create(name="Mountain")

        tags = list(Tag.objects.all())
        assert tags[0].name == "Apple"
        assert tags[1].name == "Mountain"
        assert tags[2].name == "Zebra"


class TestStartPoint:
    """Tests for the StartPoint model."""

    def test_start_point_creation(self, db):
        """Test basic start point creation."""
        point = StartPoint.objects.create(
            name="Golden Gate Park",
            latitude=37.7694,
            longitude=-122.4862,
            description="Popular cycling start point",
        )
        assert point.name == "Golden Gate Park"
        assert point.latitude == 37.7694
        assert point.longitude == -122.4862
        assert point.description == "Popular cycling start point"
        assert point.created_at is not None

    def test_start_point_str_representation(self, db):
        """Test StartPoint string representation."""
        point = StartPoint.objects.create(
            name="City Center", latitude=51.5074, longitude=-0.1278
        )
        assert str(point) == "City Center (51.5074, -0.1278)"

    def test_start_point_without_description(self, db):
        """Test creating start point without description."""
        point = StartPoint.objects.create(
            name="Trail Head", latitude=40.7128, longitude=-74.0060
        )
        assert point.description == ""

    def test_start_point_ordering(self, db):
        """Test that start points are ordered by name."""
        StartPoint.objects.create(name="Zebra Park", latitude=40.0, longitude=-74.0)
        StartPoint.objects.create(name="Apple Trail", latitude=41.0, longitude=-75.0)
        StartPoint.objects.create(name="Mountain Base", latitude=42.0, longitude=-76.0)

        points = list(StartPoint.objects.all())
        assert points[0].name == "Apple Trail"
        assert points[1].name == "Mountain Base"
        assert points[2].name == "Zebra Park"

    def test_start_point_extreme_coordinates(self, db):
        """Test start points with extreme coordinate values."""
        # North pole
        north = StartPoint.objects.create(
            name="North Pole", latitude=90.0, longitude=0.0
        )
        assert north.latitude == 90.0

        # South pole
        south = StartPoint.objects.create(
            name="South Pole", latitude=-90.0, longitude=0.0
        )
        assert south.latitude == -90.0

        # International date line
        east = StartPoint.objects.create(
            name="Date Line", latitude=0.0, longitude=180.0
        )
        assert east.longitude == 180.0


class TestRoute:
    """Tests for the Route model."""

    def test_route_creation_minimal(self, db):
        """Test creating a route with minimal required fields."""
        route = Route.objects.create(name="Test Route")
        assert route.name == "Test Route"
        assert route.distance_km == 0
        assert route.elevation_gain == 0
        assert route.route_coordinates == []
        assert route.share_token != ""
        assert len(route.share_token) == 16

    def test_route_share_token_generation(self, db):
        """Test that share tokens are automatically generated."""
        route1 = Route.objects.create(name="Route 1")
        route2 = Route.objects.create(name="Route 2")

        assert route1.share_token != ""
        assert route2.share_token != ""
        assert route1.share_token != route2.share_token

    def test_route_share_token_unique(self, db):
        """Test that share tokens are unique."""
        route = Route.objects.create(name="Test Route")
        token = route.share_token

        # Try to create another route with the same token
        with pytest.raises(IntegrityError):
            Route.objects.create(name="Another Route", share_token=token)

    def test_route_str_representation(self, db):
        """Test Route string representation."""
        route = Route.objects.create(name="Mountain Loop")
        assert str(route) == "Mountain Loop"

    def test_route_distance_miles_property(self, db):
        """Test distance conversion to miles."""
        route = Route.objects.create(name="Test Route", distance_km=10.0)
        # 10 km * 0.621371 = 6.21371 miles
        assert abs(route.distance_miles - 6.21371) < 0.001

    def test_route_distance_miles_zero(self, db):
        """Test distance miles with zero distance."""
        route = Route.objects.create(name="Test Route", distance_km=0)
        assert route.distance_miles == 0

    def test_route_estimated_time_short(self, db):
        """Test estimated time for short routes (< 1 hour)."""
        # 6 miles at 12 mph = 0.5 hours = 30 minutes
        route = Route.objects.create(name="Short Route", distance_km=9.656064)
        assert route.estimated_time == "30m"

    def test_route_estimated_time_exact_hour(self, db):
        """Test estimated time for exactly 1 hour."""
        # 12 miles at 12 mph = 1 hour
        route = Route.objects.create(name="One Hour Route", distance_km=19.312128)
        assert route.estimated_time == "1h"

    def test_route_estimated_time_hours_and_minutes(self, db):
        """Test estimated time with hours and minutes."""
        # 15 miles at 12 mph = 1.25 hours = 1h 15m
        route = Route.objects.create(name="Medium Route", distance_km=24.14016)
        assert route.estimated_time == "1h 15m"

    def test_route_estimated_time_long(self, db):
        """Test estimated time for long routes."""
        # 50 miles at 12 mph = 4.17 hours = 4h 10m
        route = Route.objects.create(name="Long Route", distance_km=80.4672)
        assert route.estimated_time == "4h 10m"

    def test_route_estimated_time_zero_distance(self, db):
        """Test estimated time with zero distance."""
        route = Route.objects.create(name="Zero Route", distance_km=0)
        assert route.estimated_time == "N/A"

    def test_route_get_absolute_url(self, db):
        """Test get_absolute_url method."""
        route = Route.objects.create(name="Test Route")
        url = route.get_absolute_url()
        assert url == f"/route/{route.pk}/"

    def test_route_get_share_url(self, db):
        """Test get_share_url method."""
        route = Route.objects.create(name="Test Route")
        url = route.get_share_url()
        assert url == f"/share/{route.share_token}/"

    def test_route_with_coordinates(self, db):
        """Test route with coordinate data."""
        coords = [[51.5074, -0.1278], [51.5084, -0.1268], [51.5094, -0.1258]]
        route = Route.objects.create(
            name="Test Route",
            route_coordinates=coords,
            start_lat=51.5074,
            start_lon=-0.1278,
        )
        assert route.route_coordinates == coords
        assert route.start_lat == 51.5074
        assert route.start_lon == -0.1278

    def test_route_with_tags(self, db):
        """Test route with multiple tags."""
        route = Route.objects.create(name="Tagged Route")
        tag1 = Tag.objects.create(name="Hiking")
        tag2 = Tag.objects.create(name="Mountain")

        route.tags.add(tag1, tag2)

        assert route.tags.count() == 2
        assert tag1 in route.tags.all()
        assert tag2 in route.tags.all()

    def test_route_ordering(self, db):
        """Test that routes are ordered by uploaded_at descending."""
        import time

        Route.objects.create(name="First Route")
        time.sleep(0.01)  # Ensure different timestamps
        Route.objects.create(name="Second Route")
        time.sleep(0.01)
        Route.objects.create(name="Third Route")

        routes = list(Route.objects.all())
        assert routes[0].name == "Third Route"  # Most recent first
        assert routes[1].name == "Second Route"
        assert routes[2].name == "First Route"

    def test_route_gpx_file_url_property(self, db):
        """Test gpx_file_url property when no file is present."""
        route = Route.objects.create(name="Test Route")
        assert route.gpx_file_url == ""

    def test_route_thumbnail_url_property(self, db):
        """Test thumbnail_url property when no thumbnail is present."""
        route = Route.objects.create(name="Test Route")
        assert route.thumbnail_url == ""

    def test_route_elevation_gain(self, db):
        """Test route with elevation gain."""
        route = Route.objects.create(
            name="Mountain Route", distance_km=20.0, elevation_gain=500.0
        )
        assert route.elevation_gain == 500.0

    def test_route_custom_share_token(self, db):
        """Test that custom share tokens are preserved."""
        route = Route.objects.create(
            name="Custom Token Route", share_token="customtoken12345"
        )
        assert route.share_token == "customtoken12345"

    def test_route_very_long_distance(self, db):
        """Test route with very long distance."""
        # Ultra marathon distance
        route = Route.objects.create(name="Ultra Route", distance_km=160.934)
        assert route.distance_miles > 100
        # At 12 mph this should be > 8 hours
        assert "h" in route.estimated_time
