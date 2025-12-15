from django.contrib import admin
from .models import Route, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ['name', 'distance_km', 'start_location', 'uploaded_at']
    list_filter = ['tags', 'uploaded_at']
    search_fields = ['name', 'start_location']
    readonly_fields = ['share_token', 'uploaded_at']
    filter_horizontal = ['tags']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'tags')
        }),
        ('GPS Data', {
            'fields': ('gpx_file', 'thumbnail_image', 'map_html', 'distance_km', 'elevation_gain')
        }),
        ('Location', {
            'fields': ('start_location', 'start_lat', 'start_lon', 'end_lat', 'end_lon')
        }),
        ('Metadata', {
            'fields': ('share_token', 'uploaded_at')
        }),
    )
