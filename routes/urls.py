from django.urls import path
from . import views

urlpatterns = [
    path("", views.route_list, name="route_list"),
    path("upload/", views.route_upload, name="route_upload"),
    path("bulk-upload/", views.bulk_upload, name="bulk_upload"),
    path("route/<int:pk>/", views.route_detail, name="route_detail"),
    path("route/<int:pk>/delete/", views.route_delete, name="route_delete"),
    path("share/<str:token>/", views.route_share, name="route_share"),
    path(
        "autocomplete/tags/",
        views.TagAutocompleteView.as_view(),
        name="tag-autocomplete",
    ),
    path("favicon.ico", views.favicon),
]
