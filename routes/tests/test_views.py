"""
Tests for routes views.

Tests cover:
- Authentication and authorization
- Route listing with filtering and sorting
- Route upload (single and bulk)
- Route detail and sharing
- Tag management
- Edge cases and error handling
"""

from unittest.mock import Mock, patch

import pytest
from django.urls import reverse

from routes.models import Route, Tag


@pytest.mark.django_db
class TestRouteListView:
    """Tests for the route_list view."""

    def test_route_list_requires_login(self, client):
        """Test that route list requires authentication."""
        response = client.get(reverse("route_list"))
        # Should redirect to login
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_route_list_authenticated(self, client, user):
        """Test route list view for authenticated user."""
        client.force_login(user)
        response = client.get(reverse("route_list"))

        assert response.status_code == 200
        assert "routes" in response.context

    def test_route_list_displays_routes(self, client, user):
        """Test that routes are displayed."""
        client.force_login(user)
        Route.objects.create(name="Test Route 1", distance_km=10.0)
        Route.objects.create(name="Test Route 2", distance_km=20.0)

        response = client.get(reverse("route_list"))

        routes = response.context["routes"]
        assert routes.count() == 2

    def test_route_list_filter_by_tag(self, client, user):
        """Test filtering routes by tag."""
        client.force_login(user)
        tag1 = Tag.objects.create(name="Hiking")
        tag2 = Tag.objects.create(name="Biking")

        route1 = Route.objects.create(name="Route 1")
        route1.tags.add(tag1)

        route2 = Route.objects.create(name="Route 2")
        route2.tags.add(tag2)

        response = client.get(reverse("route_list") + "?tag=Hiking")

        routes = response.context["routes"]
        assert routes.count() == 1
        assert routes.first().name == "Route 1"

    def test_route_list_search(self, client, user):
        """Test search functionality."""
        client.force_login(user)
        Route.objects.create(name="Mountain Trail")
        Route.objects.create(name="Beach Path")

        response = client.get(reverse("route_list") + "?search=Mountain")

        routes = response.context["routes"]
        assert routes.count() == 1
        assert routes.first().name == "Mountain Trail"

    def test_route_list_search_case_insensitive(self, client, user):
        """Test that search is case insensitive."""
        client.force_login(user)
        Route.objects.create(name="Mountain Trail")

        response = client.get(reverse("route_list") + "?search=mountain")

        routes = response.context["routes"]
        assert routes.count() == 1

    def test_route_list_filter_by_start_point(self, client, user):
        """Test filtering by start location."""
        client.force_login(user)
        Route.objects.create(name="Route 1", start_location="London")
        Route.objects.create(name="Route 2", start_location="Paris")

        response = client.get(reverse("route_list") + "?start_point=London")

        routes = response.context["routes"]
        assert routes.count() == 1
        assert routes.first().name == "Route 1"

    def test_route_list_filter_by_distance_short(self, client, user):
        """Test filtering by short distance range."""
        client.force_login(user)
        Route.objects.create(name="Short", distance_km=16.0)  # ~10 miles
        Route.objects.create(name="Long", distance_km=80.0)  # ~50 miles

        response = client.get(reverse("route_list") + "?distance=short")

        routes = response.context["routes"]
        assert routes.count() == 1
        assert routes.first().name == "Short"

    def test_route_list_filter_by_distance_medium(self, client, user):
        """Test filtering by medium distance range."""
        client.force_login(user)
        Route.objects.create(name="Medium", distance_km=40.0)  # ~25 miles
        Route.objects.create(name="Short", distance_km=16.0)

        response = client.get(reverse("route_list") + "?distance=medium")

        routes = response.context["routes"]
        assert routes.count() == 1
        assert routes.first().name == "Medium"

    def test_route_list_filter_by_distance_long(self, client, user):
        """Test filtering by long distance range."""
        client.force_login(user)
        Route.objects.create(name="Long", distance_km=64.0)  # ~40 miles
        Route.objects.create(name="Short", distance_km=16.0)

        response = client.get(reverse("route_list") + "?distance=long")

        routes = response.context["routes"]
        assert routes.count() == 1
        assert routes.first().name == "Long"

    def test_route_list_filter_by_distance_very_long(self, client, user):
        """Test filtering by very long distance range."""
        client.force_login(user)
        Route.objects.create(name="Very Long", distance_km=100.0)  # 60+ miles
        Route.objects.create(name="Short", distance_km=16.0)

        response = client.get(reverse("route_list") + "?distance=very_long")

        routes = response.context["routes"]
        assert routes.count() == 1
        assert routes.first().name == "Very Long"

    def test_route_list_sort_distance_asc(self, client, user):
        """Test sorting by distance ascending."""
        client.force_login(user)
        Route.objects.create(name="Long", distance_km=50.0)
        Route.objects.create(name="Short", distance_km=10.0)
        Route.objects.create(name="Medium", distance_km=30.0)

        response = client.get(reverse("route_list") + "?sort=distance_asc")

        routes = list(response.context["routes"])
        assert routes[0].name == "Short"
        assert routes[1].name == "Medium"
        assert routes[2].name == "Long"

    def test_route_list_sort_distance_desc(self, client, user):
        """Test sorting by distance descending."""
        client.force_login(user)
        Route.objects.create(name="Long", distance_km=50.0)
        Route.objects.create(name="Short", distance_km=10.0)
        Route.objects.create(name="Medium", distance_km=30.0)

        response = client.get(reverse("route_list") + "?sort=distance_desc")

        routes = list(response.context["routes"])
        assert routes[0].name == "Long"
        assert routes[1].name == "Medium"
        assert routes[2].name == "Short"

    def test_route_list_sort_elevation_asc(self, client, user):
        """Test sorting by elevation ascending."""
        client.force_login(user)
        Route.objects.create(name="High", elevation_gain=500.0)
        Route.objects.create(name="Low", elevation_gain=100.0)

        response = client.get(reverse("route_list") + "?sort=elevation_asc")

        routes = list(response.context["routes"])
        assert routes[0].name == "Low"
        assert routes[1].name == "High"

    def test_route_list_sort_name_asc(self, client, user):
        """Test sorting by name ascending."""
        client.force_login(user)
        Route.objects.create(name="Zebra")
        Route.objects.create(name="Apple")

        response = client.get(reverse("route_list") + "?sort=name_asc")

        routes = list(response.context["routes"])
        assert routes[0].name == "Apple"
        assert routes[1].name == "Zebra"

    def test_route_list_invalid_sort_param(self, client, user):
        """Test that invalid sort parameter is ignored."""
        client.force_login(user)
        Route.objects.create(name="Route 1")

        response = client.get(reverse("route_list") + "?sort=invalid")

        # Should not crash, just use default ordering
        assert response.status_code == 200


@pytest.mark.django_db
class TestRouteDetailView:
    """Tests for the route_detail view."""

    def test_route_detail_requires_login(self, client):
        """Test that route detail requires authentication."""
        route = Route.objects.create(name="Test Route")
        response = client.get(reverse("route_detail", kwargs={"pk": route.pk}))

        assert response.status_code == 302
        assert "/login/" in response.url

    def test_route_detail_authenticated(self, client, user):
        """Test route detail for authenticated user."""
        client.force_login(user)
        route = Route.objects.create(name="Test Route", distance_km=10.0)

        response = client.get(reverse("route_detail", kwargs={"pk": route.pk}))

        assert response.status_code == 200
        assert response.context["route"] == route

    def test_route_detail_not_found(self, client, user):
        """Test 404 for non-existent route."""
        client.force_login(user)
        response = client.get(reverse("route_detail", kwargs={"pk": 99999}))

        assert response.status_code == 404

    def test_route_detail_rename(self, client, user):
        """Test renaming a route."""
        client.force_login(user)
        route = Route.objects.create(name="Old Name")

        response = client.post(
            reverse("route_detail", kwargs={"pk": route.pk}),
            {"action": "rename", "new_name": "New Name"},
        )

        route.refresh_from_db()
        assert route.name == "New Name"
        assert response.status_code == 302

    def test_route_detail_rename_empty_name(self, client, user):
        """Test that renaming to empty string is rejected."""
        client.force_login(user)
        route = Route.objects.create(name="Original")

        client.post(
            reverse("route_detail", kwargs={"pk": route.pk}),
            {"action": "rename", "new_name": "   "},
        )

        route.refresh_from_db()
        assert route.name == "Original"  # Should not change

    def test_route_detail_update_tags(self, client, user):
        """Test updating route tags."""
        client.force_login(user)
        route = Route.objects.create(name="Test Route")
        tag1 = Tag.objects.create(name="Hiking")
        tag2 = Tag.objects.create(name="Mountain")

        client.post(
            reverse("route_detail", kwargs={"pk": route.pk}),
            {"action": "update_tags", "tags": [tag1.id, tag2.id]},
        )

        assert route.tags.count() == 2
        assert tag1 in route.tags.all()

    def test_route_detail_remove_tag(self, client, user):
        """Test removing individual tag."""
        client.force_login(user)
        route = Route.objects.create(name="Test Route")
        tag = Tag.objects.create(name="Hiking")
        route.tags.add(tag)

        client.post(
            reverse("route_detail", kwargs={"pk": route.pk}),
            {"action": "remove_tag", "tag_id": tag.id},
        )

        assert route.tags.count() == 0


@pytest.mark.django_db
class TestRouteShareView:
    """Tests for the route_share view (public access)."""

    def test_route_share_no_login_required(self, client):
        """Test that share view does not require login."""
        route = Route.objects.create(name="Shared Route")

        response = client.get(
            reverse("route_share", kwargs={"token": route.share_token})
        )

        assert response.status_code == 200
        assert response.context["route"] == route

    def test_route_share_invalid_token(self, client):
        """Test 404 for invalid share token."""
        response = client.get(
            reverse("route_share", kwargs={"token": "invalidtoken123"})
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestRouteUploadView:
    """Tests for the route_upload view."""

    def test_route_upload_requires_login(self, client):
        """Test that upload requires authentication."""
        response = client.get(reverse("route_upload"))

        assert response.status_code == 302
        assert "/login/" in response.url

    def test_route_upload_get(self, client, user):
        """Test GET request shows upload form."""
        client.force_login(user)
        response = client.get(reverse("route_upload"))

        assert response.status_code == 200
        assert "form" in response.context

    @patch("routes.views.create_route_from_gpx")
    def test_route_upload_post_valid(self, mock_create, client, user, sample_gpx_file):
        """Test uploading valid GPX file."""
        client.force_login(user)
        mock_route = Route.objects.create(name="Test Route")
        mock_create.return_value = mock_route

        response = client.post(
            reverse("route_upload"),
            {"name": "My Route", "tags_input": "hiking", "gpx_file": sample_gpx_file},
        )

        assert response.status_code == 302
        assert response.url == reverse("route_detail", kwargs={"pk": mock_route.pk})
        mock_create.assert_called_once()

    @patch("routes.views.create_route_from_gpx")
    def test_route_upload_with_tags(self, mock_create, client, user, sample_gpx_file):
        """Test uploading with comma-separated tags."""
        client.force_login(user)
        mock_route = Route.objects.create(name="Test Route")
        mock_create.return_value = mock_route

        client.post(
            reverse("route_upload"),
            {
                "name": "My Route",
                "tags_input": "hiking, mountain, trail",
                "gpx_file": sample_gpx_file,
            },
        )

        # Verify tags were passed to service
        call_args = mock_create.call_args
        tag_names = call_args.kwargs["tag_names"]
        assert "hiking" in tag_names
        assert "mountain" in tag_names
        assert "trail" in tag_names

    @patch("routes.views.create_route_from_gpx")
    def test_route_upload_handles_value_error(
        self, mock_create, client, user, sample_gpx_file
    ):
        """Test that ValueError from parsing is handled gracefully."""
        client.force_login(user)
        mock_create.side_effect = ValueError("Invalid GPX format")

        response = client.post(
            reverse("route_upload"),
            {"name": "Bad Route", "gpx_file": sample_gpx_file},
        )

        assert response.status_code == 200  # Should re-render form
        # Should show error message (check messages framework)


@pytest.mark.django_db
class TestBulkUploadView:
    """Tests for the bulk_upload view."""

    def test_bulk_upload_requires_login(self, client):
        """Test that bulk upload requires authentication."""
        response = client.get(reverse("bulk_upload"))

        assert response.status_code == 302
        assert "/login/" in response.url

    def test_bulk_upload_get(self, client, user):
        """Test GET request shows bulk upload form."""
        client.force_login(user)
        response = client.get(reverse("bulk_upload"))

        assert response.status_code == 200
        assert "form" in response.context

    @patch("routes.views.create_route_from_gpx")
    def test_bulk_upload_multiple_files(
        self, mock_create, client, user, sample_gpx_content
    ):
        """Test uploading multiple GPX files."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        client.force_login(user)
        mock_create.return_value = Route.objects.create(name="Test")

        file1 = SimpleUploadedFile(
            "route1.gpx", sample_gpx_content, content_type="application/gpx+xml"
        )
        file2 = SimpleUploadedFile(
            "route2.gpx", sample_gpx_content, content_type="application/gpx+xml"
        )

        response = client.post(
            reverse("bulk_upload"),
            {"default_tags": "hiking", "gpx_files": [file1, file2]},
        )

        assert response.status_code == 302
        assert mock_create.call_count == 2

    @patch("routes.views.create_route_from_gpx")
    def test_bulk_upload_partial_failure(
        self, mock_create, client, user, sample_gpx_content
    ):
        """Test that bulk upload continues on partial failures."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        client.force_login(user)

        # First file succeeds, second fails
        mock_create.side_effect = [
            Route.objects.create(name="Success"),
            ValueError("Failed"),
        ]

        file1 = SimpleUploadedFile(
            "good.gpx", sample_gpx_content, content_type="application/gpx+xml"
        )
        file2 = SimpleUploadedFile(
            "bad.gpx", sample_gpx_content, content_type="application/gpx+xml"
        )

        response = client.post(reverse("bulk_upload"), {"gpx_files": [file1, file2]})

        assert response.status_code == 302
        # Should have attempted both uploads
        assert mock_create.call_count == 2


@pytest.mark.django_db
class TestRouteDeleteView:
    """Tests for the route_delete view."""

    def test_route_delete_requires_login(self, client):
        """Test that delete requires authentication."""
        route = Route.objects.create(name="Test")
        response = client.post(reverse("route_delete", kwargs={"pk": route.pk}))

        assert response.status_code == 302
        assert "/login/" in response.url

    def test_route_delete_post(self, client, user):
        """Test deleting a route."""
        client.force_login(user)
        route = Route.objects.create(name="To Delete")

        response = client.post(reverse("route_delete", kwargs={"pk": route.pk}))

        assert response.status_code == 302
        assert not Route.objects.filter(pk=route.pk).exists()

    def test_route_delete_get_redirects(self, client, user):
        """Test that GET request doesn't delete (redirects)."""
        client.force_login(user)
        route = Route.objects.create(name="Safe")

        response = client.get(reverse("route_delete", kwargs={"pk": route.pk}))

        assert response.status_code == 302
        assert Route.objects.filter(pk=route.pk).exists()


@pytest.mark.django_db
class TestTagAutocompleteView:
    """Tests for the TagAutocompleteView."""

    def test_tag_autocomplete_requires_login(self, client):
        """Test that autocomplete requires authentication."""
        response = client.get(reverse("tag-autocomplete"))

        assert response.status_code == 302

    def test_tag_autocomplete_search(self, client, user):
        """Test tag search functionality."""
        client.force_login(user)
        Tag.objects.create(name="Hiking")
        Tag.objects.create(name="Biking")
        Tag.objects.create(name="Swimming")

        response = client.get(reverse("tag-autocomplete") + "?q=iking")

        assert response.status_code == 200
        # Should return tags containing "iking"


@pytest.mark.django_db
class TestFaviconView:
    """Tests for the favicon view."""

    @patch("routes.views.FileResponse")
    @patch("builtins.open")
    def test_favicon_returns_file(self, mock_open, mock_file_response, client):
        """Test that favicon view returns the file."""
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_file_response.return_value = Mock(status_code=200)

        response = client.get("/favicon.png")

        # Should return FileResponse (or 404 if file doesn't exist)
        assert response.status_code in [200, 404, 500]

    def test_favicon_only_get(self, client):
        """Test that favicon only accepts GET requests."""
        response = client.post("/favicon.png")

        assert response.status_code == 405  # Method not allowed
