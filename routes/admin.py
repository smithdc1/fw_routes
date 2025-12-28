from django import forms
from django.contrib import admin

from .models import Route, StartPoint, Tag


class StartPointAdminForm(forms.ModelForm):
    class Meta:
        model = StartPoint
        fields = "__all__"
        widgets = {
            "latitude": forms.NumberInput(attrs={"id": "id_latitude"}),
            "longitude": forms.NumberInput(attrs={"id": "id_longitude"}),
        }


@admin.register(StartPoint)
class StartPointAdmin(admin.ModelAdmin):
    form = StartPointAdminForm
    list_display = ("name", "latitude", "longitude", "created_at")
    search_fields = ("name", "description")
    list_filter = ("created_at",)
    ordering = ("name",)

    fieldsets = (
        ("Location Information", {"fields": ("name", "latitude", "longitude")}),
        ("Additional Details", {"fields": ("description",), "classes": ("collapse",)}),
    )

    class Media:
        css = {"all": ("routes/vendor/leaflet/leaflet.css",)}
        js = (
            "routes/vendor/leaflet/leaflet.js",
            "admin/js/map_widget.js",
        )

    def render_change_form(self, request, context, *args, **kwargs):
        context["adminform"].form.fields[
            "latitude"
        ].help_text = '<div id="map" style="height: 400px; margin-top: 10px;"></div>'
        return super().render_change_form(request, context, *args, **kwargs)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]
    search_fields = ["name"]


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ["name", "distance_km", "start_location", "uploaded_at"]
    list_filter = ["tags", "uploaded_at"]
    search_fields = ["name", "start_location"]
    readonly_fields = ["share_token", "uploaded_at"]
    filter_horizontal = ["tags"]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "tags")}),
        (
            "GPS Data",
            {
                "fields": (
                    "gpx_file",
                    "thumbnail_image",
                    "distance_km",
                    "elevation_gain",
                )
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "start_location",
                    "start_lat",
                    "start_lon",
                )
            },
        ),
        ("Metadata", {"fields": ("share_token", "uploaded_at")}),
    )
