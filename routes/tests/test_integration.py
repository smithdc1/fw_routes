"""
Integration tests for complete user workflows.
"""

from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from routes.models import Route, StartPoint, Tag


def get_fixture_path(filename):
    """Get the full path to a test fixture file."""
    return Path(__file__).parent / "fixtures" / filename


class FullUploadWorkflowTest(TestCase):
    """Test complete upload workflow from upload to processing."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    @patch("routes.services.process_route_async")
    @patch("routes.utils.generate_static_map_image")
    @patch("routes.utils.find_closest_start_point")
    def test_complete_upload_flow(self, mock_find_start, mock_generate, mock_task):
        """Test complete flow: upload GPX -> route created -> task runs."""
        # Setup mocks
        start_point = StartPoint.objects.create(
            name="Test Location", latitude=52.4603, longitude=-2.1638
        )
        mock_find_start.return_value = start_point
        mock_generate.return_value = ContentFile(b"fake image", name="test.webp")

        # Load GPX file
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        # Upload the route
        response = self.client.post(
            reverse("route_upload"),
            {
                "name": "My Test Route",
                "tags_input": "hiking, mountain",
                "gpx_file": gpx_file,
            },
            follow=True,
        )

        # Verify redirect to detail page
        self.assertEqual(response.status_code, 200)

        # Verify route was created
        route = Route.objects.get(name="My Test Route")
        self.assertIsNotNone(route)
        self.assertGreater(route.distance_km, 0)
        self.assertIsNotNone(route.start_lat)
        self.assertIsNotNone(route.start_lon)

        # Verify tags were created
        self.assertEqual(route.tags.count(), 2)

        # Verify async task was queued
        self.assertTrue(mock_task.enqueue.called)

    @patch("routes.services.process_route_async")
    def test_bulk_upload_flow(self, mock_task):
        """Test bulk upload of multiple GPX files."""
        path1 = get_fixture_path("sample_track.gpx")
        path2 = get_fixture_path("sample_route.gpx")

        with open(path1, "rb") as f1, open(path2, "rb") as f2:
            file1 = SimpleUploadedFile(
                "track.gpx", f1.read(), content_type="application/gpx+xml"
            )
            file2 = SimpleUploadedFile(
                "route.gpx", f2.read(), content_type="application/gpx+xml"
            )

            response = self.client.post(
                reverse("bulk_upload"),
                {"default_tags": "bulk, test", "gpx_files": [file1, file2]},
                follow=True,
            )

        self.assertEqual(response.status_code, 200)

        # Verify both routes were created
        self.assertEqual(Route.objects.count(), 2)

        # Verify tags were applied to both
        for route in Route.objects.all():
            tag_names = [tag.name for tag in route.tags.all()]
            self.assertIn("Bulk", tag_names)
            self.assertIn("Test", tag_names)


class CompleteUserJourneyTest(TestCase):
    """Test complete user journey through the application."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    @patch("routes.services.process_route_async")
    def test_full_user_journey(self, mock_task):
        """Test: upload -> list -> filter -> detail -> edit tags -> delete."""
        # 1. Upload a route
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        self.client.post(
            reverse("route_upload"),
            {"name": "Test Route", "tags_input": "hiking", "gpx_file": gpx_file},
        )

        route = Route.objects.get(name="Test Route")

        # 2. View route list
        response = self.client.get(reverse("route_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Route")

        # 3. Filter by tag
        response = self.client.get(reverse("route_list") + "?tag=Hiking")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Route")

        # 4. View route detail
        response = self.client.get(reverse("route_detail", kwargs={"pk": route.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Route")

        # 5. Update tags
        new_tag = Tag.objects.create(name="Mountain")
        response = self.client.post(
            reverse("route_detail", kwargs={"pk": route.pk}),
            {"action": "update_tags", "tags": [new_tag.id]},
        )
        self.assertEqual(response.status_code, 302)

        route.refresh_from_db()
        self.assertIn(new_tag, route.tags.all())

        # 6. Rename route
        response = self.client.post(
            reverse("route_detail", kwargs={"pk": route.pk}),
            {"action": "rename", "new_name": "Renamed Route"},
        )
        route.refresh_from_db()
        self.assertEqual(route.name, "Renamed Route")

        # 7. Delete route
        response = self.client.post(reverse("route_delete", kwargs={"pk": route.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Route.objects.filter(pk=route.pk).exists())


class PublicShareWorkflowTest(TestCase):
    """Test public sharing workflow."""

    def setUp(self):
        self.client = Client()

    def test_share_link_workflow(self):
        """Test creating and accessing route via share link."""
        # Create route (as if uploaded by authenticated user)
        route = Route.objects.create(
            name="Shared Route",
            distance_km=15.5,
            route_coordinates=[[52.4603, -2.1638], [52.4613, -2.1628]],
        )

        # Access via share link (no authentication)
        response = self.client.get(
            reverse("route_share", kwargs={"token": route.share_token})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Shared Route")

        # Verify share token is unique and valid
        self.assertIsNotNone(route.share_token)
        self.assertEqual(len(route.share_token), 16)


class FilteringAndSearchWorkflowTest(TestCase):
    """Test filtering and search workflows."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

        # Create test data
        self.tag1 = Tag.objects.create(name="Hiking")
        self.tag2 = Tag.objects.create(name="Biking")

        self.route1 = Route.objects.create(
            name="Mountain Hike", distance_km=40, start_location="Location A"
        )
        self.route1.tags.add(self.tag1)

        self.route2 = Route.objects.create(
            name="Beach Ride", distance_km=80, start_location="Location B"
        )
        self.route2.tags.add(self.tag2)

        self.route3 = Route.objects.create(
            name="City Hike", distance_km=8, start_location="Location A"
        )
        self.route3.tags.add(self.tag1)

    def test_combined_filters(self):
        """Test combining tag, distance, and location filters."""
        response = self.client.get(
            reverse("route_list") + "?tag=Hiking&distance=short&start_point=Location A"
        )

        self.assertEqual(response.status_code, 200)
        routes = list(response.context["routes"])

        # Should only show route3 (hiking, short, Location A)
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].name, "City Hike")

    def test_search_with_filters(self):
        """Test search combined with other filters."""
        response = self.client.get(reverse("route_list") + "?search=Hike&tag=Hiking")

        routes = list(response.context["routes"])
        self.assertEqual(len(routes), 2)
        route_names = [r.name for r in routes]
        self.assertIn("Mountain Hike", route_names)
        self.assertIn("City Hike", route_names)

    def test_sorting_with_filters(self):
        """Test sorting combined with filters."""
        response = self.client.get(
            reverse("route_list") + "?tag=Hiking&sort=distance_desc"
        )

        routes = list(response.context["routes"])
        # Mountain Hike (16km) should come before City Hike (8km)
        self.assertEqual(routes[0].name, "Mountain Hike")
        self.assertEqual(routes[1].name, "City Hike")
