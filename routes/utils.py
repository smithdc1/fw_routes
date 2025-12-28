import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen

import folium
import gpxpy
from django.core.files.base import ContentFile


def parse_gpx(gpx_file):
    """Parse GPX file and extract route data"""
    gpx_file.seek(0)
    gpx = gpxpy.parse(gpx_file)

    data = {
        "name": "",
        "distance_km": 0,
        "elevation_gain": 0,
        "points": [],
        "start_lat": None,
        "start_lon": None,
    }

    # Get track data
    for track in gpx.tracks:
        if not data["name"] and track.name:
            data["name"] = track.name

        for segment in track.segments:
            for point in segment.points:
                data["points"].append((point.latitude, point.longitude))

    # Get route data if no tracks
    if not data["points"]:
        for route in gpx.routes:
            if not data["name"] and route.name:
                data["name"] = route.name
            for point in route.points:
                data["points"].append((point.latitude, point.longitude))

    # Get waypoints if no tracks/routes
    if not data["points"]:
        for waypoint in gpx.waypoints:
            data["points"].append((waypoint.latitude, waypoint.longitude))

    # Calculate distance and elevation
    if data["points"]:
        data["start_lat"] = data["points"][0][0]
        data["start_lon"] = data["points"][0][1]

    # Use gpxpy's built-in calculations
    for track in gpx.tracks:
        data["distance_km"] += track.length_3d() / 1000 if track.length_3d() else 0
        uphill, downhill = track.get_uphill_downhill()
        data["elevation_gain"] += uphill if uphill else 0

    for route in gpx.routes:
        data["distance_km"] += route.length_3d() / 1000 if route.length_3d() else 0
        uphill, downhill = route.get_uphill_downhill()
        data["elevation_gain"] += uphill if uphill else 0

    return data


def get_location_name(lat, lon):
    """Get location name from coordinates using reverse geocoding"""
    try:
        # Using Nominatim (OpenStreetMap) - free, no API key needed
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        req = Request(url, headers={"User-Agent": "GPXRoutesApp/1.0"})

        with urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            # Try to get a nice readable location
            address = data.get("address", {})
            parts = []

            if address.get("road"):
                parts.append(address["road"])
            if address.get("city"):
                parts.append(address["city"])
            elif address.get("town"):
                parts.append(address["town"])
            elif address.get("village"):
                parts.append(address["village"])

            if address.get("state"):
                parts.append(address["state"])

            return ", ".join(parts) if parts else data.get("display_name", "")
    except (URLError, Exception) as e:
        print(f"Geocoding error: {e}")

    return f"{lat:.4f}, {lon:.4f}"


def generate_static_map_image(points, width=500, height=200):
    """
    Generate a static WebP thumbnail with basemap for list view.

    Uses Playwright to render a folium map to PNG, then converts to WebP
    for better compression.
    """
    if not points:
        return None

    import io
    import tempfile
    import time

    from PIL import Image
    from playwright.sync_api import sync_playwright

    # Calculate bounds of the route
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]

    # Create folium map
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)

    m = folium.Map(
        location=[center_lat, center_lon],
        tiles="OpenStreetMap",
        width=width,
        height=height,
        zoom_control=False,
        scrollWheelZoom=False,
        dragging=False,
        attributionControl=False,
    )

    # Fit the map to show the entire route with some padding
    m.fit_bounds(bounds, padding=[20, 20])

    # Add route line
    folium.PolyLine(points, color="#0d6efd", weight=4, opacity=0.85).add_to(m)

    # Start marker
    folium.CircleMarker(
        points[0],
        radius=8,
        color="white",
        fill=True,
        fillColor="#28a745",
        fillOpacity=1,
        weight=3,
    ).add_to(m)

    # End marker
    folium.CircleMarker(
        points[-1],
        radius=8,
        color="white",
        fill=True,
        fillColor="#dc3545",
        fillOpacity=1,
        weight=3,
    ).add_to(m)

    # Save to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        temp_path = f.name
        m.save(temp_path)

    try:
        # Render with Playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(f"file://{temp_path}")

            # Wait for tiles to load
            time.sleep(2)

            # Take screenshot as PNG (Playwright doesn't support WebP)
            png_bytes = page.screenshot(type="png", full_page=False)
            browser.close()

        # Clean up temp file
        os.unlink(temp_path)

        # Check if we got a valid image (tiles loaded)
        if len(png_bytes) > 5000:  # Reasonable minimum size
            # Convert PNG to WebP for better compression
            png_image = Image.open(io.BytesIO(png_bytes))
            webp_buffer = io.BytesIO()
            png_image.save(webp_buffer, format="WebP", quality=85)
            webp_buffer.seek(0)

            return ContentFile(webp_buffer.read(), name="route_preview.webp")
        else:
            print("Playwright screenshot too small - tiles may not have loaded")
            return None

    except Exception as e:
        print(f"Playwright rendering failed: {e}")
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return None


def calculate_distance_meters(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates using Haversine formula.
    Returns distance in meters.
    """
    from math import atan2, cos, radians, sin, sqrt

    R = 6371000  # Earth radius in meters

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance


def find_closest_start_point(latitude, longitude, max_distance_meters=250):
    """
    Find the closest StartPoint within max_distance_meters.
    Returns StartPoint object if found, None otherwise.
    """
    from .models import StartPoint

    closest_point = None
    min_distance = float("inf")

    for start_point in StartPoint.objects.all():
        distance = calculate_distance_meters(
            latitude, longitude, start_point.latitude, start_point.longitude
        )

        if distance < min_distance and distance <= max_distance_meters:
            min_distance = distance
            closest_point = start_point

    return closest_point
