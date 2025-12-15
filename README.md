# GPX Routes Manager

A Django web application for managing GPS routes (GPX files) with mobile-first design, Backblaze B2 storage integration, and easy sharing capabilities.

## Features

- 📱 **Mobile-First Design** - Optimized for phones with responsive Bootstrap 5 UI
- 🗺️ **Interactive Maps** - View routes with folium-generated maps
- ☁️ **Cloud Storage** - GPX files and map images stored in Backblaze B2
- 🔖 **Tagging System** - Organize routes with custom tags
- 🔗 **Easy Sharing** - Share routes via unique links (no login required for viewers)
- 📤 **Bulk Upload** - Upload multiple GPX files at once
- 📊 **Route Stats** - Distance, elevation gain, start location
- 🔒 **Simple Authentication** - One shared login for all users
- 🌍 **Geocoding** - Automatic location names from GPS coordinates

## Quick Start

### 1. Install Dependencies

```bash
pip install django gpxpy pillow folium b2sdk --break-system-packages
```

### 2. Configure Backblaze B2

Set these environment variables:

```bash
export B2_APPLICATION_KEY_ID="your-key-id"
export B2_APPLICATION_KEY="your-application-key"
export B2_BUCKET_NAME="your-bucket-name"
```

Or edit `gpx_routes/settings.py` and update the B2 settings directly.

### 3. Set Up Database

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Admin User

```bash
python manage.py createsuperuser
```

Enter a username and password. You can share these credentials with friends/family for site access.

### 5. Run the Server

```bash
python manage.py runserver 0.0.0.0:8000
```

Visit http://localhost:8000

## Usage

### Logging In

- Navigate to `/login/`
- Use the shared username/password
- Session lasts 30 days - no need to log in repeatedly

### Uploading Routes

**Single Upload:**
1. Click "Upload" in the navigation
2. Select a GPX file
3. Optionally add a name and tags
4. Click "Upload Route"

**Bulk Upload:**
1. Click "Bulk Upload" in the navigation
2. Select multiple GPX files
3. Add default tags to apply to all routes
4. Click "Upload All Routes"

### Managing Tags

On the route detail page:
- View all tags assigned to the route
- Add new tags (comma-separated)
- Remove tags by clicking the × button
- Tags are created automatically if they don't exist

### Sharing Routes

Each route has a unique share link:
1. Open the route detail page
2. Scroll to "Share This Route"
3. Click "Copy" to copy the link
4. Share with anyone - they can view without logging in

## File Structure

```
/home/claude/
├── gpx_routes/              # Django project
│   ├── settings.py          # Configuration
│   ├── urls.py              # URL routing
│   └── wsgi.py
├── routes/                  # Main app
│   ├── models.py            # Route and Tag models
│   ├── views.py             # View functions
│   ├── forms.py             # Upload forms
│   ├── utils.py             # GPX parsing, B2 upload, maps
│   ├── urls.py              # App URLs
│   ├── admin.py             # Admin interface
│   └── templates/           # HTML templates
│       └── routes/
│           ├── base.html           # Base template
│           ├── route_list.html     # List view
│           ├── route_detail.html   # Detail view
│           ├── route_upload.html   # Upload form
│           └── bulk_upload.html    # Bulk upload
└── manage.py                # Django management
```

## Models

### Route
- `name`: Route name
- `gpx_file_url`: B2 URL for GPX file
- `map_image_url`: B2 URL for map visualization
- `distance_km`: Route distance in kilometers
- `elevation_gain`: Total elevation gain in meters
- `start_location`: Human-readable start location
- `start_lat`, `start_lon`: Start coordinates
- `end_lat`, `end_lon`: End coordinates
- `tags`: Many-to-many relationship with Tag
- `share_token`: Unique token for sharing
- `uploaded_at`: Upload timestamp

### Tag
- `name`: Tag name (unique)
- `created_at`: Creation timestamp

## Customization

### Change Login Duration

Edit `gpx_routes/settings.py`:

```python
SESSION_COOKIE_AGE = 2592000  # 30 days (in seconds)
```

### Styling

The app uses Bootstrap 5 with custom CSS in `base.html`. Key color variables:

```css
:root {
    --primary-color: #0d6efd;  /* Bootstrap blue */
}
```

### Map Styling

Edit `routes/utils.py` in the `generate_static_map_image()` function to customize:
- Map zoom level
- Route line color and width
- Marker styles

## API Endpoints

- `/` - Route list (requires login)
- `/upload/` - Single upload (requires login)
- `/bulk-upload/` - Bulk upload (requires login)
- `/route/<id>/` - Route detail (requires login)
- `/share/<token>/` - Public share view (no login)
- `/login/` - Login page
- `/logout/` - Logout
- `/admin/` - Django admin

## Security Notes

1. **Shared Authentication**: This app uses a single shared login. All logged-in users have equal access.
2. **Share Links**: Routes shared via token are publicly accessible without authentication.
3. **Production**: Before deploying:
   - Change `SECRET_KEY` in settings.py
   - Set `DEBUG = False`
   - Configure `ALLOWED_HOSTS`
   - Use a production-grade database (PostgreSQL)
   - Enable HTTPS

## Troubleshooting

**Issue**: GPX file won't upload
- Check B2 credentials are correct
- Ensure GPX file is valid
- Check B2 bucket permissions

**Issue**: Maps not displaying
- Check browser console for errors
- Verify B2 URLs are publicly accessible
- Try refreshing the page

**Issue**: Location shows coordinates instead of name
- Geocoding service (Nominatim) may be rate-limited
- Location names are best-effort only

## Technologies

- **Backend**: Django 6.0
- **Frontend**: Bootstrap 5, Bootstrap Icons
- **Maps**: Folium (OpenStreetMap)
- **Storage**: Backblaze B2
- **GPX Parsing**: gpxpy
- **Geocoding**: Nominatim (OpenStreetMap)

## License

Open source - modify as needed for your use case.
