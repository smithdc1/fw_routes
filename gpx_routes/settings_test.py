"""
Test-specific settings for GPX Routes project.

Use these settings when running tests to:
- Use in-memory database
- Disable external services
- Speed up tests
"""

from .settings import *

# Use in-memory SQLite for speed
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Use immediate backend for django-tasks to run tasks synchronously
TASKS = {
    "default": {
        "BACKEND": "django_tasks.backends.immediate.ImmediateBackend",
    }
}

# Use local file storage for tests (not S3)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Disable password hashing for speed
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable migrations for speed (use --keepdb if needed)
# This can be enabled with pytest-django's --nomigrations flag

# Use a simple secret key for tests
SECRET_KEY = "test-secret-key-not-for-production"

# Disable debug for more realistic tests
DEBUG = False

ALLOWED_HOSTS = ["*"]

# Media root for tests
MEDIA_ROOT = "/tmp/test_media"
