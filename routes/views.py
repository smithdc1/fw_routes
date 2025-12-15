from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.core.files.base import ContentFile
from .models import Route, Tag
from .forms import RouteUploadForm, BulkUploadForm, TagForm
from .utils import parse_gpx, get_location_name, generate_static_map_image, generate_interactive_map_html
import hashlib
from datetime import datetime


@login_required
def route_list(request):
    """List all routes with filtering"""
    routes = Route.objects.all().prefetch_related('tags')
    
    # Filter by tag if provided
    tag_filter = request.GET.get('tag')
    if tag_filter:
        routes = routes.filter(tags__name=tag_filter)
    
    # Search
    search = request.GET.get('search')
    if search:
        routes = routes.filter(name__icontains=search)
    
    context = {
        'routes': routes,
        'all_tags': Tag.objects.all(),
        'active_tag': tag_filter,
        'search_query': search
    }
    return render(request, 'routes/route_list.html', context)


@login_required
def route_detail(request, pk):
    """Show detailed route information"""
    route = get_object_or_404(Route, pk=pk)
    
    if request.method == 'POST':
        # Handle tag updates
        action = request.POST.get('action')
        
        if action == 'add_tags':
            tag_names = request.POST.get('tags', '').split(',')
            for tag_name in tag_names:
                tag_name = tag_name.strip()
                if tag_name:
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    route.tags.add(tag)
            messages.success(request, 'Tags added successfully')
            
        elif action == 'remove_tag':
            tag_id = request.POST.get('tag_id')
            if tag_id:
                route.tags.remove(tag_id)
                messages.success(request, 'Tag removed')
        
        return redirect('route_detail', pk=pk)
    
    context = {
        'route': route,
        'tag_form': TagForm(),
        'share_url': request.build_absolute_uri(route.get_share_url())
    }
    return render(request, 'routes/route_detail.html', context)


def route_share(request, token):
    """Public route view accessible via share link (no login required)"""
    route = get_object_or_404(Route, share_token=token)
    context = {
        'route': route,
        'is_shared_view': True
    }
    return render(request, 'routes/route_detail.html', context)


@login_required
def route_upload(request):
    """Upload a single GPX file"""
    if request.method == 'POST':
        form = RouteUploadForm(request.POST, request.FILES)
        if form.is_valid():
            gpx_file = request.FILES['gpx_file']
            
            # Parse GPX
            gpx_data = parse_gpx(gpx_file)
            
            # Get location name
            start_location = ''
            if gpx_data['start_lat'] and gpx_data['start_lon']:
                start_location = get_location_name(
                    gpx_data['start_lat'],
                    gpx_data['start_lon']
                )
            
            # Generate thumbnail image (static PNG for list view)
            thumbnail = generate_static_map_image(gpx_data['points'], width=800, height=200)
            
            # Generate interactive map (HTML for detail view)
            interactive_map = generate_interactive_map_html(gpx_data['points'], width=800, height=500)
            
            # Create route
            route = form.save(commit=False)
            route.name = form.cleaned_data['name'] or gpx_data['name'] or gpx_file.name.replace('.gpx', '')
            route.distance_km = gpx_data['distance_km']
            route.elevation_gain = gpx_data['elevation_gain']
            route.start_lat = gpx_data['start_lat']
            route.start_lon = gpx_data['start_lon']
            route.end_lat = gpx_data['end_lat']
            route.end_lon = gpx_data['end_lon']
            route.start_location = start_location
            
            # Save GPX file
            gpx_file.seek(0)
            route.gpx_file.save(gpx_file.name, gpx_file, save=False)
            
            # Save thumbnail
            if thumbnail:
                thumb_filename = f"{hashlib.md5(f'{datetime.now()}{gpx_file.name}'.encode()).hexdigest()}.png"
                route.thumbnail_image.save(thumb_filename, thumbnail, save=False)
            
            # Save interactive map
            if interactive_map:
                map_filename = f"{hashlib.md5(f'{datetime.now()}{gpx_file.name}_map'.encode()).hexdigest()}.html"
                route.map_html.save(map_filename, interactive_map, save=False)
            
            route.save()
            
            # Add tags
            tags_input = form.cleaned_data.get('tags_input', '')
            if tags_input:
                for tag_name in tags_input.split(','):
                    tag_name = tag_name.strip()
                    if tag_name:
                        tag, _ = Tag.objects.get_or_create(name=tag_name)
                        route.tags.add(tag)
            
            messages.success(request, f'Route "{route.name}" uploaded successfully!')
            return redirect('route_detail', pk=route.pk)
    else:
        form = RouteUploadForm()
    
    return render(request, 'routes/route_upload.html', {'form': form})


@login_required
def bulk_upload(request):
    """Bulk upload multiple GPX files"""
    if request.method == 'POST':
        form = BulkUploadForm(request.POST, request.FILES)
        files = request.FILES.getlist('gpx_files')
        
        if form.is_valid() and files:
            default_tags = form.cleaned_data.get('default_tags', '')
            tag_list = [t.strip() for t in default_tags.split(',') if t.strip()]
            
            uploaded_count = 0
            failed_files = []
            
            for gpx_file in files:
                try:
                    # Parse GPX
                    gpx_data = parse_gpx(gpx_file)
                    
                    # Get location
                    start_location = ''
                    if gpx_data['start_lat'] and gpx_data['start_lon']:
                        start_location = get_location_name(
                            gpx_data['start_lat'],
                            gpx_data['start_lon']
                        )
                    
                    # Generate thumbnail and map
                    thumbnail = generate_static_map_image(gpx_data['points'], width=800, height=200)
                    interactive_map = generate_interactive_map_html(gpx_data['points'], width=800, height=500)
                    
                    # Create route
                    route = Route(
                        name=gpx_data['name'] or gpx_file.name.replace('.gpx', ''),
                        distance_km=gpx_data['distance_km'],
                        elevation_gain=gpx_data['elevation_gain'],
                        start_lat=gpx_data['start_lat'],
                        start_lon=gpx_data['start_lon'],
                        end_lat=gpx_data['end_lat'],
                        end_lon=gpx_data['end_lon'],
                        start_location=start_location
                    )
                    
                    # Save files
                    gpx_file.seek(0)
                    route.gpx_file.save(gpx_file.name, gpx_file, save=False)
                    
                    if thumbnail:
                        thumb_filename = f"{hashlib.md5(f'{datetime.now()}{gpx_file.name}'.encode()).hexdigest()}.png"
                        route.thumbnail_image.save(thumb_filename, thumbnail, save=False)
                    
                    if interactive_map:
                        map_filename = f"{hashlib.md5(f'{datetime.now()}{gpx_file.name}_map'.encode()).hexdigest()}.html"
                        route.map_html.save(map_filename, interactive_map, save=False)
                    
                    route.save()
                    
                    # Add default tags
                    for tag_name in tag_list:
                        tag, _ = Tag.objects.get_or_create(name=tag_name)
                        route.tags.add(tag)
                    
                    uploaded_count += 1
                    
                except Exception as e:
                    failed_files.append(f"{gpx_file.name} ({str(e)})")
            
            if uploaded_count > 0:
                messages.success(request, f'Successfully uploaded {uploaded_count} route(s)')
            
            if failed_files:
                messages.warning(request, f'Failed to upload: {", ".join(failed_files)}')
            
            return redirect('route_list')
    else:
        form = BulkUploadForm()
    
    return render(request, 'routes/bulk_upload.html', {'form': form})


@login_required
@require_http_methods(["DELETE"])
def route_delete(request, pk):
    """Delete a route"""
    route = get_object_or_404(Route, pk=pk)
    route.delete()
    return JsonResponse({'success': True})
