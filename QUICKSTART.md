# GPX Routes Manager - Quick Start Guide

A Django web application for managing GPS routes (GPX files) with mobile-first design, static map thumbnails, and Backblaze B2 cloud storage.

## Features

- 📱 Mobile-first responsive design (Bootstrap 5)
- 🗺️ Static PNG thumbnails for list view (fast scrolling)
- 🔍 Interactive maps for detail view (zoom/pan)
- ☁️ Cloud storage via Backblaze B2 (S3-compatible)
- 🔖 Tag-based organization
- 🔗 Public sharing via unique links
- 📤 Single and bulk upload support
- 🔒 Simple shared authentication

## Installation

### 1. Install Dependencies

```bash
pip install -e .
```

If you want high-quality thumbnails with basemap (optional):
```bash
playwright install chromium
```

Without Playwright, thumbnails will be simple route lines (no map background).

### 2. Configure Backblaze B2

Get your credentials from Backblaze B2:
- Application Key ID
- Application Key
- Bucket Name
- Region (e.g., us-west-000)

**Option A: Environment Variables (recommended)**

```bash
export B2_KEY_ID="your-application-key-id"
export B2_APPLICATION_KEY="your-application-key"
export B2_BUCKET_NAME="your-bucket-name"
export B2_REGION="us-west-000"
```

**Option B: Edit settings.py**

Edit `gpx_routes/settings.py`:

```python
AWS_ACCESS_KEY_ID = 'your-application-key-id'
AWS_SECRET_ACCESS_KEY = 'your-application-key'
AWS_STORAGE_BUCKET_NAME = 'your-bucket-name'
AWS_S3_REGION_NAME = 'us-west-000'
```

### 3. Set Up Database

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Admin User

```bash
python manage.py createsuperuser
```

Enter username and password. Share these credentials with family/friends.

### 5. Run Server

```bash
python manage.py runserver 0.0.0.0:8000
```

Visit: http://localhost:8000

## Usage

### Logging In

1. Navigate to http://localhost:8000/login/
2. Enter the shared username/password
3. Session lasts 30 days (no repeated logins)

### Uploading Routes

**Single Upload:**
1. Click "Upload" in navigation
2. Select a .gpx file
3. Optionally add name and tags
4. Click "Upload Route"

**Bulk Upload:**
1. Click "Bulk Upload"
2. Select multiple .gpx files
3. Add default tags (applied to all)
4. Click "Upload All Routes"

### Managing Tags

On the detail page:
- Click × on any tag to remove it
- Type new tags (comma-separated) and click "Add Tags"
- Tags are created automatically if they don't exist

### Sharing Routes

1. Open route detail page
2. Scroll to "Share This Route"
3. Click "Copy" to copy the link
4. Anyone with the link can view (no login required)

## Project Structure

```
gpx_routes_project/
├── gpx_routes/              # Django project settings
│   ├── settings.py          # Configuration (B2, session, etc.)
│   ├── urls.py              # URL routing
│   └── wsgi.py
├── routes/                  # Main app
│   ├── models.py            # Route and Tag models
│   ├── views.py             # View functions
│   ├── forms.py             # Upload forms
│   ├── utils.py             # GPX parsing, map generation
│   ├── urls.py              # App URLs
│   ├── admin.py             # Admin interface
│   ├── templates/           # HTML templates
│   │   ├── routes/
│   │   │   ├── base.html
│   │   │   ├── route_list.html
│   │   │   ├── route_detail.html
│   │   │   ├── route_upload.html
│   │   │   └── bulk_upload.html
│   │   └── registration/
│   │       └── login.html
│   └── migrations/
├── manage.py
├── pyproject.toml
└── README.md
```

## How It Works

### Upload Flow

1. **User uploads GPX** → Django receives file
2. **Parse GPX** → Extract GPS points, distance, elevation
3. **Generate maps:**
   - Static thumbnail PNG (list view) - uses Playwright or matplotlib
   - Interactive HTML map (detail view) - uses folium
4. **Upload to B2** → django-storages handles this automatically
5. **Geocode location** → OpenStreetMap Nominatim API
6. **Save to database** → Route record created
7. **Redirect to detail** → User sees their route

### Map Generation

**List View Thumbnails:**
- If Playwright available: Renders folium map to PNG with basemap
- Otherwise: Uses matplotlib to draw simple route line
- Result: Static PNG image (~150-250 KB or ~50 KB)

**Detail View:**
- Folium generates interactive HTML map
- Embeds OpenStreetMap tiles
- Saved as .html file in B2
- Displayed in iframe on detail page

## File Storage (Backblaze B2)

Files are organized in your B2 bucket:

```
your-bucket-name/
├── gpx/                    # Original GPX files
│   └── abc123.gpx
├── thumbnails/             # Static PNG thumbnails
│   └── def456.png
└── maps/                   # Interactive HTML maps
    └── ghi789.html
```

All files are public-read by default (required for sharing).

## Customization

### Change Session Duration

Edit `gpx_routes/settings.py`:

```python
SESSION_COOKIE_AGE = 2592000  # 30 days in seconds
```

### Change Map Colors

Edit `routes/utils.py`:

```python
# Route line color
folium.PolyLine(points, color='#0d6efd', ...)  # Change #0d6efd

# Start marker color
fillColor='#28a745'  # Green

# End marker color
fillColor='#dc3545'  # Red
```

### Change UI Colors

Edit `routes/templates/routes/base.html` in the `<style>` section:

```css
:root {
    --primary-color: #0d6efd;  /* Main blue color */
}
```

## Admin Interface

Access Django admin at: http://localhost:8000/admin/

Login with your superuser credentials.

You can:
- View all routes and tags
- Edit route details
- Delete routes
- Manage tags
- View file URLs

## Deployment

### For Production:

1. **Change SECRET_KEY** in settings.py
2. **Set DEBUG = False**
3. **Configure ALLOWED_HOSTS**
4. **Use PostgreSQL** instead of SQLite
5. **Enable HTTPS**
6. **Use a production server** (Gunicorn + Nginx)

### Docker (Optional)

```dockerfile
FROM python:3.12

RUN apt-get update && apt-get install -y \
    libnss3 libatk1.0-0 libatk-bridge2.0-0

COPY pyproject.toml .
RUN pip install .
RUN playwright install chromium

COPY . /app
WORKDIR /app

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## Troubleshooting

### Thumbnails have no basemap

This means Playwright isn't installed or tiles didn't load. The app falls back to simple matplotlib thumbnails.

**Solutions:**
- Install Playwright: `playwright install chromium`
- Check network connectivity to tile.openstreetmap.org
- This is fine for low volume - thumbnails still work, just without background

### Files not uploading to B2

- Check your B2 credentials in settings.py
- Ensure bucket exists and is public
- Verify region matches your bucket location

### Geocoding not working

The app uses OpenStreetMap Nominatim (free, no API key). If it's down:
- Coordinates will be shown instead of location names
- This doesn't affect core functionality

### Can't log in

- Make sure you created a superuser: `python manage.py createsuperuser`
- Check username/password
- Sessions are stored in database - try running migrations again

## Cost Estimate

For 100 routes uploaded:

**Storage:**
- GPX files: 100 × 50 KB = 5 MB
- Thumbnails: 100 × 150 KB = 15 MB
- Maps: 100 × 250 KB = 25 MB
- **Total: ~45 MB**

**Backblaze B2 Pricing:**
- Storage: $0.005/GB/month = $0.0002/month
- Download: First 3× storage free, then $0.01/GB
- **Cost: ~$0.02/month for 100 routes**

Essentially free for personal use!

## Technologies

- **Backend:** Django 6.0, Python 3.12
- **Frontend:** Bootstrap 5, Bootstrap Icons
- **Maps:** Folium (Leaflet.js), matplotlib
- **Storage:** Backblaze B2 (S3-compatible)
- **GPX:** gpxpy library
- **Rendering:** Playwright (headless Chrome) - optional
- **Geocoding:** OpenStreetMap Nominatim

## Support

For issues or questions:
1. Check this README
2. Review code comments in `routes/utils.py` and `routes/views.py`
3. Check Django logs for errors

## License

Open source - modify as needed for your use case.
