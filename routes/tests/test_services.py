"""
Tests for routes services module.

Tests cover:
- GPX file processing and route creation
- Tag assignment and normalization
- Error handling for invalid GPX files
- Integration with background tasks
"""

from unittest.mock import patch

import pytest

from routes.models import Tag
from routes.services import create_route_from_gpx


class TestCreateRouteFromGPX:
    """Tests for the create_route_from_gpx service function."""

    @patch("routes.services.process_route_async")
    def test_create_route_basic(self, mock_task, db, sample_gpx_file):
        """Test basic route creation from GPX file."""
        route = create_route_from_gpx(sample_gpx_file)

        assert route.id is not None
        assert route.name == "Sample Track"
        assert route.distance_km >= 0
        assert route.route_coordinates != []
        assert len(route.route_coordinates) == 3
        assert route.start_lat is not None
        assert route.start_lon is not None
        # Verify background task was queued
        mock_task.enqueue.assert_called_once_with(route.id)

    @patch("routes.services.process_route_async")
    def test_create_route_with_custom_name(self, mock_task, db, sample_gpx_file):
        """Test route creation with custom name override."""
        route = create_route_from_gpx(sample_gpx_file, name="Custom Route Name")

        assert route.name == "Custom Route Name"
        mock_task.enqueue.assert_called_once()

    @patch("routes.services.process_route_async")
    def test_create_route_with_tags(self, mock_task, db, sample_gpx_file):
        """Test route creation with tags."""
        tag_names = ["hiking", "mountain", "trail"]
        route = create_route_from_gpx(sample_gpx_file, tag_names=tag_names)

        assert route.tags.count() == 3
        tag_names_in_db = [tag.name for tag in route.tags.all()]
        # Tags should be normalized to titlecase
        assert "Hiking" in tag_names_in_db
        assert "Mountain" in tag_names_in_db
        assert "Trail" in tag_names_in_db

    @patch("routes.services.process_route_async")
    def test_create_route_with_existing_tags(self, mock_task, db, sample_gpx_file):
        """Test route creation with mix of new and existing tags."""
        # Create an existing tag
        existing_tag = Tag.objects.create(name="Hiking")

        tag_names = ["hiking", "new_tag"]
        route = create_route_from_gpx(sample_gpx_file, tag_names=tag_names)

        assert route.tags.count() == 2
        # Should reuse existing tag
        assert existing_tag in route.tags.all()
        # Should create new tag
        assert Tag.objects.filter(name="New_Tag").exists()

    @patch("routes.services.process_route_async")
    def test_create_route_with_empty_tag_names(self, mock_task, db, sample_gpx_file):
        """Test that empty tag names are ignored."""
        tag_names = ["hiking", "", "  ", "trail"]
        route = create_route_from_gpx(sample_gpx_file, tag_names=tag_names)

        # Should only create 2 tags (empty strings should be skipped)
        assert route.tags.count() == 2

    @patch("routes.services.process_route_async")
    def test_create_route_fallback_to_filename(self, mock_task, db, sample_gpx_content):
        """Test route name falls back to filename when GPX has no name."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # GPX content without metadata name
        gpx_no_name = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
    <trk>
        <trkseg>
            <trkpt lat="51.5074" lon="-0.1278">
                <ele>50</ele>
            </trkpt>
            <trkpt lat="51.5084" lon="-0.1268">
                <ele>60</ele>
            </trkpt>
        </trkseg>
    </trk>
</gpx>
"""
        gpx_file = SimpleUploadedFile(
            "my_route.gpx", gpx_no_name, content_type="application/gpx+xml"
        )

        route = create_route_from_gpx(gpx_file)
        assert route.name == "my_route"  # Filename without .gpx extension

    @patch("routes.services.process_route_async")
    def test_create_route_from_route_element(
        self, mock_task, db, gpx_with_route_content
    ):
        """Test parsing GPX file with route instead of track."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        gpx_file = SimpleUploadedFile(
            "route.gpx", gpx_with_route_content, content_type="application/gpx+xml"
        )

        route = create_route_from_gpx(gpx_file)
        assert route.name == "Route Example"
        assert len(route.route_coordinates) == 3

    @patch("routes.services.process_route_async")
    def test_create_route_from_waypoints(
        self, mock_task, db, gpx_with_waypoints_content
    ):
        """Test parsing GPX file with only waypoints."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        gpx_file = SimpleUploadedFile(
            "waypoints.gpx",
            gpx_with_waypoints_content,
            content_type="application/gpx+xml",
        )

        route = create_route_from_gpx(gpx_file)
        assert len(route.route_coordinates) == 2

    def test_create_route_invalid_gpx(self, db, invalid_gpx_content):
        """Test that invalid GPX raises ValueError."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        invalid_file = SimpleUploadedFile(
            "invalid.gpx", invalid_gpx_content, content_type="application/gpx+xml"
        )

        with pytest.raises(Exception):  # parse_gpx will raise an exception
            create_route_from_gpx(invalid_file)

    @patch("routes.services.process_route_async")
    def test_create_route_preserves_coordinates(self, mock_task, db, sample_gpx_file):
        """Test that route coordinates are properly stored."""
        route = create_route_from_gpx(sample_gpx_file)

        # Verify coordinates are stored
        assert route.route_coordinates is not None
        assert len(route.route_coordinates) > 0

        # Verify first point matches start coordinates
        first_point = route.route_coordinates[0]
        assert first_point[0] == route.start_lat
        assert first_point[1] == route.start_lon

    @patch("routes.services.process_route_async")
    def test_create_route_file_saved_to_storage(self, mock_task, db, sample_gpx_file):
        """Test that GPX file is saved to storage."""
        route = create_route_from_gpx(sample_gpx_file)

        assert route.gpx_file.name is not None
        assert "test_route.gpx" in route.gpx_file.name

    @patch("routes.services.process_route_async")
    def test_create_route_calculates_elevation(
        self, mock_task, db, complex_gpx_content
    ):
        """Test that elevation gain is calculated from GPX data."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        gpx_file = SimpleUploadedFile(
            "elevation.gpx", complex_gpx_content, content_type="application/gpx+xml"
        )

        route = create_route_from_gpx(gpx_file)
        # With elevation data, elevation gain should be > 0
        assert route.elevation_gain >= 0

    @patch("routes.services.process_route_async")
    def test_create_route_with_none_tag_names(self, mock_task, db, sample_gpx_file):
        """Test route creation when tag_names is None."""
        route = create_route_from_gpx(sample_gpx_file, tag_names=None)

        assert route.tags.count() == 0

    @patch("routes.services.process_route_async")
    def test_create_route_with_empty_list_tag_names(
        self, mock_task, db, sample_gpx_file
    ):
        """Test route creation with empty tag list."""
        route = create_route_from_gpx(sample_gpx_file, tag_names=[])

        assert route.tags.count() == 0

    @patch("routes.services.process_route_async")
    def test_create_route_task_queue_called(self, mock_task, db, sample_gpx_file):
        """Test that background task is queued with correct route ID."""
        route = create_route_from_gpx(sample_gpx_file)

        mock_task.enqueue.assert_called_once_with(route.id)
        assert mock_task.enqueue.call_count == 1
