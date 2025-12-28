"""
Tests for routes async tasks.

Note: These tests use the immediate backend for django-tasks (configured in settings_test.py)
so tasks run synchronously during tests. We call the task function directly.
"""

from django.test import TestCase
from unittest.mock import patch, MagicMock
from routes.tasks import process_route_async
from routes.models import Route, StartPoint
from django.core.files.base import ContentFile


class ProcessRouteAsyncTest(TestCase):
    """Tests for process_route_async task."""

    @patch("routes.tasks.find_closest_start_point")
    @patch("routes.tasks.generate_static_map_image")
    def test_process_route_with_start_point_match(
        self, mock_generate_thumb, mock_find_start
    ):
        """Test processing route that matches a start point."""
        # Create a route
        route = Route.objects.create(
            name="Test Route",
            distance_km=10,
            start_lat=52.4603,
            start_lon=-2.1638,
            route_coordinates=[[52.4603, -2.1638], [52.4613, -2.1628]],
        )

        # Create a start point
        start_point = StartPoint.objects.create(
            name="Test Start Location", latitude=52.4603, longitude=-2.1638
        )

        # Mock find_closest_start_point to return our start point
        mock_find_start.return_value = start_point

        # Mock thumbnail generation
        mock_generate_thumb.return_value = ContentFile(b"fake image", name="test.webp")

        # Run the task (will execute immediately)
        result = process_route_async(route.id)

        # Verify start location was set
        route.refresh_from_db()
        self.assertEqual(route.start_location, "Test Start Location")

        # Verify thumbnail was generated
        self.assertTrue(route.thumbnail_image)

        # Verify result message
        self.assertIn("Successfully processed", result)

    @patch("routes.tasks.get_location_name")
    @patch("routes.tasks.find_closest_start_point")
    @patch("routes.tasks.generate_static_map_image")
    def test_process_route_with_geocoding_fallback(
        self, mock_generate_thumb, mock_find_start, mock_geocode
    ):
        """Test processing route with geocoding API fallback."""
        route = Route.objects.create(
            name="Test Route",
            distance_km=10,
            start_lat=52.4603,
            start_lon=-2.1638,
            route_coordinates=[[52.4603, -2.1638], [52.4613, -2.1628]],
        )

        # No start point match
        mock_find_start.return_value = None

        # Mock geocoding API
        mock_geocode.return_value = "Birmingham, England"

        # Mock thumbnail generation
        mock_generate_thumb.return_value = ContentFile(b"fake image", name="test.webp")

        # Run the task
        result = process_route_async(route.id)

        # Verify geocoded location was set
        route.refresh_from_db()
        self.assertEqual(route.start_location, "Birmingham, England")

        # Verify geocoding was called
        self.assertTrue(mock_geocode.called)

    @patch("routes.tasks.find_closest_start_point")
    @patch("routes.tasks.generate_static_map_image")
    def test_thumbnail_generation(self, mock_generate_thumb, mock_find_start):
        """Test thumbnail generation during task."""
        route = Route.objects.create(
            name="Test Route",
            distance_km=10,
            start_lat=52.4603,
            start_lon=-2.1638,
            route_coordinates=[[52.4603, -2.1638], [52.4613, -2.1628]],
        )

        mock_find_start.return_value = None

        # Mock thumbnail generation
        fake_thumbnail = ContentFile(b"fake image data", name="test.webp")
        mock_generate_thumb.return_value = fake_thumbnail

        # Run the task
        process_route_async(route.id)

        # Verify thumbnail was saved
        route.refresh_from_db()
        self.assertTrue(route.thumbnail_image)
        self.assertIn(".webp", route.thumbnail_image.name)

    @patch("routes.tasks.find_closest_start_point")
    @patch("routes.tasks.generate_static_map_image")
    def test_thumbnail_generation_failure(self, mock_generate_thumb, mock_find_start):
        """Test handling thumbnail generation failure."""
        route = Route.objects.create(
            name="Test Route",
            distance_km=10,
            start_lat=52.4603,
            start_lon=-2.1638,
            route_coordinates=[[52.4603, -2.1638], [52.4613, -2.1628]],
        )

        mock_find_start.return_value = None

        # Thumbnail generation returns None (failure)
        mock_generate_thumb.return_value = None

        # Run the task - should not crash
        result = process_route_async(route.id)

        # Should still complete successfully
        self.assertIn("Successfully processed", result)

        # Thumbnail should still be empty
        route.refresh_from_db()
        self.assertFalse(route.thumbnail_image)

    def test_route_not_found(self):
        """Test handling non-existent route."""
        result = process_route_async(99999)

        self.assertIn("not found", result)

    @patch("routes.tasks.find_closest_start_point")
    @patch("routes.tasks.generate_static_map_image")
    def test_skip_if_location_already_set(self, mock_generate_thumb, mock_find_start):
        """Test that geocoding is skipped if location already set."""
        route = Route.objects.create(
            name="Test Route",
            distance_km=10,
            start_lat=52.4603,
            start_lon=-2.1638,
            start_location="Already Set Location",  # Already has location
            route_coordinates=[[52.4603, -2.1638]],
        )

        mock_generate_thumb.return_value = ContentFile(b"fake", name="test.webp")

        # Run the task
        process_route_async(route.id)

        # find_closest_start_point should NOT be called
        self.assertFalse(mock_find_start.called)

        # Location should remain unchanged
        route.refresh_from_db()
        self.assertEqual(route.start_location, "Already Set Location")

    @patch("routes.tasks.find_closest_start_point")
    @patch("routes.tasks.generate_static_map_image")
    def test_skip_thumbnail_if_exists(self, mock_generate_thumb, mock_find_start):
        """Test that thumbnail generation is skipped if already exists."""
        route = Route.objects.create(
            name="Test Route",
            distance_km=10,
            start_lat=52.4603,
            start_lon=-2.1638,
            route_coordinates=[[52.4603, -2.1638]],
        )
        # Set existing thumbnail
        route.thumbnail_image.save("existing.webp", ContentFile(b"existing"), save=True)

        mock_find_start.return_value = None

        # Run the task
        process_route_async(route.id)

        # generate_static_map_image should NOT be called
        self.assertFalse(mock_generate_thumb.called)

    @patch("routes.tasks.find_closest_start_point")
    @patch("routes.tasks.generate_static_map_image")
    def test_task_handles_exceptions(self, mock_generate_thumb, mock_find_start):
        """Test that task handles exceptions gracefully."""
        route = Route.objects.create(
            name="Test Route",
            distance_km=10,
            start_lat=52.4603,
            start_lon=-2.1638,
            route_coordinates=[[52.4603, -2.1638]],
        )

        # Make find_closest_start_point raise an exception
        mock_find_start.side_effect = Exception("Test exception")

        # Task should not crash
        result = process_route_async(route.id)

        # Should return error message
        self.assertIn("Error processing", result)
