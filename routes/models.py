from django.db import models
from django.urls import reverse
import hashlib
from datetime import datetime


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Route(models.Model):
    name = models.CharField(max_length=200)
    gpx_file = models.FileField(upload_to='gpx/')  # Original GPX file
    thumbnail_image = models.ImageField(upload_to='thumbnails/', blank=True)  # Static PNG for list view
    map_html = models.FileField(upload_to='maps/', blank=True)  # Interactive HTML map for detail view
    distance_km = models.FloatField(default=0)
    start_location = models.CharField(max_length=300, blank=True)
    start_lat = models.FloatField(null=True, blank=True)
    start_lon = models.FloatField(null=True, blank=True)
    end_lat = models.FloatField(null=True, blank=True)
    end_lon = models.FloatField(null=True, blank=True)
    elevation_gain = models.FloatField(default=0)
    tags = models.ManyToManyField(Tag, blank=True, related_name='routes')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    share_token = models.CharField(max_length=32, unique=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.share_token:
            self.share_token = hashlib.md5(
                f"{self.name}{datetime.now()}".encode()
            ).hexdigest()[:16]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('route_detail', kwargs={'pk': self.pk})

    def get_share_url(self):
        return reverse('route_share', kwargs={'token': self.share_token})

    @property
    def distance_miles(self):
        return self.distance_km * 0.621371
    
    @property
    def gpx_file_url(self):
        """Get the URL for the GPX file"""
        return self.gpx_file.url if self.gpx_file else ''
    
    @property
    def thumbnail_url(self):
        """Get the URL for the thumbnail image"""
        return self.thumbnail_image.url if self.thumbnail_image else ''
    
    @property
    def map_url(self):
        """Get the URL for the interactive map"""
        return self.map_html.url if self.map_html else ''
