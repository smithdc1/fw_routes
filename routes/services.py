"""
Service functions for route processing.

This module contains business logic extracted from views to avoid code duplication
and improve maintainability.
"""

from django.core.files.base import ContentFile
from .models import Route, Tag
from .utils import parse_gpx
from .tasks import process_route_async


def create_route_from_gpx(gpx_file, name=None, tag_names=None, defer_parsing=False):
    """
    Create a Route object from a GPX file.

    This function handles all the common logic for creating a route from a GPX file,
    including parsing, saving the file, adding tags, and queuing background processing.

    Args:
        gpx_file: UploadedFile object containing GPX data
        name: Optional route name (uses GPX metadata or filename if not provided)
        tag_names: Optional list/iterable of tag names to attach to the route
        defer_parsing: If True, skip parsing and defer to background task (for bulk uploads)

    Returns:
        Route object (saved to database)

    Raises:
        ValueError: If GPX parsing fails (when defer_parsing=False)
        Exception: If route creation fails for any other reason

    Example:
        >>> from django.core.files.uploadedfile import SimpleUploadedFile
        >>> gpx_file = request.FILES['gpx_file']
        >>> route = create_route_from_gpx(gpx_file, name="My Route", tag_names=["hiking", "trail"])
    """
    if defer_parsing:
        # For bulk uploads: create route with minimal info and defer parsing to background
        route = Route(
            name=name or gpx_file.name.replace(".gpx", ""),
            # All other fields have defaults or are nullable
        )
    else:
        # For single uploads: parse GPX file immediately to extract route data
        gpx_data = parse_gpx(gpx_file)

        # Create route with parsed data
        route = Route(
            name=name or gpx_data["name"] or gpx_file.name.replace(".gpx", ""),
            distance_km=gpx_data["distance_km"],
            elevation_gain=gpx_data["elevation_gain"],
            start_lat=gpx_data["start_lat"],
            start_lon=gpx_data["start_lon"],
            end_lat=gpx_data["end_lat"],
            end_lon=gpx_data["end_lon"],
            route_coordinates=gpx_data["points"],  # Store coordinates in database
        )

    # Save GPX file to storage
    gpx_file.seek(0)
    route.gpx_file.save(gpx_file.name, gpx_file, save=False)

    # Save the route object to database
    route.save()

    # Add tags if provided
    if tag_names:
        for tag_name in tag_names:
            tag_name = tag_name.strip()
            if tag_name:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                route.tags.add(tag)

    # Queue background task for geocoding and thumbnail generation
    # (and GPX parsing if deferred)
    process_route_async.enqueue(route.id)

    return route
