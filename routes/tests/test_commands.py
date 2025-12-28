"""
Tests for management commands.

Tests cover:
- regenerate_thumbnails command with various options
- update_start_locations command with geocoding
- Dry-run mode and error handling
- Edge cases and command arguments
"""

from io import StringIO
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command

from routes.models import Route, StartPoint


@pytest.mark.django_db
class TestRegenerateThumbnailsCommand:
    """Tests for the regenerate_thumbnails management command."""

    def test_regenerate_thumbnails_no_routes(self):
        """Test command with no routes to process."""
        out = StringIO()
        call_command("regenerate_thumbnails", stdout=out)

        output = out.getvalue()
        assert "No routes to process" in output

    @patch("routes.management.commands.regenerate_thumbnails.generate_static_map_image")
    def test_regenerate_thumbnails_with_route_id(self, mock_generate):
        """Test regenerating thumbnail for specific route ID."""
        mock_generate.return_value = Mock()

        coords = [[51.5074, -0.1278], [51.5084, -0.1268]]
        route_obj = Route.objects.create(name="Test Route", route_coordinates=coords)

        out = StringIO()
        call_command(
            "regenerate_thumbnails",
            route_id=route_obj.id,
            stdout=out,
        )

        output = out.getvalue()
        assert f"Processing route #{route_obj.id}" in output
        mock_generate.assert_called_once()

    def test_regenerate_thumbnails_route_id_not_found(self):
        """Test command with non-existent route ID."""
        out = StringIO()
        call_command("regenerate_thumbnails", route_id=99999, stdout=out)

        output = out.getvalue()
        assert "not found" in output

    @patch("routes.management.commands.regenerate_thumbnails.generate_static_map_image")
    def test_regenerate_thumbnails_all_routes(self, mock_generate):
        """Test regenerating all routes with --all flag."""
        mock_generate.return_value = Mock()

        coords = [[51.5074, -0.1278], [51.5084, -0.1268]]
        Route.objects.create(name="Route 1", route_coordinates=coords)
        Route.objects.create(name="Route 2", route_coordinates=coords)

        out = StringIO()
        call_command("regenerate_thumbnails", all=True, stdout=out)

        output = out.getvalue()
        assert "Processing all" in output
        assert mock_generate.call_count == 2

    @patch("routes.management.commands.regenerate_thumbnails.generate_static_map_image")
    def test_regenerate_thumbnails_dry_run(self, mock_generate):
        """Test dry-run mode doesn't make changes."""
        mock_generate.return_value = Mock()

        coords = [[51.5074, -0.1278], [51.5084, -0.1268]]
        Route.objects.create(name="Test Route", route_coordinates=coords)

        out = StringIO()
        call_command("regenerate_thumbnails", all=True, dry_run=True, stdout=out)

        output = out.getvalue()
        assert "DRY RUN" in output
        assert "Would regenerate thumbnail" in output
        # Should not actually call generate function in dry run
        mock_generate.assert_not_called()

    def test_regenerate_thumbnails_route_without_coordinates(self):
        """Test command skips routes without coordinates."""
        Route.objects.create(name="No Coords", route_coordinates=[])

        out = StringIO()
        call_command("regenerate_thumbnails", all=True, stdout=out)

        output = out.getvalue()
        # Should process 0 routes
        assert "Skipped: 1" in output or "No routes to process" in output

    @patch("routes.management.commands.regenerate_thumbnails.generate_static_map_image")
    def test_regenerate_thumbnails_force_flag(self, mock_generate):
        """Test --force flag regenerates even existing thumbnails."""
        mock_generate.return_value = Mock()

        coords = [[51.5074, -0.1278], [51.5084, -0.1268]]
        Route.objects.create(
            name="Has Thumbnail",
            route_coordinates=coords,
            thumbnail_image="old_thumb.webp",
        )

        out = StringIO()
        call_command("regenerate_thumbnails", force=True, stdout=out)

        output = out.getvalue()
        assert "Successfully regenerated: 1" in output
        mock_generate.assert_called_once()

    @patch("routes.management.commands.regenerate_thumbnails.generate_static_map_image")
    def test_regenerate_thumbnails_generation_failure(self, mock_generate):
        """Test handling of thumbnail generation failure."""
        mock_generate.return_value = None  # Simulate failure

        coords = [[51.5074, -0.1278], [51.5084, -0.1268]]
        Route.objects.create(name="Test Route", route_coordinates=coords)

        out = StringIO()
        call_command("regenerate_thumbnails", all=True, stdout=out)

        output = out.getvalue()
        assert "Failed to generate thumbnail" in output
        assert "Errors: 1" in output

    @patch("routes.management.commands.regenerate_thumbnails.generate_static_map_image")
    def test_regenerate_thumbnails_exception_handling(self, mock_generate):
        """Test command handles exceptions gracefully."""
        mock_generate.side_effect = Exception("Generation error")

        coords = [[51.5074, -0.1278], [51.5084, -0.1268]]
        Route.objects.create(name="Test Route", route_coordinates=coords)

        out = StringIO()
        call_command("regenerate_thumbnails", all=True, stdout=out)

        output = out.getvalue()
        assert "Error" in output
        assert "Errors: 1" in output

    @patch("routes.management.commands.regenerate_thumbnails.generate_static_map_image")
    def test_regenerate_thumbnails_summary_output(self, mock_generate):
        """Test command outputs correct summary."""
        mock_generate.return_value = Mock()

        coords = [[51.5074, -0.1278], [51.5084, -0.1268]]
        Route.objects.create(name="Route 1", route_coordinates=coords)
        Route.objects.create(name="Route 2", route_coordinates=coords)
        Route.objects.create(name="No Coords", route_coordinates=[])

        out = StringIO()
        call_command("regenerate_thumbnails", all=True, stdout=out)

        output = out.getvalue()
        assert "Summary:" in output
        assert "Total processed:" in output


@pytest.mark.django_db
class TestUpdateStartLocationsCommand:
    """Tests for the update_start_locations management command."""

    def test_update_start_locations_no_routes(self):
        """Test command with no routes to process."""
        out = StringIO()
        call_command("update_start_locations", stdout=out)

        output = out.getvalue()
        assert "No routes to process" in output

    def test_update_start_locations_matches_start_point(self):
        """Test command matches route to start point."""
        StartPoint.objects.create(
            name="Test Start", latitude=51.5074, longitude=-0.1278
        )
        test_route = Route.objects.create(
            name="Test Route",
            start_lat=51.5074,
            start_lon=-0.1278,
            start_location="",
        )

        out = StringIO()
        call_command("update_start_locations", stdout=out)

        test_route.refresh_from_db()
        assert test_route.start_location == "Test Start"

        output = out.getvalue()
        assert "Matched to start points: 1" in output

    def test_update_start_locations_no_match_nearby(self):
        """Test command when no start point is nearby."""
        # Create start point far away
        StartPoint.objects.create(name="Far Point", latitude=52.0, longitude=-1.0)
        test_route = Route.objects.create(
            name="Test Route",
            start_lat=51.5074,
            start_lon=-0.1278,
            start_location="",
        )

        out = StringIO()
        call_command("update_start_locations", stdout=out)

        test_route.refresh_from_db()
        assert test_route.start_location == ""

        output = out.getvalue()
        assert "Unchanged: 1" in output

    @patch("routes.management.commands.update_start_locations.get_location_name")
    def test_update_start_locations_force_geocode(self, mock_geocode):
        """Test --force-geocode flag triggers geocoding."""
        mock_geocode.return_value = "London, England"

        Route.objects.create(
            name="Test Route",
            start_lat=51.5074,
            start_lon=-0.1278,
            start_location="",
        )

        out = StringIO()
        call_command("update_start_locations", force_geocode=True, stdout=out)

        output = out.getvalue()
        assert "Re-geocoded: 1" in output
        mock_geocode.assert_called_once()

    def test_update_start_locations_all_flag(self):
        """Test --all flag processes all routes."""
        StartPoint.objects.create(
            name="Test Start", latitude=51.5074, longitude=-0.1278
        )

        # Route without start_location
        Route.objects.create(
            name="Route 1",
            start_lat=51.5074,
            start_lon=-0.1278,
            start_location="",
        )

        # Route with existing start_location
        Route.objects.create(
            name="Route 2",
            start_lat=51.5074,
            start_lon=-0.1278,
            start_location="Old Location",
        )

        out = StringIO()
        call_command("update_start_locations", all=True, stdout=out)

        output = out.getvalue()
        # Should process both routes
        assert "Processing all 2 routes" in output

    def test_update_start_locations_dry_run(self):
        """Test dry-run mode doesn't make changes."""
        StartPoint.objects.create(
            name="Test Start", latitude=51.5074, longitude=-0.1278
        )
        test_route = Route.objects.create(
            name="Test Route",
            start_lat=51.5074,
            start_lon=-0.1278,
            start_location="",
        )

        out = StringIO()
        call_command("update_start_locations", dry_run=True, stdout=out)

        test_route.refresh_from_db()
        # Should not have changed
        assert test_route.start_location == ""

        output = out.getvalue()
        assert "DRY RUN" in output

    def test_update_start_locations_is_coordinate_string(self):
        """Test detection of coordinate strings."""
        Route.objects.create(
            name="Coord String",
            start_lat=51.5074,
            start_lon=-0.1278,
            start_location="51.5074, -0.1278",
        )

        out = StringIO()
        call_command("update_start_locations", stdout=out)

        # Coordinate strings should not be changed without force_geocode
        output = out.getvalue()
        assert "Unchanged: 1" in output

    @patch("routes.management.commands.update_start_locations.get_location_name")
    def test_update_start_locations_keeps_proper_names(self, mock_geocode):
        """Test that proper location names are not geocoded."""
        test_route = Route.objects.create(
            name="Test Route",
            start_lat=51.5074,
            start_lon=-0.1278,
            start_location="London Bridge",
        )

        out = StringIO()
        call_command("update_start_locations", all=True, force_geocode=True, stdout=out)

        # Should not geocode because location is already a proper name
        mock_geocode.assert_not_called()

        test_route.refresh_from_db()
        assert test_route.start_location == "London Bridge"

    def test_update_start_locations_exception_handling(self):
        """Test command handles exceptions gracefully."""
        Route.objects.create(
            name="Test Route",
            start_lat=51.5074,
            start_lon=-0.1278,
            start_location="",
        )

        with patch(
            "routes.management.commands.update_start_locations.find_closest_start_point",
            side_effect=Exception("Test error"),
        ):
            out = StringIO()
            call_command("update_start_locations", stdout=out)

            output = out.getvalue()
            assert "Errors: 1" in output

    def test_update_start_locations_summary_output(self):
        """Test command outputs correct summary."""
        StartPoint.objects.create(
            name="Test Start", latitude=51.5074, longitude=-0.1278
        )

        Route.objects.create(
            name="Match",
            start_lat=51.5074,
            start_lon=-0.1278,
            start_location="",
        )
        Route.objects.create(
            name="No Match",
            start_lat=52.0,
            start_lon=-1.0,
            start_location="",
        )

        out = StringIO()
        call_command("update_start_locations", stdout=out)

        output = out.getvalue()
        assert "Summary:" in output
        assert "Matched to start points: 1" in output
        assert "Unchanged: 1" in output
        assert "Total processed: 2" in output
