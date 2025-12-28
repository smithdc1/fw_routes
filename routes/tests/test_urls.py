"""
Tests for URL routing.
"""

from django.test import TestCase
from django.urls import resolve, reverse

from routes import views


class URLRoutingTest(TestCase):
    """Tests for URL routing and reverse lookups."""

    def test_route_list_url(self):
        """Test route_list URL."""
        url = reverse("route_list")
        self.assertEqual(url, "/")
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.route_list)

    def test_route_upload_url(self):
        """Test route_upload URL."""
        url = reverse("route_upload")
        self.assertEqual(url, "/upload/")
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.route_upload)

    def test_bulk_upload_url(self):
        """Test bulk_upload URL."""
        url = reverse("bulk_upload")
        self.assertEqual(url, "/bulk-upload/")
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.bulk_upload)

    def test_route_detail_url(self):
        """Test route_detail URL."""
        url = reverse("route_detail", kwargs={"pk": 123})
        self.assertEqual(url, "/route/123/")
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.route_detail)

    def test_route_delete_url(self):
        """Test route_delete URL."""
        url = reverse("route_delete", kwargs={"pk": 123})
        self.assertEqual(url, "/route/123/delete/")
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.route_delete)

    def test_route_share_url(self):
        """Test route_share URL."""
        url = reverse("route_share", kwargs={"token": "abc123"})
        self.assertEqual(url, "/share/abc123/")
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.route_share)

    def test_tag_autocomplete_url(self):
        """Test tag-autocomplete URL."""
        url = reverse("tag-autocomplete")
        self.assertEqual(url, "/autocomplete/tags/")
        resolver = resolve(url)
        self.assertTrue(hasattr(resolver.func, "view_class"))
        self.assertEqual(resolver.func.view_class, views.TagAutocompleteView)

    def test_favicon_url(self):
        """Test favicon URL resolves."""
        url = "/favicon.ico"
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.favicon)
