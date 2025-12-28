"""
Tests for routes service layer.
"""

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
from routes.services import create_route_from_gpx
from routes.models import Route, Tag
from pathlib import Path


def get_fixture_path(filename):
    """Get the full path to a test fixture file."""
    return Path(__file__).parent / "fixtures" / filename


class CreateRouteFromGPXTest(TestCase):
    """Tests for create_route_from_gpx service function."""

    @patch("routes.services.process_route_async")
    def test_create_route_with_name_and_tags(self, mock_task):
        """Test creating a route with explicit name and tags."""
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        route = create_route_from_gpx(
            gpx_file, name="My Custom Route", tag_names=["hiking", "mountain"]
        )

        # Verify route was created
        self.assertIsNotNone(route)
        self.assertEqual(route.name, "My Custom Route")
        self.assertGreater(route.distance_km, 0)
        self.assertIsNotNone(route.start_lat)
        self.assertIsNotNone(route.start_lon)
        self.assertGreater(len(route.route_coordinates), 0)

        # Verify tags were created and associated
        self.assertEqual(route.tags.count(), 2)
        tag_names = [tag.name for tag in route.tags.all()]
        self.assertIn("Hiking", tag_names)  # Tags are normalized
        self.assertIn("Mountain", tag_names)

        # Verify async task was queued
        self.assertTrue(mock_task.enqueue.called)
        self.assertEqual(mock_task.enqueue.call_args[0][0], route.id)

    @patch("routes.services.process_route_async")
    def test_create_route_without_name_uses_gpx_metadata(self, mock_task):
        """Test creating route without name uses GPX metadata."""
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        route = create_route_from_gpx(gpx_file)

        # Should use name from GPX file
        self.assertIsNotNone(route.name)
        self.assertEqual(route.name, "Sample Track")

    @patch("routes.services.process_route_async")
    def test_create_route_without_name_uses_filename(self, mock_task):
        """Test creating route without name or GPX metadata uses filename."""
        path = get_fixture_path("waypoints_only.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "my_route.gpx", f.read(), content_type="application/gpx+xml"
            )

        route = create_route_from_gpx(gpx_file)

        # Should use filename without .gpx extension
        self.assertEqual(route.name, "my_route")

    @patch("routes.services.process_route_async")
    def test_create_route_without_tags(self, mock_task):
        """Test creating route without tags."""
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        route = create_route_from_gpx(gpx_file, name="Test Route")

        self.assertEqual(route.tags.count(), 0)

    @patch("routes.services.process_route_async")
    def test_gpx_file_saved_to_storage(self, mock_task):
        """Test that GPX file is saved to storage."""
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        route = create_route_from_gpx(gpx_file, name="Test Route")

        # Verify file was saved (Django may append random chars to filename)
        self.assertTrue(route.gpx_file)
        self.assertTrue("sample_track" in route.gpx_file.name)
        self.assertTrue(route.gpx_file.name.endswith(".gpx"))

    @patch("routes.services.process_route_async")
    def test_invalid_gpx_raises_error(self, mock_task):
        """Test that invalid GPX raises ValueError."""
        invalid_gpx = SimpleUploadedFile(
            "invalid.gpx", b"not valid gpx", content_type="application/gpx+xml"
        )

        with self.assertRaises(Exception):
            create_route_from_gpx(invalid_gpx, name="Test Route")

    @patch("routes.services.process_route_async")
    def test_tags_created_if_not_exist(self, mock_task):
        """Test that new tags are created if they don't exist."""
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        # Ensure tags don't exist
        self.assertFalse(Tag.objects.filter(name="NewTag1").exists())
        self.assertFalse(Tag.objects.filter(name="NewTag2").exists())

        route = create_route_from_gpx(
            gpx_file, name="Test Route", tag_names=["NewTag1", "NewTag2"]
        )

        # Verify tags were created
        self.assertTrue(Tag.objects.filter(name="Newtag1").exists())
        self.assertTrue(Tag.objects.filter(name="Newtag2").exists())
        self.assertEqual(route.tags.count(), 2)

    @patch("routes.services.process_route_async")
    def test_existing_tags_reused(self, mock_task):
        """Test that existing tags are reused, not duplicated."""
        # Create tag beforehand
        existing_tag = Tag.objects.create(name="Hiking")

        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        route = create_route_from_gpx(gpx_file, name="Test Route", tag_names=["hiking"])

        # Should have only 1 Hiking tag in database
        self.assertEqual(Tag.objects.filter(name="Hiking").count(), 1)
        self.assertEqual(route.tags.count(), 1)
        self.assertIn(existing_tag, route.tags.all())

    @patch("routes.services.process_route_async")
    def test_whitespace_in_tag_names_handled(self, mock_task):
        """Test that whitespace in tag names is handled correctly."""
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        route = create_route_from_gpx(
            gpx_file, name="Test Route", tag_names=["  hiking  ", "", "mountain"]
        )

        # Empty strings should be skipped
        self.assertEqual(route.tags.count(), 2)
        tag_names = [tag.name for tag in route.tags.all()]
        self.assertIn("Hiking", tag_names)
        self.assertIn("Mountain", tag_names)
