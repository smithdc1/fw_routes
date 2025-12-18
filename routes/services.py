"""
Service functions for route processing.

This module contains business logic extracted from views to avoid code duplication
and improve maintainability.
"""

from django.core.files.base import ContentFile
from .models import Route, Tag
from .utils import parse_gpx
from .tasks import process_route_async, process_route_deferred


def create_route_from_gpx(gpx_file, name=None, tag_names=None):
    """
    Create a Route object from a GPX file (for single uploads).

    This function parses the GPX immediately and saves the file to storage,
    then queues background processing for geocoding and thumbnails.

    Args:
        gpx_file: UploadedFile object containing GPX data
        name: Optional route name (uses GPX metadata or filename if not provided)
        tag_names: Optional list/iterable of tag names to attach to the route

    Returns:
        Route object (saved to database)

    Raises:
        ValueError: If GPX parsing fails
        Exception: If route creation fails for any other reason

    Example:
        >>> from django.core.files.uploadedfile import SimpleUploadedFile
        >>> gpx_file = request.FILES['gpx_file']
        >>> route = create_route_from_gpx(gpx_file, name="My Route", tag_names=["hiking", "trail"])
    """
    # Parse GPX file immediately to extract route data
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
    process_route_async.enqueue(route.id)

    return route


def queue_route_from_gpx(gpx_file, name=None, tag_names=None):
    """
    Queue a route for deferred processing (for bulk uploads).

    This function reads the file content and queues a background task to handle
    file upload to S3 and parsing. This prevents timeouts during bulk uploads.

    Args:
        gpx_file: UploadedFile object containing GPX data
        name: Optional route name (uses filename if not provided)
        tag_names: Optional list/iterable of tag names to attach to the route

    Returns:
        None (processing happens in background)

    Example:
        >>> gpx_file = request.FILES['gpx_file']
        >>> queue_route_from_gpx(gpx_file, tag_names=["hiking", "trail"])
    """
    # Read the file content into memory as bytes
    gpx_file.seek(0)
    file_content = gpx_file.read()

    # Ensure we always have bytes for consistent serialization
    if isinstance(file_content, str):
        file_content = file_content.encode('utf-8')

    file_name = gpx_file.name

    # Queue background task with file data (always as bytes)
    # This task will handle S3 upload, parsing, and all other processing
    process_route_deferred.enqueue(
        file_content=file_content,
        file_name=file_name,
        route_name=name,
        tag_names=tag_names or []
    )

