"""
Tests for routes models.
"""

from django.test import TestCase
from django.db import IntegrityError
from routes.models import Tag, StartPoint, Route


class TagModelTest(TestCase):
    """Tests for the Tag model."""

    def test_create_tag(self):
        """Test creating a tag."""
        tag = Tag.objects.create(name="Hiking")
        self.assertEqual(tag.name, "Hiking")
        self.assertIsNotNone(tag.created_at)

    def test_tag_str_representation(self):
        """Test tag string representation."""
        tag = Tag.objects.create(name="Mountain Biking")
        self.assertEqual(str(tag), "Mountain Biking")

    def test_normalize_name_whitespace(self):
        """Test normalize_name removes extra whitespace."""
        result = Tag.normalize_name("  hiking   trail  ")
        self.assertEqual(result, "Hiking Trail")

    def test_normalize_name_titlecase(self):
        """Test normalize_name applies titlecase."""
        result = Tag.normalize_name("mountain biking")
        self.assertEqual(result, "Mountain Biking")

    def test_normalize_name_empty(self):
        """Test normalize_name with empty string."""
        result = Tag.normalize_name("")
        self.assertEqual(result, "")

    def test_normalize_name_none(self):
        """Test normalize_name with None."""
        result = Tag.normalize_name(None)
        self.assertEqual(result, "")

    def test_save_normalizes_name(self):
        """Test that save() automatically normalizes tag names."""
        tag = Tag.objects.create(name="  hiking   TRAIL  ")
        self.assertEqual(tag.name, "Hiking Trail")

    def test_tag_unique_constraint(self):
        """Test that duplicate tag names are not allowed."""
        Tag.objects.create(name="Hiking")
        with self.assertRaises(IntegrityError):
            Tag.objects.create(name="Hiking")

    def test_tag_ordering(self):
        """Test that tags are ordered by name."""
        Tag.objects.create(name="Zebra")
        Tag.objects.create(name="Apple")
        Tag.objects.create(name="Mountain")

        tags = list(Tag.objects.all())
        self.assertEqual(tags[0].name, "Apple")
        self.assertEqual(tags[1].name, "Mountain")
        self.assertEqual(tags[2].name, "Zebra")


class StartPointModelTest(TestCase):
    """Tests for the StartPoint model."""

    def test_create_start_point(self):
        """Test creating a start point."""
        sp = StartPoint.objects.create(
            name="Test Start",
            latitude=52.4603,
            longitude=-2.1638,
            description="Test description",
        )
        self.assertEqual(sp.name, "Test Start")
        self.assertEqual(sp.latitude, 52.4603)
        self.assertEqual(sp.longitude, -2.1638)
        self.assertEqual(sp.description, "Test description")
        self.assertIsNotNone(sp.created_at)

    def test_start_point_str_representation(self):
        """Test start point string representation."""
        sp = StartPoint.objects.create(
            name="City Center", latitude=52.4603, longitude=-2.1638
        )
        self.assertEqual(str(sp), "City Center (52.4603, -2.1638)")

    def test_start_point_ordering(self):
        """Test that start points are ordered by name."""
        StartPoint.objects.create(name="Zebra Point", latitude=0, longitude=0)
        StartPoint.objects.create(name="Apple Point", latitude=0, longitude=0)
        StartPoint.objects.create(name="Mountain Point", latitude=0, longitude=0)

        points = list(StartPoint.objects.all())
        self.assertEqual(points[0].name, "Apple Point")
        self.assertEqual(points[1].name, "Mountain Point")
        self.assertEqual(points[2].name, "Zebra Point")

    def test_start_point_blank_description(self):
        """Test that description can be blank."""
        sp = StartPoint.objects.create(
            name="Test Point", latitude=52.4603, longitude=-2.1638, description=""
        )
        self.assertEqual(sp.description, "")


class RouteModelTest(TestCase):
    """Tests for the Route model."""

    def test_create_route(self):
        """Test creating a basic route."""
        route = Route.objects.create(
            name="Test Route",
            distance_km=10.5,
            elevation_gain=250.0,
            start_lat=52.4603,
            start_lon=-2.1638,
            route_coordinates=[[52.4603, -2.1638], [52.4613, -2.1628]],
        )
        self.assertEqual(route.name, "Test Route")
        self.assertEqual(route.distance_km, 10.5)
        self.assertEqual(route.elevation_gain, 250.0)
        self.assertIsNotNone(route.uploaded_at)

    def test_route_str_representation(self):
        """Test route string representation."""
        route = Route.objects.create(name="Mountain Loop")
        self.assertEqual(str(route), "Mountain Loop")

    def test_share_token_auto_generation(self):
        """Test that share_token is automatically generated."""
        route = Route.objects.create(name="Test Route")
        self.assertIsNotNone(route.share_token)
        self.assertEqual(len(route.share_token), 16)

    def test_share_token_uniqueness(self):
        """Test that share tokens are unique across routes."""
        route1 = Route.objects.create(name="Route 1")
        route2 = Route.objects.create(name="Route 2")
        self.assertNotEqual(route1.share_token, route2.share_token)

    def test_get_absolute_url(self):
        """Test get_absolute_url method."""
        route = Route.objects.create(name="Test Route")
        url = route.get_absolute_url()
        self.assertEqual(url, f"/route/{route.pk}/")

    def test_get_share_url(self):
        """Test get_share_url method."""
        route = Route.objects.create(name="Test Route")
        url = route.get_share_url()
        self.assertEqual(url, f"/share/{route.share_token}/")

    def test_distance_miles_property(self):
        """Test distance_miles property calculation."""
        route = Route.objects.create(name="Test Route", distance_km=10.0)
        expected_miles = 10.0 * 0.621371
        self.assertAlmostEqual(route.distance_miles, expected_miles, places=2)

    def test_estimated_time_under_one_hour(self):
        """Test estimated_time for routes under 1 hour."""
        route = Route.objects.create(name="Short Route", distance_km=8.0)
        # 8km = ~4.97 miles, at 12mph = ~24.85 minutes
        self.assertEqual(route.estimated_time, "24m")

    def test_estimated_time_exact_hours(self):
        """Test estimated_time for exact hour values."""
        route = Route.objects.create(name="Medium Route", distance_km=19.31)
        # 19.31km = ~12 miles, at 12mph = ~1 hour
        self.assertIn(route.estimated_time, ["59m", "1h"])  # Account for rounding

    def test_estimated_time_hours_and_minutes(self):
        """Test estimated_time with hours and minutes."""
        route = Route.objects.create(name="Long Route", distance_km=32.19)
        # 32.19km = 20 miles, at 12mph = 1h 40m
        self.assertEqual(route.estimated_time, "1h 40m")

    def test_estimated_time_zero_distance(self):
        """Test estimated_time with zero distance."""
        route = Route.objects.create(name="Zero Route", distance_km=0)
        self.assertEqual(route.estimated_time, "N/A")

    def test_gpx_file_url_with_file(self):
        """Test gpx_file_url property when file exists."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        route = Route.objects.create(name="Test Route")
        route.gpx_file.save(
            "test.gpx", SimpleUploadedFile("test.gpx", b"<gpx></gpx>"), save=True
        )
        self.assertTrue(route.gpx_file_url)
        self.assertIn("test.gpx", route.gpx_file_url)

    def test_gpx_file_url_without_file(self):
        """Test gpx_file_url property when no file exists."""
        route = Route.objects.create(name="Test Route")
        self.assertEqual(route.gpx_file_url, "")

    def test_thumbnail_url_with_file(self):
        """Test thumbnail_url property when thumbnail exists."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        route = Route.objects.create(name="Test Route")
        route.thumbnail_image.save(
            "test.webp", SimpleUploadedFile("test.webp", b"fake image"), save=True
        )
        self.assertTrue(route.thumbnail_url)
        self.assertIn("test.webp", route.thumbnail_url)

    def test_thumbnail_url_without_file(self):
        """Test thumbnail_url property when no thumbnail exists."""
        route = Route.objects.create(name="Test Route")
        self.assertEqual(route.thumbnail_url, "")

    def test_route_ordering(self):
        """Test that routes are ordered by -uploaded_at."""
        import time

        route1 = Route.objects.create(name="Route 1")
        time.sleep(0.01)  # Small delay to ensure different timestamps
        route2 = Route.objects.create(name="Route 2")
        time.sleep(0.01)
        route3 = Route.objects.create(name="Route 3")

        routes = list(Route.objects.all())
        self.assertEqual(routes[0].name, "Route 3")
        self.assertEqual(routes[1].name, "Route 2")
        self.assertEqual(routes[2].name, "Route 1")

    def test_route_tags_relationship(self):
        """Test ManyToMany relationship with tags."""
        route = Route.objects.create(name="Test Route")
        tag1 = Tag.objects.create(name="Hiking")
        tag2 = Tag.objects.create(name="Mountain")

        route.tags.add(tag1, tag2)
        self.assertEqual(route.tags.count(), 2)
        self.assertIn(tag1, route.tags.all())
        self.assertIn(tag2, route.tags.all())

    def test_route_default_values(self):
        """Test that routes have appropriate default values."""
        route = Route.objects.create(name="Test Route")
        self.assertEqual(route.distance_km, 0)
        self.assertEqual(route.elevation_gain, 0)
        self.assertEqual(route.route_coordinates, [])
        self.assertEqual(route.start_location, "")
