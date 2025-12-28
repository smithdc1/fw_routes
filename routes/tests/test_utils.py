"""
Tests for routes utility functions.
"""

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock, mock_open
from routes.utils import (
    parse_gpx,
    get_location_name,
    generate_static_map_image,
    calculate_distance_meters,
    find_closest_start_point,
)
from routes.models import StartPoint
from pathlib import Path
import json


def get_fixture_path(filename):
    """Get the full path to a test fixture file."""
    return Path(__file__).parent / "fixtures" / filename


class ParseGPXTest(TestCase):
    """Tests for parse_gpx utility function."""

    def test_parse_gpx_with_tracks(self):
        """Test parsing GPX file with track data."""
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as gpx_file:
            data = parse_gpx(gpx_file)

        self.assertEqual(data["name"], "Sample Track")
        self.assertGreater(data["distance_km"], 0)
        self.assertGreater(data["elevation_gain"], 0)
        self.assertGreater(len(data["points"]), 0)
        self.assertIsNotNone(data["start_lat"])
        self.assertIsNotNone(data["start_lon"])
        # First point should match the first trkpt in the file
        self.assertEqual(data["start_lat"], 52.4603)
        self.assertEqual(data["start_lon"], -2.1638)

    def test_parse_gpx_with_routes(self):
        """Test parsing GPX file with route data (no tracks)."""
        path = get_fixture_path("sample_route.gpx")
        with open(path, "rb") as gpx_file:
            data = parse_gpx(gpx_file)

        self.assertEqual(data["name"], "Sample Route (No Track)")
        self.assertGreater(len(data["points"]), 0)
        self.assertIsNotNone(data["start_lat"])
        self.assertIsNotNone(data["start_lon"])

    def test_parse_gpx_with_waypoints_only(self):
        """Test parsing GPX file with only waypoints."""
        path = get_fixture_path("waypoints_only.gpx")
        with open(path, "rb") as gpx_file:
            data = parse_gpx(gpx_file)

        self.assertGreater(len(data["points"]), 0)
        self.assertEqual(len(data["points"]), 2)  # 2 waypoints in file

    def test_parse_gpx_extracts_distance(self):
        """Test that parse_gpx calculates distance correctly."""
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as gpx_file:
            data = parse_gpx(gpx_file)

        # Should have calculated some distance
        self.assertGreater(data["distance_km"], 0)

    def test_parse_gpx_extracts_elevation(self):
        """Test that parse_gpx calculates elevation gain."""
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as gpx_file:
            data = parse_gpx(gpx_file)

        # Sample track has elevation gain
        self.assertGreater(data["elevation_gain"], 0)

    def test_parse_gpx_empty_file(self):
        """Test parsing GPX with no tracks/routes/waypoints."""
        empty_gpx = b'<?xml version="1.0"?><gpx version="1.1"></gpx>'
        gpx_file = SimpleUploadedFile("empty.gpx", empty_gpx)

        data = parse_gpx(gpx_file)

        self.assertEqual(data["name"], "")
        self.assertEqual(data["distance_km"], 0)
        self.assertEqual(data["elevation_gain"], 0)
        self.assertEqual(len(data["points"]), 0)
        self.assertIsNone(data["start_lat"])
        self.assertIsNone(data["start_lon"])


class GetLocationNameTest(TestCase):
    """Tests for get_location_name utility function."""

    @patch("routes.utils.urlopen")
    def test_successful_geocoding(self, mock_urlopen):
        """Test successful geocoding with full address."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "address": {
                    "road": "Main Street",
                    "city": "Birmingham",
                    "state": "England",
                },
                "display_name": "Full Address String",
            }
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        location = get_location_name(52.4603, -2.1638)

        self.assertEqual(location, "Main Street, Birmingham, England")

    @patch("routes.utils.urlopen")
    def test_geocoding_with_town(self, mock_urlopen):
        """Test geocoding with town instead of city."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"address": {"town": "Small Town", "state": "England"}}
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        location = get_location_name(52.4603, -2.1638)

        self.assertEqual(location, "Small Town, England")

    @patch("routes.utils.urlopen")
    def test_geocoding_with_village(self, mock_urlopen):
        """Test geocoding with village."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"address": {"village": "Small Village", "state": "England"}}
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        location = get_location_name(52.4603, -2.1638)

        self.assertEqual(location, "Small Village, England")

    @patch("routes.utils.urlopen")
    def test_geocoding_with_minimal_data(self, mock_urlopen):
        """Test geocoding with minimal address data."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"address": {}, "display_name": "Full Display Name"}
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        location = get_location_name(52.4603, -2.1638)

        self.assertEqual(location, "Full Display Name")

    @patch("routes.utils.urlopen")
    def test_geocoding_timeout(self, mock_urlopen):
        """Test geocoding timeout returns coordinates."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("timeout")

        location = get_location_name(52.4603, -2.1638)

        # Should return coordinates as fallback
        self.assertIn("52.4603", location)
        self.assertIn("-2.1638", location)

    @patch("routes.utils.urlopen")
    def test_geocoding_api_error(self, mock_urlopen):
        """Test geocoding API error returns coordinates."""
        mock_urlopen.side_effect = Exception("API Error")

        location = get_location_name(52.4603, -2.1638)

        # Should return coordinates as fallback
        self.assertIn("52.4603", location)
        self.assertIn("-2.1638", location)


class GenerateStaticMapImageTest(TestCase):
    """Tests for generate_static_map_image utility function."""

    def test_empty_points_returns_none(self):
        """Test that empty points list returns None."""
        result = generate_static_map_image([])

        self.assertIsNone(result)

    @patch("routes.utils.os.unlink")
    @patch("routes.utils.sync_playwright")
    def test_successful_thumbnail_generation(self, mock_playwright, mock_unlink):
        """Test successful thumbnail generation."""
        # Mock Playwright
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.screenshot.return_value = b"x" * 10000  # Fake PNG data > 5000 bytes
        mock_browser.new_page.return_value = mock_page
        mock_p = MagicMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p

        points = [(52.4603, -2.1638), (52.4613, -2.1628), (52.4623, -2.1618)]
        result = generate_static_map_image(points)

        # Should return a ContentFile
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, "read"))

    @patch("routes.utils.os.unlink")
    @patch("routes.utils.sync_playwright")
    def test_thumbnail_too_small_returns_none(self, mock_playwright, mock_unlink):
        """Test that too-small screenshots return None."""
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.screenshot.return_value = b"x" * 100  # Too small
        mock_browser.new_page.return_value = mock_page
        mock_p = MagicMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p

        points = [(52.4603, -2.1638), (52.4613, -2.1628)]
        result = generate_static_map_image(points)

        self.assertIsNone(result)

    @patch("routes.utils.os.unlink")
    @patch("routes.utils.sync_playwright")
    def test_playwright_error_returns_none(self, mock_playwright, mock_unlink):
        """Test that Playwright errors return None."""
        mock_playwright.side_effect = Exception("Playwright failed")

        points = [(52.4603, -2.1638), (52.4613, -2.1628)]
        result = generate_static_map_image(points)

        self.assertIsNone(result)


class CalculateDistanceMetersTest(TestCase):
    """Tests for calculate_distance_meters utility function."""

    def test_same_point_zero_distance(self):
        """Test that distance between same point is zero."""
        distance = calculate_distance_meters(52.4603, -2.1638, 52.4603, -2.1638)

        self.assertAlmostEqual(distance, 0, places=0)

    def test_known_distance(self):
        """Test distance calculation with known coordinates."""
        # London to Birmingham (approximate)
        lat1, lon1 = 51.5074, -0.1278  # London
        lat2, lon2 = 52.4862, -1.8904  # Birmingham

        distance = calculate_distance_meters(lat1, lon1, lat2, lon2)

        # Should be approximately 160-170 km
        self.assertGreater(distance, 150000)
        self.assertLess(distance, 180000)

    def test_short_distance(self):
        """Test short distance calculation."""
        # Two points very close together
        lat1, lon1 = 52.4603, -2.1638
        lat2, lon2 = 52.4613, -2.1628

        distance = calculate_distance_meters(lat1, lon1, lat2, lon2)

        # Should be around 100-300 meters (closer than initially expected)
        self.assertGreater(distance, 100)
        self.assertLess(distance, 500)

    def test_equator_distance(self):
        """Test distance calculation on equator."""
        lat1, lon1 = 0, 0
        lat2, lon2 = 0, 1  # 1 degree longitude difference

        distance = calculate_distance_meters(lat1, lon1, lat2, lon2)

        # At equator, 1 degree longitude ≈ 111 km
        self.assertGreater(distance, 100000)
        self.assertLess(distance, 120000)


class FindClosestStartPointTest(TestCase):
    """Tests for find_closest_start_point utility function."""

    def test_find_point_within_distance(self):
        """Test finding start point within max distance."""
        sp = StartPoint.objects.create(
            name="Test Point", latitude=52.4603, longitude=-2.1638
        )

        # Very close point (within 250m)
        result = find_closest_start_point(52.4605, -2.1640, max_distance_meters=250)

        self.assertEqual(result, sp)

    def test_no_point_within_distance(self):
        """Test when no start point is within max distance."""
        StartPoint.objects.create(
            name="Far Point", latitude=52.4603, longitude=-2.1638
        )

        # Far away point (>250m)
        result = find_closest_start_point(52.5000, -2.2000, max_distance_meters=250)

        self.assertIsNone(result)

    def test_find_closest_among_multiple(self):
        """Test finding the closest point among multiple options."""
        sp1 = StartPoint.objects.create(
            name="Far Point", latitude=52.4600, longitude=-2.1600
        )
        sp2 = StartPoint.objects.create(
            name="Close Point", latitude=52.4605, longitude=-2.1640
        )
        sp3 = StartPoint.objects.create(
            name="Medium Point", latitude=52.4610, longitude=-2.1650
        )

        # Should find sp2 as it's closest
        result = find_closest_start_point(52.4605, -2.1638, max_distance_meters=1000)

        self.assertEqual(result, sp2)

    def test_empty_database_returns_none(self):
        """Test when there are no start points in database."""
        result = find_closest_start_point(52.4603, -2.1638, max_distance_meters=250)

        self.assertIsNone(result)

    def test_custom_max_distance(self):
        """Test with custom max distance parameter."""
        sp = StartPoint.objects.create(
            name="Test Point", latitude=52.4603, longitude=-2.1638
        )

        # Point ~500m away should be found with larger max_distance
        result = find_closest_start_point(52.4650, -2.1638, max_distance_meters=1000)

        self.assertEqual(result, sp)

        # Same point should NOT be found with smaller max_distance
        result = find_closest_start_point(52.4650, -2.1638, max_distance_meters=100)

        self.assertIsNone(result)
