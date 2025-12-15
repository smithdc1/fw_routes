import gpxpy
import folium
from io import BytesIO
from django.core.files.base import ContentFile
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
import os


def parse_gpx(gpx_file):
    """Parse GPX file and extract route data"""
    gpx_file.seek(0)
    gpx = gpxpy.parse(gpx_file)
    
    data = {
        'name': '',
        'distance_km': 0,
        'elevation_gain': 0,
        'points': [],
        'start_lat': None,
        'start_lon': None,
        'end_lat': None,
        'end_lon': None,
    }
    
    # Get track data
    for track in gpx.tracks:
        if not data['name'] and track.name:
            data['name'] = track.name
        
        for segment in track.segments:
            for point in segment.points:
                data['points'].append((point.latitude, point.longitude))
    
    # Get route data if no tracks
    if not data['points']:
        for route in gpx.routes:
            if not data['name'] and route.name:
                data['name'] = route.name
            for point in route.points:
                data['points'].append((point.latitude, point.longitude))
    
    # Get waypoints if no tracks/routes
    if not data['points']:
        for waypoint in gpx.waypoints:
            data['points'].append((waypoint.latitude, waypoint.longitude))
    
    # Calculate distance and elevation
    if data['points']:
        data['start_lat'] = data['points'][0][0]
        data['start_lon'] = data['points'][0][1]
        data['end_lat'] = data['points'][-1][0]
        data['end_lon'] = data['points'][-1][1]
    
    # Use gpxpy's built-in calculations
    for track in gpx.tracks:
        data['distance_km'] += track.length_3d() / 1000 if track.length_3d() else 0
        uphill, downhill = track.get_uphill_downhill()
        data['elevation_gain'] += uphill if uphill else 0
    
    for route in gpx.routes:
        data['distance_km'] += route.length_3d() / 1000 if route.length_3d() else 0
        uphill, downhill = route.get_uphill_downhill()
        data['elevation_gain'] += uphill if uphill else 0
    
    return data


def get_location_name(lat, lon):
    """Get location name from coordinates using reverse geocoding"""
    try:
        # Using Nominatim (OpenStreetMap) - free, no API key needed
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        headers = {'User-Agent': 'GPXRoutesApp/1.0'}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            # Try to get a nice readable location
            address = data.get('address', {})
            parts = []
            
            if address.get('road'):
                parts.append(address['road'])
            if address.get('city'):
                parts.append(address['city'])
            elif address.get('town'):
                parts.append(address['town'])
            elif address.get('village'):
                parts.append(address['village'])
            
            if address.get('state'):
                parts.append(address['state'])
            
            return ', '.join(parts) if parts else data.get('display_name', '')
    except Exception as e:
        print(f"Geocoding error: {e}")
    
    return f"{lat:.4f}, {lon:.4f}"


def generate_static_map_image(points, width=800, height=200):
    """
    Generate a static PNG thumbnail with basemap for list view.
    
    Uses Playwright to render a folium map to PNG with OpenStreetMap tiles.
    This creates production-quality thumbnails with proper map context.
    
    Falls back to matplotlib if Playwright is unavailable or tiles don't load.
    """
    if not points:
        return None
    
    try:
        # Try Playwright method first (best quality)
        from playwright.sync_api import sync_playwright
        import time
        import tempfile
        
        # Create folium map
        center_lat = sum(p[0] for p in points) / len(points)
        center_lon = sum(p[1] for p in points) / len(points)
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            tiles='OpenStreetMap',
            width=width,
            height=height,
            zoom_control=False,
            scrollWheelZoom=False,
            dragging=False,
            attributionControl=False
        )
        
        # Add route line
        folium.PolyLine(
            points,
            color='#0d6efd',
            weight=4,
            opacity=0.85
        ).add_to(m)
        
        # Start marker
        folium.CircleMarker(
            points[0],
            radius=8,
            color='white',
            fill=True,
            fillColor='#28a745',
            fillOpacity=1,
            weight=3
        ).add_to(m)
        
        # End marker
        folium.CircleMarker(
            points[-1],
            radius=8,
            color='white',
            fill=True,
            fillColor='#dc3545',
            fillOpacity=1,
            weight=3
        ).add_to(m)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            temp_path = f.name
            m.save(temp_path)
        
        try:
            # Render with Playwright
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={'width': width, 'height': height})
                page.goto(f'file://{temp_path}')
                
                # Wait for tiles to load
                time.sleep(2)
                
                # Take screenshot
                screenshot_bytes = page.screenshot(type='png', full_page=False)
                browser.close()
            
            # Clean up temp file
            os.unlink(temp_path)
            
            # Check if we got a valid image (tiles loaded)
            if len(screenshot_bytes) > 5000:  # Reasonable minimum size
                return ContentFile(screenshot_bytes, name='route_preview.png')
            else:
                print("Playwright screenshot too small, falling back to matplotlib")
                raise Exception("Tiles didn't load")
                
        except Exception as e:
            print(f"Playwright rendering failed: {e}")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
            
    except Exception as e:
        print(f"Falling back to matplotlib method: {e}")
        # Fallback to matplotlib (no basemap but works offline)
        return _generate_simple_thumbnail(points, width, height)


def _generate_simple_thumbnail(points, width=800, height=200):
    """
    Fallback method: Generate simple PNG without basemap using matplotlib.
    Used when Playwright is unavailable or network issues prevent tile loading.
    """
    try:
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        
        dpi = 100
        fig, ax = plt.subplots(figsize=(width/dpi, height/dpi), dpi=dpi)
        
        # Plot route line
        ax.plot(lons, lats, color='#0d6efd', linewidth=3, solid_capstyle='round')
        
        # Start marker
        ax.plot(lons[0], lats[0], 'o', color='#28a745', markersize=10, 
               markeredgecolor='white', markeredgewidth=2, zorder=5)
        
        # End marker
        ax.plot(lons[-1], lats[-1], 'o', color='#dc3545', markersize=10,
               markeredgecolor='white', markeredgewidth=2, zorder=5)
        
        # Style
        ax.set_aspect('equal', adjustable='box')
        ax.axis('off')
        plt.tight_layout(pad=0)
        fig.patch.set_facecolor('#e3f2fd')
        
        # Save to bytes
        img_bytes = BytesIO()
        plt.savefig(img_bytes, format='png', bbox_inches='tight', 
                   pad_inches=0, facecolor='#e3f2fd', dpi=dpi)
        plt.close(fig)
        
        img_bytes.seek(0)
        return ContentFile(img_bytes.read(), name='route_preview.png')
        
    except Exception as e:
        print(f"Thumbnail generation error: {e}")
        return None


def generate_interactive_map_html(points, width=800, height=400):
    """
    Generate a full interactive HTML map for detail view using folium.
    This provides zoom, pan, and exploration capabilities.
    """
    if not points:
        return None
    
    try:
        # Create map
        center_lat = sum(p[0] for p in points) / len(points)
        center_lon = sum(p[1] for p in points) / len(points)
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            width=width,
            height=height,
            tiles='OpenStreetMap'
        )
        
        # Add route line
        folium.PolyLine(
            points,
            color='#0d6efd',
            weight=4,
            opacity=0.8,
            popup='Route Path'
        ).add_to(m)
        
        # Add start marker
        folium.CircleMarker(
            points[0],
            radius=10,
            color='green',
            fill=True,
            fillColor='lightgreen',
            fillOpacity=0.9,
            popup='<b>Start Point</b>',
            tooltip='Start'
        ).add_to(m)
        
        # Add end marker
        folium.CircleMarker(
            points[-1],
            radius=10,
            color='red',
            fill=True,
            fillColor='lightcoral',
            fillOpacity=0.9,
            popup='<b>End Point</b>',
            tooltip='End'
        ).add_to(m)
        
        # Save HTML to bytes
        html_bytes = BytesIO()
        m.save(html_bytes, close_file=False)
        html_bytes.seek(0)
        
        return ContentFile(html_bytes.read(), name='map.html')
        
    except Exception as e:
        print(f"Interactive map generation error: {e}")
        return None
