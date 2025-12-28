"""
Tests for management commands.
"""

from io import StringIO
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase

from routes.models import Route, StartPoint


class RegenerateThumbnailsCommandTest(TestCase):
    """Tests for regenerate_thumbnails management command."""

    @patch("routes.management.commands.regenerate_thumbnails.generate_static_map_image")
    def test_default_mode_existing_thumbnails(self, mock_generate):
        """Test default mode regenerates routes with existing thumbnails."""
        # Route with thumbnail
        route1 = Route.objects.create(
            name="Route 1", route_coordinates=[[52.4603, -2.1638]]
        )
        route1.thumbnail_image.save("old.webp", ContentFile(b"old"), save=True)

        # Route without thumbnail
        Route.objects.create(name="Route 2", route_coordinates=[[52.4603, -2.1638]])

        mock_generate.return_value = ContentFile(b"new image", name="new.webp")

        out = StringIO()
        call_command("regenerate_thumbnails", stdout=out)

        # Should regenerate route1, skip route2
        self.assertEqual(mock_generate.call_count, 1)

    @patch("routes.management.commands.regenerate_thumbnails.generate_static_map_image")
    def test_all_flag(self, mock_generate):
        """Test --all flag regenerates all routes."""
        Route.objects.create(name="Route 1", route_coordinates=[[52.4603, -2.1638]])
        Route.objects.create(name="Route 2", route_coordinates=[[52.4613, -2.1628]])

        mock_generate.return_value = ContentFile(b"new image", name="new.webp")

        out = StringIO()
        call_command("regenerate_thumbnails", "--all", stdout=out)

        # Should regenerate both routes
        self.assertEqual(mock_generate.call_count, 2)

    @patch("routes.management.commands.regenerate_thumbnails.generate_static_map_image")
    def test_force_flag(self, mock_generate):
        """Test --force flag regenerates all routes."""
        route1 = Route.objects.create(
            name="Route 1", route_coordinates=[[52.4603, -2.1638]]
        )
        route1.thumbnail_image.save("old.webp", ContentFile(b"old"), save=True)

        Route.objects.create(name="Route 2", route_coordinates=[[52.4613, -2.1628]])

        mock_generate.return_value = ContentFile(b"new image", name="new.webp")

        out = StringIO()
        call_command("regenerate_thumbnails", "--force", stdout=out)

        # Should regenerate both routes
        self.assertEqual(mock_generate.call_count, 2)

    @patch("routes.management.commands.regenerate_thumbnails.generate_static_map_image")
    def test_dry_run_flag(self, mock_generate):
        """Test --dry-run flag doesn't make changes."""
        route = Route.objects.create(
            name="Route 1", route_coordinates=[[52.4603, -2.1638]]
        )
        route.thumbnail_image.save("old.webp", ContentFile(b"old"), save=True)

        out = StringIO()
        call_command("regenerate_thumbnails", "--dry-run", stdout=out)

        # Should not call generate_static_map_image
        self.assertEqual(mock_generate.call_count, 0)

        # Output should indicate dry run
        output = out.getvalue()
        self.assertIn("DRY RUN", output)

    @patch("routes.management.commands.regenerate_thumbnails.generate_static_map_image")
    def test_route_id_specific_route(self, mock_generate):
        """Test --route-id flag regenerates specific route."""
        route1 = Route.objects.create(
            name="Route 1", route_coordinates=[[52.4603, -2.1638]]
        )
        route1.thumbnail_image.save("old.webp", ContentFile(b"old"), save=True)

        Route.objects.create(name="Route 2", route_coordinates=[[52.4613, -2.1628]])

        mock_generate.return_value = ContentFile(b"new image", name="new.webp")

        out = StringIO()
        call_command("regenerate_thumbnails", f"--route-id={route1.id}", stdout=out)

        # Should only regenerate route1
        self.assertEqual(mock_generate.call_count, 1)

    def test_route_id_not_found(self):
        """Test --route-id with non-existent route."""
        out = StringIO()
        call_command("regenerate_thumbnails", "--route-id=99999", stdout=out)

        output = out.getvalue()
        self.assertIn("not found", output)

    @patch("routes.management.commands.regenerate_thumbnails.generate_static_map_image")
    def test_skip_routes_without_coordinates(self, mock_generate):
        """Test that routes without coordinates are skipped."""
        Route.objects.create(name="No Coords", route_coordinates=[])

        out = StringIO()
        call_command("regenerate_thumbnails", "--all", stdout=out)

        # Should not try to generate
        self.assertEqual(mock_generate.call_count, 0)

    @patch("routes.management.commands.regenerate_thumbnails.generate_static_map_image")
    def test_error_handling(self, mock_generate):
        """Test error handling when thumbnail generation fails."""
        Route.objects.create(name="Route 1", route_coordinates=[[52.4603, -2.1638]])

        # Simulate generation failure
        mock_generate.side_effect = Exception("Generation failed")

        out = StringIO()
        call_command("regenerate_thumbnails", "--all", stdout=out)

        output = out.getvalue()
        self.assertIn("Error", output)

    @patch("routes.management.commands.regenerate_thumbnails.generate_static_map_image")
    def test_summary_output(self, mock_generate):
        """Test that command outputs summary."""
        Route.objects.create(name="Route 1", route_coordinates=[[52.4603, -2.1638]])
        Route.objects.create(name="Route 2", route_coordinates=[[52.4613, -2.1628]])

        mock_generate.return_value = ContentFile(b"new image", name="new.webp")

        out = StringIO()
        call_command("regenerate_thumbnails", "--all", stdout=out)

        output = out.getvalue()
        self.assertIn("Summary", output)
        self.assertIn("Successfully regenerated: 2", output)


class UpdateStartLocationsCommandTest(TestCase):
    """Tests for update_start_locations management command."""

    @patch("routes.management.commands.update_start_locations.find_closest_start_point")
    def test_default_mode_empty_locations(self, mock_find):
        """Test default mode processes routes without start_location."""
        route1 = Route.objects.create(
            name="Route 1",
            start_lat=52.4603,
            start_lon=-2.1638,
            start_location="",  # Empty location
        )
        Route.objects.create(
            name="Route 2",
            start_lat=52.4613,
            start_lon=-2.1628,
            start_location="Already Set",  # Has location
        )

        start_point = StartPoint.objects.create(
            name="Test Point", latitude=52.4603, longitude=-2.1638
        )
        mock_find.return_value = start_point

        out = StringIO()
        call_command("update_start_locations", stdout=out)

        # Should only process route1
        self.assertEqual(mock_find.call_count, 1)

        route1.refresh_from_db()
        self.assertEqual(route1.start_location, "Test Point")

    @patch("routes.management.commands.update_start_locations.find_closest_start_point")
    def test_all_flag(self, mock_find):
        """Test --all flag processes all routes."""
        Route.objects.create(
            name="Route 1", start_lat=52.4603, start_lon=-2.1638, start_location=""
        )
        Route.objects.create(
            name="Route 2",
            start_lat=52.4613,
            start_lon=-2.1628,
            start_location="Already Set",
        )

        start_point = StartPoint.objects.create(
            name="Test Point", latitude=52.4603, longitude=-2.1638
        )
        mock_find.return_value = start_point

        out = StringIO()
        call_command("update_start_locations", "--all", stdout=out)

        # Should process both routes
        self.assertEqual(mock_find.call_count, 2)

    @patch("routes.management.commands.update_start_locations.get_location_name")
    @patch("routes.management.commands.update_start_locations.find_closest_start_point")
    def test_force_geocode_flag(self, mock_find, mock_geocode):
        """Test --force-geocode flag uses API when no start point match."""
        route = Route.objects.create(
            name="Route 1", start_lat=52.4603, start_lon=-2.1638, start_location=""
        )

        # No start point match
        mock_find.return_value = None
        mock_geocode.return_value = "Birmingham, England"

        out = StringIO()
        call_command("update_start_locations", "--force-geocode", stdout=out)

        # Should call geocoding API
        self.assertTrue(mock_geocode.called)

        route.refresh_from_db()
        self.assertEqual(route.start_location, "Birmingham, England")

    @patch("routes.management.commands.update_start_locations.find_closest_start_point")
    def test_dry_run_flag(self, mock_find):
        """Test --dry-run flag doesn't save changes."""
        route = Route.objects.create(
            name="Route 1", start_lat=52.4603, start_lon=-2.1638, start_location=""
        )

        start_point = StartPoint.objects.create(
            name="Test Point", latitude=52.4603, longitude=-2.1638
        )
        mock_find.return_value = start_point

        out = StringIO()
        call_command("update_start_locations", "--dry-run", stdout=out)

        # Location should not be updated
        route.refresh_from_db()
        self.assertEqual(route.start_location, "")

        # Output should indicate dry run
        output = out.getvalue()
        self.assertIn("DRY RUN", output)

    @patch("routes.management.commands.update_start_locations.find_closest_start_point")
    def test_skip_routes_without_coordinates(self, mock_find):
        """Test that routes without coordinates are skipped."""
        Route.objects.create(
            name="No Coords", start_lat=None, start_lon=None, start_location=""
        )

        out = StringIO()
        call_command("update_start_locations", stdout=out)

        # Should not process this route
        self.assertEqual(mock_find.call_count, 0)

        output = out.getvalue()
        self.assertIn("0 routes", output)

    @patch("routes.management.commands.update_start_locations.find_closest_start_point")
    def test_coordinate_string_detection(self, mock_find):
        """Test detection of coordinate strings vs proper location names."""
        Route.objects.create(
            name="Route 1",
            start_lat=52.4603,
            start_lon=-2.1638,
            start_location="52.4603, -2.1638",  # Coordinate string
        )
        Route.objects.create(
            name="Route 2",
            start_lat=52.4613,
            start_lon=-2.1628,
            start_location="Birmingham",  # Proper location
        )

        start_point = StartPoint.objects.create(
            name="Test Point", latitude=52.4603, longitude=-2.1638
        )
        mock_find.return_value = start_point

        out = StringIO()
        call_command("update_start_locations", "--all", stdout=out)

        # Should process both routes
        self.assertEqual(mock_find.call_count, 2)

    @patch("routes.management.commands.update_start_locations.find_closest_start_point")
    def test_summary_output(self, mock_find):
        """Test that command outputs summary."""
        Route.objects.create(
            name="Route 1", start_lat=52.4603, start_lon=-2.1638, start_location=""
        )
        Route.objects.create(
            name="Route 2", start_lat=52.4613, start_lon=-2.1628, start_location=""
        )

        start_point = StartPoint.objects.create(
            name="Test Point", latitude=52.4603, longitude=-2.1638
        )
        mock_find.return_value = start_point

        out = StringIO()
        call_command("update_start_locations", stdout=out)

        output = out.getvalue()
        self.assertIn("Summary", output)
        self.assertIn("Matched to start points:", output)

    @patch("routes.management.commands.update_start_locations.find_closest_start_point")
    def test_error_handling(self, mock_find):
        """Test error handling when processing fails."""
        Route.objects.create(
            name="Route 1", start_lat=52.4603, start_lon=-2.1638, start_location=""
        )

        # Simulate error
        mock_find.side_effect = Exception("Processing failed")

        out = StringIO()
        call_command("update_start_locations", stdout=out)

        output = out.getvalue()
        self.assertIn("Error", output)
