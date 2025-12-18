from django_tasks import task
from django.core.files.base import ContentFile
from .models import Route, Tag
from .utils import get_location_name, generate_static_map_image, parse_gpx
import hashlib
from datetime import datetime
import io


@task()
def process_route_async(route_id):
    """
    Background task to process route geocoding and thumbnail generation.

    This runs asynchronously after a route is uploaded to avoid blocking the upload.
    """
    try:
        route = Route.objects.get(pk=route_id)

        # 1. Geocoding - Check start points first, then fall back to API
        if route.start_lat and route.start_lon and not route.start_location:
            # Try to find a matching start point within 250m
            from .utils import find_closest_start_point

            start_point = find_closest_start_point(
                route.start_lat, route.start_lon, max_distance_meters=250
            )

            if start_point:
                # Use the predefined start point name
                route.start_location = start_point.name
                route.save(update_fields=["start_location"])
            else:
                # Fall back to geocoding API
                location_name = get_location_name(route.start_lat, route.start_lon)
                if location_name:
                    route.start_location = location_name
                    route.save(update_fields=["start_location"])

        # 2. Generate thumbnail image
        if route.route_coordinates and not route.thumbnail_image:
            thumbnail = generate_static_map_image(
                route.route_coordinates, width=800, height=200
            )
            if thumbnail:
                thumb_filename = f"{hashlib.md5(f'{datetime.now()}{route.name}'.encode()).hexdigest()}.png"
                route.thumbnail_image.save(thumb_filename, thumbnail, save=True)

        return f"Successfully processed route {route_id}"

    except Route.DoesNotExist:
        return f"Route {route_id} not found"
    except Exception as e:
        # Log the error but don't fail completely
        return f"Error processing route {route_id}: {str(e)}"


@task()
def process_route_deferred(file_content, file_name, route_name=None, tag_names=None):
    """
    Background task to handle complete route creation from GPX file (for bulk uploads).

    This task handles file upload to S3, GPX parsing, geocoding, and thumbnail generation.
    This prevents timeouts during bulk uploads by deferring all slow operations.

    Args:
        file_content: Raw bytes of the GPX file
        file_name: Original filename
        route_name: Optional route name
        tag_names: Optional list of tag names
    """
    try:
        # 1. Parse GPX file from bytes (convert to text mode for gpxpy)
        gpx_text = file_content.decode('utf-8')
        gpx_file_obj = io.StringIO(gpx_text)
        gpx_data = parse_gpx(gpx_file_obj)

        # 2. Create route with parsed data
        route = Route(
            name=route_name or gpx_data["name"] or file_name.replace(".gpx", ""),
            distance_km=gpx_data["distance_km"],
            elevation_gain=gpx_data["elevation_gain"],
            start_lat=gpx_data["start_lat"],
            start_lon=gpx_data["start_lon"],
            end_lat=gpx_data["end_lat"],
            end_lon=gpx_data["end_lon"],
            route_coordinates=gpx_data["points"],
        )

        # 3. Save GPX file to S3 storage (this is the slow operation we're deferring)
        gpx_file_obj.seek(0)
        route.gpx_file.save(file_name, ContentFile(file_content), save=False)

        # 4. Save route to database
        route.save()

        # 5. Add tags if provided
        if tag_names:
            for tag_name in tag_names:
                tag_name = tag_name.strip()
                if tag_name:
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    route.tags.add(tag)

        # 6. Geocoding - Check start points first, then fall back to API
        if route.start_lat and route.start_lon:
            from .utils import find_closest_start_point

            start_point = find_closest_start_point(
                route.start_lat, route.start_lon, max_distance_meters=250
            )

            if start_point:
                route.start_location = start_point.name
                route.save(update_fields=["start_location"])
            else:
                location_name = get_location_name(route.start_lat, route.start_lon)
                if location_name:
                    route.start_location = location_name
                    route.save(update_fields=["start_location"])

        # 7. Generate thumbnail image
        if route.route_coordinates:
            thumbnail = generate_static_map_image(
                route.route_coordinates, width=800, height=200
            )
            if thumbnail:
                thumb_filename = f"{hashlib.md5(f'{datetime.now()}{route.name}'.encode()).hexdigest()}.png"
                route.thumbnail_image.save(thumb_filename, thumbnail, save=True)

        return f"Successfully created and processed route from {file_name}"

    except Exception as e:
        # Log the error
        return f"Error creating route from {file_name}: {str(e)}"
