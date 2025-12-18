from django_tasks import task
from .models import Route
from .utils import get_location_name, generate_static_map_image, parse_gpx
import hashlib
from datetime import datetime


@task()
def process_route_async(route_id):
    """
    Background task to parse GPX file and process route data.

    This runs asynchronously after a route is uploaded to avoid blocking the upload.
    Handles GPX parsing, geocoding, and thumbnail generation.
    """
    try:
        route = Route.objects.get(pk=route_id)

        # 1. Parse GPX file if not already parsed (distance_km will be 0 if not parsed)
        if route.distance_km == 0 and route.gpx_file:
            try:
                # Open and parse the GPX file from storage
                with route.gpx_file.open('r') as gpx_file:
                    gpx_data = parse_gpx(gpx_file)

                # Update route with parsed data
                route.distance_km = gpx_data["distance_km"]
                route.elevation_gain = gpx_data["elevation_gain"]
                route.start_lat = gpx_data["start_lat"]
                route.start_lon = gpx_data["start_lon"]
                route.end_lat = gpx_data["end_lat"]
                route.end_lon = gpx_data["end_lon"]
                route.route_coordinates = gpx_data["points"]

                # Update name if GPX contains a name and current name is just the filename
                if gpx_data["name"] and route.name.endswith('.gpx'):
                    route.name = gpx_data["name"]

                route.save(update_fields=[
                    "distance_km", "elevation_gain", "start_lat", "start_lon",
                    "end_lat", "end_lon", "route_coordinates", "name"
                ])

            except Exception as e:
                return f"Error parsing GPX for route {route_id}: {str(e)}"

        # 2. Geocoding - Check start points first, then fall back to API
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

        # 3. Generate thumbnail image
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
