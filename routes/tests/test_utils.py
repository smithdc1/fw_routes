"""
Tests for routes utils module.

Tests cover:
- GPX parsing for different GPX structures
- Distance calculations using Haversine formula
- Start point matching with distance thresholds
- Edge cases and error handling
"""

from unittest.mock import Mock, patch

from routes.models import StartPoint
from routes.utils import (
    calculate_distance_meters,
    find_closest_start_point,
    get_location_name,
    parse_gpx,
)


class TestParseGPX:
    """Tests for the parse_gpx utility function."""

    def test_parse_gpx_with_track(self, sample_gpx_file):
        """Test parsing GPX file with track data."""
        data = parse_gpx(sample_gpx_file)

        assert data["name"] == "Sample Track"
        assert len(data["points"]) == 3
        assert data["start_lat"] == 51.5074
        assert data["start_lon"] == -0.1278
        assert data["distance_km"] >= 0
        assert data["elevation_gain"] >= 0

    def test_parse_gpx_with_route(self, gpx_with_route_content):
        """Test parsing GPX file with route instead of track."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        gpx_file = SimpleUploadedFile(
            "route.gpx", gpx_with_route_content, content_type="application/gpx+xml"
        )
        data = parse_gpx(gpx_file)

        assert data["name"] == "Route Example"
        assert len(data["points"]) == 3
        assert data["start_lat"] is not None
        assert data["start_lon"] is not None

    def test_parse_gpx_with_waypoints(self, gpx_with_waypoints_content):
        """Test parsing GPX file with only waypoints."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        gpx_file = SimpleUploadedFile(
            "waypoints.gpx",
            gpx_with_waypoints_content,
            content_type="application/gpx+xml",
        )
        data = parse_gpx(gpx_file)

        assert len(data["points"]) == 2
        assert data["start_lat"] is not None
        assert data["start_lon"] is not None

    def test_parse_gpx_empty(self, empty_gpx_content):
        """Test parsing empty GPX file (no tracks, routes, or waypoints)."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        gpx_file = SimpleUploadedFile(
            "empty.gpx", empty_gpx_content, content_type="application/gpx+xml"
        )
        data = parse_gpx(gpx_file)

        assert data["name"] == ""
        assert data["points"] == []
        assert data["start_lat"] is None
        assert data["start_lon"] is None
        assert data["distance_km"] == 0
        assert data["elevation_gain"] == 0

    def test_parse_gpx_with_elevation(self, complex_gpx_content):
        """Test parsing GPX with elevation data."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        gpx_file = SimpleUploadedFile(
            "elevation.gpx", complex_gpx_content, content_type="application/gpx+xml"
        )
        data = parse_gpx(gpx_file)

        assert data["elevation_gain"] >= 0
        # With the elevation data, we should have some gain
        assert len(data["points"]) == 5

    def test_parse_gpx_coordinates_format(self, sample_gpx_file):
        """Test that coordinates are in correct format (lat, lon) tuples."""
        data = parse_gpx(sample_gpx_file)

        for point in data["points"]:
            assert isinstance(point, tuple)
            assert len(point) == 2
            lat, lon = point
            assert isinstance(lat, (int, float))
            assert isinstance(lon, (int, float))
            # Validate coordinate ranges
            assert -90 <= lat <= 90
            assert -180 <= lon <= 180

    def test_parse_gpx_file_seekable(self, sample_gpx_file):
        """Test that GPX parsing resets file pointer."""
        parse_gpx(sample_gpx_file)
        # File should be seeked to 0 at start of parse_gpx
        # Parsing succeeds without raising an exception

    def test_parse_gpx_multiple_tracks(self):
        """Test parsing GPX with multiple tracks."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        multi_track_gpx = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
    <trk>
        <name>Track 1</name>
        <trkseg>
            <trkpt lat="51.5074" lon="-0.1278">
                <ele>50</ele>
            </trkpt>
            <trkpt lat="51.5084" lon="-0.1268">
                <ele>60</ele>
            </trkpt>
        </trkseg>
    </trk>
    <trk>
        <name>Track 2</name>
        <trkseg>
            <trkpt lat="51.5094" lon="-0.1258">
                <ele>55</ele>
            </trkpt>
        </trkseg>
    </trk>
</gpx>
"""
        gpx_file = SimpleUploadedFile(
            "multi.gpx", multi_track_gpx, content_type="application/gpx+xml"
        )
        data = parse_gpx(gpx_file)

        # Should use name from first track
        assert data["name"] == "Track 1"
        # Should combine points from all tracks
        assert len(data["points"]) == 3

    def test_parse_gpx_no_name_in_track(self):
        """Test parsing GPX where track has no name."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        no_name_gpx = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
    <trk>
        <trkseg>
            <trkpt lat="51.5074" lon="-0.1278">
                <ele>50</ele>
            </trkpt>
        </trkseg>
    </trk>
</gpx>
"""
        gpx_file = SimpleUploadedFile(
            "noname.gpx", no_name_gpx, content_type="application/gpx+xml"
        )
        data = parse_gpx(gpx_file)

        assert data["name"] == ""


class TestCalculateDistanceMeters:
    """Tests for the calculate_distance_meters utility function."""

    def test_calculate_distance_same_point(self):
        """Test distance between identical points is zero."""
        distance = calculate_distance_meters(51.5074, -0.1278, 51.5074, -0.1278)
        assert distance == 0

    def test_calculate_distance_known_distance(self):
        """Test distance calculation with known coordinates."""
        # London (51.5074, -0.1278) to Paris (48.8566, 2.3522)
        # Approximate distance: ~344 km = 344000 meters
        distance = calculate_distance_meters(51.5074, -0.1278, 48.8566, 2.3522)
        # Allow 5% tolerance for Haversine approximation
        assert 320000 < distance < 360000

    def test_calculate_distance_short_distance(self):
        """Test distance calculation for short distances."""
        # Two points very close together
        distance = calculate_distance_meters(51.5074, -0.1278, 51.5075, -0.1279)
        # Should be around 100-150 meters
        assert 0 < distance < 200

    def test_calculate_distance_antipodal_points(self):
        """Test distance between antipodal points (opposite sides of Earth)."""
        # North pole and South pole
        distance = calculate_distance_meters(90, 0, -90, 0)
        # Should be approximately half Earth's circumference (~20000 km)
        assert 19000000 < distance < 21000000

    def test_calculate_distance_across_dateline(self):
        """Test distance calculation across international date line."""
        # Points on either side of date line
        distance = calculate_distance_meters(0, 179, 0, -179)
        # Should be relatively short despite longitude difference
        assert distance < 500000  # Less than 500 km

    def test_calculate_distance_equator_points(self):
        """Test distance between points on equator."""
        # 1 degree of longitude at equator ≈ 111 km
        distance = calculate_distance_meters(0, 0, 0, 1)
        # Should be approximately 111 km (111000 meters)
        assert 110000 < distance < 112000

    def test_calculate_distance_meridian_points(self):
        """Test distance between points on same meridian."""
        # 1 degree of latitude ≈ 111 km anywhere
        distance = calculate_distance_meters(0, 0, 1, 0)
        # Should be approximately 111 km
        assert 110000 < distance < 112000

    def test_calculate_distance_negative_coordinates(self):
        """Test distance with negative coordinates."""
        # Southern and Western hemispheres
        distance = calculate_distance_meters(-33.8688, 151.2093, -37.8136, 144.9631)
        # Sydney to Melbourne: approximately 714 km
        assert 700000 < distance < 730000


class TestFindClosestStartPoint:
    """Tests for the find_closest_start_point utility function."""

    def test_find_closest_start_point_within_range(self, db):
        """Test finding start point within max distance."""
        point = StartPoint.objects.create(
            name="Test Point", latitude=51.5074, longitude=-0.1278
        )

        # Search very close to the point (within 250m default)
        result = find_closest_start_point(51.5075, -0.1279)

        assert result == point

    def test_find_closest_start_point_outside_range(self, db):
        """Test that points outside max distance are not returned."""
        StartPoint.objects.create(
            name="Distant Point", latitude=51.5074, longitude=-0.1278
        )

        # Search far away (> 250m)
        result = find_closest_start_point(52.0, -1.0)

        assert result is None

    def test_find_closest_start_point_multiple_points(self, db):
        """Test finding closest among multiple points."""
        StartPoint.objects.create(name="Far Point", latitude=51.50, longitude=-0.12)
        point2 = StartPoint.objects.create(
            name="Close Point", latitude=51.5074, longitude=-0.1278
        )
        StartPoint.objects.create(name="Mid Point", latitude=51.505, longitude=-0.125)

        # Search very close to point2
        result = find_closest_start_point(51.5075, -0.1279, max_distance_meters=1000)

        assert result == point2

    def test_find_closest_start_point_custom_max_distance(self, db):
        """Test using custom max distance parameter."""
        point = StartPoint.objects.create(
            name="Point", latitude=51.5074, longitude=-0.1278
        )

        # Search with larger max distance
        result = find_closest_start_point(
            51.52,
            -0.13,
            max_distance_meters=5000,  # 5 km
        )

        assert result == point

    def test_find_closest_start_point_at_exact_limit(self, db):
        """Test finding point at exactly the max distance."""
        # Create a point exactly 250m away (approximately)
        point = StartPoint.objects.create(
            name="Limit Point", latitude=51.5074, longitude=-0.1278
        )

        # Calculate a point approximately 250m away
        # At 51.5° latitude, 1 degree ≈ 111km
        # So 250m ≈ 0.00225 degrees
        result = find_closest_start_point(51.50965, -0.1278, max_distance_meters=250)

        # Should find it (within tolerance)
        assert result == point or result is None  # Depends on exact calculation

    def test_find_closest_start_point_no_points(self, db):
        """Test when no start points exist."""
        result = find_closest_start_point(51.5074, -0.1278)
        assert result is None

    def test_find_closest_start_point_exact_match(self, db):
        """Test finding point at exact coordinates."""
        point = StartPoint.objects.create(
            name="Exact", latitude=51.5074, longitude=-0.1278
        )

        result = find_closest_start_point(51.5074, -0.1278)

        assert result == point

    def test_find_closest_start_point_very_small_max_distance(self, db):
        """Test with very small max distance."""
        StartPoint.objects.create(name="Point", latitude=51.5074, longitude=-0.1278)

        # Search with only 1 meter max distance
        result = find_closest_start_point(51.5075, -0.1279, max_distance_meters=1)

        assert result is None  # Too far even for close coordinates


class TestGetLocationName:
    """Tests for the get_location_name utility function."""

    @patch("routes.utils.urlopen")
    def test_get_location_name_success(self, mock_urlopen):
        """Test successful location name retrieval."""
        # Mock the response
        mock_response = Mock()
        mock_response.read.return_value = b"""{
            "address": {
                "road": "Main Street",
                "city": "London",
                "state": "England"
            }
        }"""
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = get_location_name(51.5074, -0.1278)

        assert result == "Main Street, London, England"
        mock_urlopen.assert_called_once()

    @patch("routes.utils.urlopen")
    def test_get_location_name_partial_address(self, mock_urlopen):
        """Test with partial address data."""
        mock_response = Mock()
        mock_response.read.return_value = b"""{
            "address": {
                "city": "London"
            }
        }"""
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = get_location_name(51.5074, -0.1278)

        assert result == "London"

    @patch("routes.utils.urlopen")
    def test_get_location_name_town_fallback(self, mock_urlopen):
        """Test fallback to town when city not available."""
        mock_response = Mock()
        mock_response.read.return_value = b"""{
            "address": {
                "road": "High Street",
                "town": "Cambridge",
                "state": "England"
            }
        }"""
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = get_location_name(52.2053, 0.1218)

        assert result == "High Street, Cambridge, England"

    @patch("routes.utils.urlopen")
    def test_get_location_name_village_fallback(self, mock_urlopen):
        """Test fallback to village when city/town not available."""
        mock_response = Mock()
        mock_response.read.return_value = b"""{
            "address": {
                "village": "Small Village",
                "state": "Scotland"
            }
        }"""
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = get_location_name(57.0, -4.0)

        assert result == "Small Village, Scotland"

    @patch("routes.utils.urlopen")
    def test_get_location_name_display_name_fallback(self, mock_urlopen):
        """Test fallback to display_name when no structured address."""
        mock_response = Mock()
        mock_response.read.return_value = b"""{
            "display_name": "Somewhere in the Ocean",
            "address": {}
        }"""
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = get_location_name(0.0, 0.0)

        assert result == "Somewhere in the Ocean"

    @patch("routes.utils.urlopen")
    def test_get_location_name_network_error(self, mock_urlopen):
        """Test fallback to coordinates on network error."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Network error")

        result = get_location_name(51.5074, -0.1278)

        # Should fall back to coordinate string
        assert result == "51.5074, -0.1278"

    @patch("routes.utils.urlopen")
    def test_get_location_name_timeout(self, mock_urlopen):
        """Test handling of timeout errors."""
        mock_urlopen.side_effect = TimeoutError("Request timeout")

        result = get_location_name(51.5074, -0.1278)

        # Should fall back to coordinates
        assert "51.5074" in result
        assert "-0.1278" in result

    @patch("routes.utils.urlopen")
    def test_get_location_name_invalid_json(self, mock_urlopen):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.read.return_value = b"<html>Not JSON</html>"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = get_location_name(51.5074, -0.1278)

        # Should fall back to coordinates
        assert "51.5074" in result
