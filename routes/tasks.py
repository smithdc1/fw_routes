from django_tasks import task
from .models import Route
from .utils import get_location_name, generate_static_map_image
import hashlib
from datetime import datetime


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
            thumbnail = generate_static_map_image(route.route_coordinates)
            if thumbnail:
                thumb_filename = f"{hashlib.md5(f'{datetime.now()}{route.name}'.encode()).hexdigest()}.webp"
                route.thumbnail_image.save(thumb_filename, thumbnail, save=True)

        return f"Successfully processed route {route_id}"

    except Route.DoesNotExist:
        return f"Route {route_id} not found"
    except Exception as e:
        # Log the error but don't fail completely
        return f"Error processing route {route_id}: {str(e)}"
