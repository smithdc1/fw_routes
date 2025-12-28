"""
Tests for routes views.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
from routes.models import Route, Tag, StartPoint
from pathlib import Path


def get_fixture_path(filename):
    """Get the full path to a test fixture file."""
    return Path(__file__).parent / "fixtures" / filename


class AuthenticationTest(TestCase):
    """Tests for view authentication requirements."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

    def test_route_list_requires_auth(self):
        """Test that route_list requires authentication."""
        response = self.client.get(reverse("route_list"))
        self.assertEqual(response.status_code, 302)
        # Django redirects to /accounts/login/ by default
        self.assertTrue("/login/" in response.url)

    def test_route_detail_requires_auth(self):
        """Test that route_detail requires authentication."""
        route = Route.objects.create(name="Test Route")
        response = self.client.get(reverse("route_detail", kwargs={"pk": route.pk}))
        self.assertEqual(response.status_code, 302)

    def test_route_upload_requires_auth(self):
        """Test that route_upload requires authentication."""
        response = self.client.get(reverse("route_upload"))
        self.assertEqual(response.status_code, 302)

    def test_bulk_upload_requires_auth(self):
        """Test that bulk_upload requires authentication."""
        response = self.client.get(reverse("bulk_upload"))
        self.assertEqual(response.status_code, 302)

    def test_route_delete_requires_auth(self):
        """Test that route_delete requires authentication."""
        route = Route.objects.create(name="Test Route")
        response = self.client.post(reverse("route_delete", kwargs={"pk": route.pk}))
        self.assertEqual(response.status_code, 302)

    def test_route_share_no_auth_required(self):
        """Test that route_share does NOT require authentication."""
        route = Route.objects.create(name="Test Route")
        response = self.client.get(
            reverse("route_share", kwargs={"token": route.share_token})
        )
        self.assertEqual(response.status_code, 200)


class RouteListViewTest(TestCase):
    """Tests for the route_list view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    def test_route_list_displays_routes(self):
        """Test that route list displays all routes."""
        Route.objects.create(name="Route 1", distance_km=10)
        Route.objects.create(name="Route 2", distance_km=20)

        response = self.client.get(reverse("route_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Route 1")
        self.assertContains(response, "Route 2")

    def test_filter_by_tag(self):
        """Test filtering routes by tag."""
        tag = Tag.objects.create(name="Hiking")
        route1 = Route.objects.create(name="Hiking Route", distance_km=10)
        route1.tags.add(tag)
        route2 = Route.objects.create(name="Other Route", distance_km=20)

        response = self.client.get(reverse("route_list") + f"?tag={tag.name}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hiking Route")
        self.assertNotContains(response, "Other Route")

    def test_filter_by_start_point(self):
        """Test filtering routes by start point."""
        route1 = Route.objects.create(
            name="Route 1", distance_km=10, start_location="Location A"
        )
        route2 = Route.objects.create(
            name="Route 2", distance_km=20, start_location="Location B"
        )

        response = self.client.get(reverse("route_list") + "?start_point=Location A")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Route 1")
        self.assertNotContains(response, "Route 2")

    def test_filter_by_distance_short(self):
        """Test filtering routes by short distance (<=20 miles)."""
        Route.objects.create(name="Short Route", distance_km=16)  # ~10 miles
        Route.objects.create(name="Long Route", distance_km=64)  # ~40 miles

        response = self.client.get(reverse("route_list") + "?distance=short")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Short Route")
        self.assertNotContains(response, "Long Route")

    def test_filter_by_distance_medium(self):
        """Test filtering routes by medium distance (20-35 miles)."""
        Route.objects.create(name="Short Route", distance_km=16)
        Route.objects.create(name="Medium Route", distance_km=48)  # ~30 miles
        Route.objects.create(name="Long Route", distance_km=96)  # ~60 miles

        response = self.client.get(reverse("route_list") + "?distance=medium")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Short Route")
        self.assertContains(response, "Medium Route")
        self.assertNotContains(response, "Long Route")

    def test_filter_by_distance_long(self):
        """Test filtering routes by long distance (35-50 miles)."""
        Route.objects.create(name="Long Route", distance_km=64)  # ~40 miles
        Route.objects.create(name="Very Long Route", distance_km=96)  # ~60 miles

        response = self.client.get(reverse("route_list") + "?distance=long")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Long Route")
        self.assertNotContains(response, "Very Long Route")

    def test_filter_by_distance_very_long(self):
        """Test filtering routes by very long distance (>50 miles)."""
        Route.objects.create(name="Medium Long Route", distance_km=64)  # ~40 miles
        Route.objects.create(name="Very Long Route", distance_km=96)  # ~60 miles

        response = self.client.get(reverse("route_list") + "?distance=very_long")

        self.assertEqual(response.status_code, 200)
        # 64km is less than 80.47km threshold (50 miles), so should not be included
        self.assertNotContains(response, "Medium Long Route")
        self.assertContains(response, "Very Long Route")

    def test_search_by_name(self):
        """Test searching routes by name."""
        Route.objects.create(name="Mountain Loop", distance_km=10)
        Route.objects.create(name="Beach Trail", distance_km=20)

        response = self.client.get(reverse("route_list") + "?search=Mountain")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mountain Loop")
        self.assertNotContains(response, "Beach Trail")

    def test_sort_by_distance_asc(self):
        """Test sorting routes by distance ascending."""
        Route.objects.create(name="Route 3", distance_km=30)
        Route.objects.create(name="Route 1", distance_km=10)
        Route.objects.create(name="Route 2", distance_km=20)

        response = self.client.get(reverse("route_list") + "?sort=distance_asc")

        self.assertEqual(response.status_code, 200)
        routes = list(response.context["routes"])
        self.assertEqual(routes[0].name, "Route 1")
        self.assertEqual(routes[1].name, "Route 2")
        self.assertEqual(routes[2].name, "Route 3")

    def test_sort_by_distance_desc(self):
        """Test sorting routes by distance descending."""
        Route.objects.create(name="Route 3", distance_km=30)
        Route.objects.create(name="Route 1", distance_km=10)
        Route.objects.create(name="Route 2", distance_km=20)

        response = self.client.get(reverse("route_list") + "?sort=distance_desc")

        routes = list(response.context["routes"])
        self.assertEqual(routes[0].name, "Route 3")
        self.assertEqual(routes[1].name, "Route 2")
        self.assertEqual(routes[2].name, "Route 1")

    def test_sort_by_name_asc(self):
        """Test sorting routes by name ascending."""
        Route.objects.create(name="Zebra Route")
        Route.objects.create(name="Apple Route")
        Route.objects.create(name="Mountain Route")

        response = self.client.get(reverse("route_list") + "?sort=name_asc")

        routes = list(response.context["routes"])
        self.assertEqual(routes[0].name, "Apple Route")
        self.assertEqual(routes[1].name, "Mountain Route")
        self.assertEqual(routes[2].name, "Zebra Route")

    def test_combined_filters(self):
        """Test combining multiple filters."""
        tag = Tag.objects.create(name="Hiking")
        route1 = Route.objects.create(name="Mountain Hike", distance_km=16)
        route1.tags.add(tag)
        route2 = Route.objects.create(name="Long Hike", distance_km=80)
        route2.tags.add(tag)
        Route.objects.create(name="Beach Walk", distance_km=16)

        response = self.client.get(
            reverse("route_list")
            + f"?tag={tag.name}&distance=short&search=Mountain"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mountain Hike")
        self.assertNotContains(response, "Long Hike")
        self.assertNotContains(response, "Beach Walk")

    def test_empty_results(self):
        """Test view with no matching routes."""
        response = self.client.get(reverse("route_list") + "?search=Nonexistent")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["routes"]), 0)


class RouteDetailViewTest(TestCase):
    """Tests for the route_detail view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    def test_get_route_detail(self):
        """Test GET request displays route details."""
        route = Route.objects.create(
            name="Test Route",
            distance_km=10,
            route_coordinates=[[52.4603, -2.1638]],
        )

        response = self.client.get(reverse("route_detail", kwargs={"pk": route.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Route")
        self.assertEqual(response.context["route"], route)

    def test_rename_route_valid(self):
        """Test renaming a route with valid name."""
        route = Route.objects.create(name="Old Name")

        response = self.client.post(
            reverse("route_detail", kwargs={"pk": route.pk}),
            {"action": "rename", "new_name": "New Name"},
        )

        self.assertEqual(response.status_code, 302)
        route.refresh_from_db()
        self.assertEqual(route.name, "New Name")

    def test_rename_route_empty_name(self):
        """Test renaming a route with empty name fails."""
        route = Route.objects.create(name="Original Name")

        response = self.client.post(
            reverse("route_detail", kwargs={"pk": route.pk}),
            {"action": "rename", "new_name": ""},
            follow=True,
        )

        route.refresh_from_db()
        self.assertEqual(route.name, "Original Name")
        messages = list(response.context["messages"])
        self.assertTrue(any("cannot be empty" in str(m) for m in messages))

    def test_update_tags(self):
        """Test updating route tags."""
        route = Route.objects.create(name="Test Route")
        tag1 = Tag.objects.create(name="Hiking")
        tag2 = Tag.objects.create(name="Mountain")

        response = self.client.post(
            reverse("route_detail", kwargs={"pk": route.pk}),
            {"action": "update_tags", "tags": [tag1.id, tag2.id]},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(route.tags.count(), 2)
        self.assertIn(tag1, route.tags.all())
        self.assertIn(tag2, route.tags.all())

    def test_remove_tag(self):
        """Test removing individual tag from route."""
        route = Route.objects.create(name="Test Route")
        tag = Tag.objects.create(name="Hiking")
        route.tags.add(tag)

        response = self.client.post(
            reverse("route_detail", kwargs={"pk": route.pk}),
            {"action": "remove_tag", "tag_id": tag.id},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(route.tags.count(), 0)

    def test_route_detail_404(self):
        """Test that invalid route ID returns 404."""
        response = self.client.get(reverse("route_detail", kwargs={"pk": 99999}))
        self.assertEqual(response.status_code, 404)


class RouteShareViewTest(TestCase):
    """Tests for the route_share view (public access)."""

    def setUp(self):
        self.client = Client()

    def test_valid_share_token(self):
        """Test accessing route with valid share token."""
        route = Route.objects.create(
            name="Shared Route", route_coordinates=[[52.4603, -2.1638]]
        )

        response = self.client.get(
            reverse("route_share", kwargs={"token": route.share_token})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Shared Route")

    def test_invalid_share_token(self):
        """Test that invalid share token returns 404."""
        response = self.client.get(
            reverse("route_share", kwargs={"token": "invalidtoken123"})
        )

        self.assertEqual(response.status_code, 404)


class RouteUploadViewTest(TestCase):
    """Tests for the route_upload view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    def test_get_upload_form(self):
        """Test GET request displays upload form."""
        response = self.client.get(reverse("route_upload"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "form")

    @patch("routes.views.create_route_from_gpx")
    def test_post_valid_gpx_with_name_and_tags(self, mock_create):
        """Test uploading valid GPX with name and tags."""
        # Mock the route creation
        mock_route = Route.objects.create(name="Test Route", distance_km=10)
        mock_create.return_value = mock_route

        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        response = self.client.post(
            reverse("route_upload"),
            {
                "name": "My Route",
                "tags_input": "hiking, mountain",
                "gpx_file": gpx_file,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(mock_create.called)

    @patch("routes.views.create_route_from_gpx")
    def test_post_valid_gpx_without_name(self, mock_create):
        """Test uploading GPX without name uses filename."""
        mock_route = Route.objects.create(name="sample_track", distance_km=10)
        mock_create.return_value = mock_route

        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        response = self.client.post(
            reverse("route_upload"), {"name": "", "gpx_file": gpx_file}
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(mock_create.called)

    @patch("routes.views.create_route_from_gpx")
    def test_post_invalid_gpx(self, mock_create):
        """Test uploading invalid GPX shows error."""
        mock_create.side_effect = ValueError("Invalid GPX file")

        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        response = self.client.post(
            reverse("route_upload"), {"name": "Test", "gpx_file": gpx_file}, follow=True
        )

        messages = list(response.context["messages"])
        self.assertTrue(any("Error processing GPX" in str(m) for m in messages))


class BulkUploadViewTest(TestCase):
    """Tests for the bulk_upload view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    def test_get_bulk_upload_form(self):
        """Test GET request displays bulk upload form."""
        response = self.client.get(reverse("bulk_upload"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "form")

    @patch("routes.views.create_route_from_gpx")
    def test_post_multiple_valid_files(self, mock_create):
        """Test bulk uploading multiple valid GPX files."""
        mock_create.return_value = Route.objects.create(name="Test", distance_km=10)

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
                {"default_tags": "hiking", "gpx_files": [file1, file2]},
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(mock_create.call_count, 2)

    @patch("routes.views.create_route_from_gpx")
    def test_partial_failure(self, mock_create):
        """Test bulk upload with some files failing."""
        # First call succeeds, second fails
        mock_create.side_effect = [
            Route.objects.create(name="Success", distance_km=10),
            Exception("Failed to process"),
        ]

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
                reverse("bulk_upload"), {"gpx_files": [file1, file2]}, follow=True
            )

        messages = list(response.context["messages"])
        # Should have both success and warning messages
        self.assertTrue(any("Successfully uploaded 1" in str(m) for m in messages))
        self.assertTrue(any("Failed to upload" in str(m) for m in messages))


class RouteDeleteViewTest(TestCase):
    """Tests for the route_delete view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    def test_post_deletes_route(self):
        """Test POST request deletes the route."""
        route = Route.objects.create(name="To Delete")

        response = self.client.post(
            reverse("route_delete", kwargs={"pk": route.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Route.objects.filter(pk=route.pk).exists())

    def test_get_redirects(self):
        """Test GET request redirects without deleting."""
        route = Route.objects.create(name="Not Deleted")

        response = self.client.get(reverse("route_delete", kwargs={"pk": route.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Route.objects.filter(pk=route.pk).exists())

    def test_delete_404(self):
        """Test deleting non-existent route returns 404."""
        response = self.client.post(reverse("route_delete", kwargs={"pk": 99999}))
        self.assertEqual(response.status_code, 404)


class TagAutocompleteViewTest(TestCase):
    """Tests for the TagAutocompleteView."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    def test_autocomplete_search(self):
        """Test autocomplete search functionality."""
        Tag.objects.create(name="Hiking")
        Tag.objects.create(name="Mountain Hiking")
        Tag.objects.create(name="Beach")

        response = self.client.get(reverse("tag-autocomplete") + "?q=hiking")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should return hiking-related tags
        self.assertGreater(len(data["results"]), 0)

    def test_autocomplete_requires_login(self):
        """Test that autocomplete requires authentication."""
        self.client.logout()
        response = self.client.get(reverse("tag-autocomplete"))
        # Should redirect to login or return 403
        self.assertIn(response.status_code, [302, 403])


class FaviconViewTest(TestCase):
    """Tests for the favicon view."""

    def setUp(self):
        self.client = Client()

    @patch("routes.views.settings")
    def test_favicon_returns_file(self, mock_settings):
        """Test that favicon view returns a file response."""
        # Mock the BASE_DIR to point to a test location
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            mock_settings.BASE_DIR = tmpdir_path

            # Create the necessary directory structure and file
            favicon_dir = tmpdir_path / "staticfiles" / "favicon"
            favicon_dir.mkdir(parents=True, exist_ok=True)
            favicon_file = favicon_dir / "favicon.png"
            favicon_file.write_bytes(b"fake png data")

            response = self.client.get("/favicon.ico")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "image/png")
