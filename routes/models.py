import hashlib
from datetime import datetime

from django.db import models
from django.urls import reverse


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @classmethod
    def normalize_name(cls, name):
        """
        Normalize tag name to titlecase with whitespace cleanup.

        This is the single source of truth for tag name normalization.
        Use this method whenever processing tag names to ensure consistency.

        Args:
            name: Raw tag name string

        Returns:
            Normalized tag name (titlecase, single spaces, trimmed)

        Example:
            >>> Tag.normalize_name("  hiking   trail  ")
            "Hiking Trail"
        """
        import re

        if not name:
            return ""
        # Normalize whitespace (collapse multiple spaces) and apply titlecase
        return re.sub(r"\s+", " ", name.strip()).title()

    def save(self, *args, **kwargs):
        """Normalize tag names to titlecase to prevent duplicates"""
        if self.name:
            self.name = self.normalize_name(self.name)
        super().save(*args, **kwargs)


class StartPoint(models.Model):
    name = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Start Point"
        verbose_name_plural = "Start Points"

    def __str__(self):
        return f"{self.name} ({self.latitude}, {self.longitude})"


class Route(models.Model):
    name = models.CharField(max_length=200)
    gpx_file = models.FileField(upload_to="gpx/")  # Original GPX file
    thumbnail_image = models.ImageField(
        upload_to="thumbnails/", blank=True
    )  # Static PNG for list view
    route_coordinates = models.JSONField(
        default=list, blank=True
    )  # Store [[lat, lon], ...] for map rendering
    distance_km = models.FloatField(default=0)
    start_location = models.CharField(max_length=300, blank=True)
    start_lat = models.FloatField(null=True, blank=True)
    start_lon = models.FloatField(null=True, blank=True)
    elevation_gain = models.FloatField(default=0)
    tags = models.ManyToManyField(Tag, blank=True, related_name="routes")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    share_token = models.CharField(max_length=32, unique=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.share_token:
            self.share_token = hashlib.md5(
                f"{self.name}{datetime.now()}".encode()
            ).hexdigest()[:16]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("route_detail", kwargs={"pk": self.pk})

    def get_share_url(self):
        return reverse("route_share", kwargs={"token": self.share_token})

    @property
    def distance_miles(self):
        return self.distance_km * 0.621371

    @property
    def estimated_time(self):
        """Calculate estimated ride time at 12mph average pace"""
        if self.distance_miles == 0:
            return "N/A"

        hours = self.distance_miles / 12.0
        total_minutes = int(hours * 60)

        if total_minutes < 60:
            return f"{total_minutes}m"
        else:
            h = total_minutes // 60
            m = total_minutes % 60
            if m == 0:
                return f"{h}h"
            return f"{h}h {m}m"

    @property
    def gpx_file_url(self):
        """Get the URL for the GPX file"""
        return self.gpx_file.url if self.gpx_file else ""

    @property
    def thumbnail_url(self):
        """Get the URL for the thumbnail image"""
        return self.thumbnail_image.url if self.thumbnail_image else ""
