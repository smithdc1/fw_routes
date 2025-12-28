"""
Tests for admin configuration.
"""

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import Client, TestCase

from routes.admin import RouteAdmin, StartPointAdmin, TagAdmin
from routes.models import Route, StartPoint, Tag


class AdminRegistrationTest(TestCase):
    """Tests for admin registration."""

    def test_route_admin_registered(self):
        """Test that Route model is registered in admin."""
        self.assertIn(Route, admin.site._registry)
        self.assertIsInstance(admin.site._registry[Route], RouteAdmin)

    def test_tag_admin_registered(self):
        """Test that Tag model is registered in admin."""
        self.assertIn(Tag, admin.site._registry)
        self.assertIsInstance(admin.site._registry[Tag], TagAdmin)

    def test_start_point_admin_registered(self):
        """Test that StartPoint model is registered in admin."""
        self.assertIn(StartPoint, admin.site._registry)
        self.assertIsInstance(admin.site._registry[StartPoint], StartPointAdmin)


class RouteAdminTest(TestCase):
    """Tests for RouteAdmin configuration."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", password="adminpass", email="admin@example.com"
        )
        self.client = Client()
        self.client.login(username="admin", password="adminpass")

    def test_route_list_display(self):
        """Test list_display fields."""
        route_admin = RouteAdmin(Route, admin.site)
        expected = ["name", "distance_km", "start_location", "uploaded_at"]
        self.assertEqual(route_admin.list_display, expected)

    def test_route_list_filter(self):
        """Test list_filter fields."""
        route_admin = RouteAdmin(Route, admin.site)
        expected = ["tags", "uploaded_at"]
        self.assertEqual(route_admin.list_filter, expected)

    def test_route_search_fields(self):
        """Test search_fields."""
        route_admin = RouteAdmin(Route, admin.site)
        expected = ["name", "start_location"]
        self.assertEqual(route_admin.search_fields, expected)

    def test_route_readonly_fields(self):
        """Test readonly_fields."""
        route_admin = RouteAdmin(Route, admin.site)
        expected = ["share_token", "uploaded_at"]
        self.assertEqual(route_admin.readonly_fields, expected)

    def test_route_filter_horizontal(self):
        """Test filter_horizontal for tags."""
        route_admin = RouteAdmin(Route, admin.site)
        expected = ["tags"]
        self.assertEqual(route_admin.filter_horizontal, expected)

    def test_route_admin_changelist_view(self):
        """Test that route admin changelist view loads."""
        Route.objects.create(name="Test Route", distance_km=10)

        response = self.client.get("/admin/routes/route/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Route")


class TagAdminTest(TestCase):
    """Tests for TagAdmin configuration."""

    def test_tag_list_display(self):
        """Test list_display fields."""
        tag_admin = TagAdmin(Tag, admin.site)
        expected = ["name", "created_at"]
        self.assertEqual(tag_admin.list_display, expected)

    def test_tag_search_fields(self):
        """Test search_fields."""
        tag_admin = TagAdmin(Tag, admin.site)
        expected = ["name"]
        self.assertEqual(tag_admin.search_fields, expected)


class StartPointAdminTest(TestCase):
    """Tests for StartPointAdmin configuration."""

    def test_start_point_list_display(self):
        """Test list_display fields."""
        sp_admin = StartPointAdmin(StartPoint, admin.site)
        expected = ("name", "latitude", "longitude", "created_at")
        self.assertEqual(sp_admin.list_display, expected)

    def test_start_point_search_fields(self):
        """Test search_fields."""
        sp_admin = StartPointAdmin(StartPoint, admin.site)
        expected = ("name", "description")
        self.assertEqual(sp_admin.search_fields, expected)

    def test_start_point_list_filter(self):
        """Test list_filter."""
        sp_admin = StartPointAdmin(StartPoint, admin.site)
        expected = ("created_at",)
        self.assertEqual(sp_admin.list_filter, expected)

    def test_start_point_ordering(self):
        """Test ordering."""
        sp_admin = StartPointAdmin(StartPoint, admin.site)
        expected = ("name",)
        self.assertEqual(sp_admin.ordering, expected)
