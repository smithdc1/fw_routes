from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.core.files.base import ContentFile
from django_tomselect.autocompletes import AutocompleteModelView
from .models import Route, Tag, StartPoint
from .forms import RouteUploadForm, BulkUploadForm, TagForm
from .services import create_route_from_gpx, queue_route_from_gpx
import hashlib
from datetime import datetime
import json


@login_required
def route_list(request):
    """List all routes with filtering"""
    routes = Route.objects.all().prefetch_related("tags")

    # Filter by tag if provided
    tag_filter = request.GET.get("tag")
    if tag_filter:
        routes = routes.filter(tags__name=tag_filter)

    # Search
    search = request.GET.get("search")
    if search:
        routes = routes.filter(name__icontains=search)

    # Filter by start point if provided
    start_point_filter = request.GET.get("start_point")
    if start_point_filter:
        routes = routes.filter(start_location=start_point_filter)

    # Filter by distance range
    distance_filter = request.GET.get("distance")
    if distance_filter:
        # Distance ranges in kilometers (stored in DB)
        # Based on actual data: shortest=10.2mi, longest=50+mi
        if distance_filter == "short":
            routes = routes.filter(distance_km__lte=32.19)  # up to 20 miles
        elif distance_filter == "medium":
            routes = routes.filter(
                distance_km__gt=32.19, distance_km__lte=56.33
            )  # 20-35 miles
        elif distance_filter == "long":
            routes = routes.filter(
                distance_km__gt=56.33, distance_km__lte=80.47
            )  # 35-50 miles
        elif distance_filter == "very_long":
            routes = routes.filter(distance_km__gt=80.47)  # 50+ miles

    # Sorting
    sort_by = request.GET.get("sort", "distance_asc")  # Default: distance low to high
    valid_sorts = {
        "distance_asc": "distance_km",
        "distance_desc": "-distance_km",
        "elevation_asc": "elevation_gain",
        "elevation_desc": "-elevation_gain",
        "name_asc": "name",
        "name_desc": "-name",
    }

    if sort_by in valid_sorts:
        routes = routes.order_by(valid_sorts[sort_by])

    context = {
        "routes": routes,
        "all_tags": Tag.objects.all(),
        "active_tag": tag_filter,
        "all_start_points": StartPoint.objects.all(),
        "active_start_point": start_point_filter,
        "search_query": search,
        "active_distance": distance_filter,
        "active_sort": sort_by,
    }
    return render(request, "routes/route_list.html", context)


@login_required
def route_detail(request, pk):
    """Show detailed route information"""
    route = get_object_or_404(Route, pk=pk)

    if request.method == "POST":
        # Handle different actions
        action = request.POST.get("action")

        if action == "rename":
            new_name = request.POST.get("new_name", "").strip()
            if new_name:
                route.name = new_name
                route.save()
                messages.success(request, f'Route renamed to "{new_name}"')
            else:
                messages.error(request, "Route name cannot be empty")

        elif action == "update_tags":
            # Handle the TomSelect form submission
            form = TagForm(request.POST)
            if form.is_valid():
                # Set all tags from the form
                route.tags.set(form.cleaned_data["tags"])
                messages.success(request, "Tags updated successfully")
            else:
                # Show specific validation errors
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                if not form.errors:
                    messages.error(request, "Error updating tags")

        elif action == "remove_tag":
            # Keep existing individual tag removal functionality
            tag_id = request.POST.get("tag_id")
            if tag_id:
                route.tags.remove(tag_id)
                messages.success(request, "Tag removed")

        return redirect("route_detail", pk=pk)

    # GET request - initialize form with current tags
    tag_form = TagForm(initial={"tags": route.tags.all()})

    context = {
        "route": route,
        "tag_form": tag_form,
        "share_url": request.build_absolute_uri(route.get_share_url()),
        "route_coordinates": route.route_coordinates,
    }
    return render(request, "routes/route_detail.html", context)


def route_share(request, token):
    """Public route view accessible via share link (no login required)"""
    route = get_object_or_404(Route, share_token=token)

    context = {"route": route, "route_coordinates": route.route_coordinates}
    return render(request, "routes/route_detail.html", context)


@login_required
def route_upload(request):
    """Upload a single GPX file"""
    if request.method == "POST":
        form = RouteUploadForm(request.POST, request.FILES)
        if form.is_valid():
            gpx_file = request.FILES["gpx_file"]

            # Extract form data
            name = form.cleaned_data.get("name")
            tags_input = form.cleaned_data.get("tags_input", "")
            tag_names = [t.strip() for t in tags_input.split(",") if t.strip()]

            try:
                # Use service layer to create route (consolidates business logic)
                route = create_route_from_gpx(gpx_file, name=name, tag_names=tag_names)

                messages.success(
                    request,
                    f'Route "{route.name}" uploaded successfully! '
                    "Location and thumbnail are being processed.",
                )
                return redirect("route_detail", pk=route.pk)
            except ValueError as e:
                messages.error(request, f"Error processing GPX file: {e}")
            except Exception as e:
                messages.error(request, f"Unexpected error: {e}")
    else:
        form = RouteUploadForm()

    return render(request, "routes/route_upload.html", {"form": form})


@login_required
def bulk_upload(request):
    """Bulk upload multiple GPX files"""
    if request.method == "POST":
        form = BulkUploadForm(request.POST, request.FILES)
        files = request.FILES.getlist("gpx_files")

        if form.is_valid() and files:
            default_tags = form.cleaned_data.get("default_tags", "")
            tag_names = [t.strip() for t in default_tags.split(",") if t.strip()]

            uploaded_count = 0
            failed_files = []

            for gpx_file in files:
                try:
                    # Queue route for background processing to prevent timeouts
                    # This defers S3 upload, parsing, geocoding, and thumbnails
                    queue_route_from_gpx(gpx_file, tag_names=tag_names)
                    uploaded_count += 1
                except Exception as e:
                    failed_files.append(f"{gpx_file.name} ({str(e)})")

            if uploaded_count > 0:
                messages.success(
                    request,
                    f"Successfully uploaded {uploaded_count} route(s)! "
                    "Routes are being processed in the background (parsing, locations, and thumbnails).",
                )

            if failed_files:
                messages.warning(
                    request, f"Failed to upload: {', '.join(failed_files)}"
                )

            return redirect("route_list")
    else:
        form = BulkUploadForm()

    return render(request, "routes/bulk_upload.html", {"form": form})


@login_required
def route_delete(request, pk):
    """Delete a route"""
    route = get_object_or_404(Route, pk=pk)

    if request.method == "POST":
        route.delete()
        messages.success(request, f'Route "{route.name}" has been deleted')
        return redirect("route_list")

    # If not POST, redirect back to detail page
    return redirect("route_detail", pk=pk)


class TagAutocompleteView(AutocompleteModelView):
    """Autocomplete view for tag selection with creation support"""

    model = Tag
    search_lookups = ["name__icontains"]
    value_fields = ["id", "name"]
    ordering = ["name"]

    # Require login
    login_required = True

    def create_object(self, text):
        """Create new tag with normalization (uses Tag.normalize_name)"""
        normalized_name = Tag.normalize_name(text)
        tag, created = Tag.objects.get_or_create(name=normalized_name)
        return tag

    def get_list_url(self):
        """Disable list URL"""
        return ""

    def get_create_url(self):
        """Disable create URL"""
        return ""
