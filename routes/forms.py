import defusedxml.ElementTree as ET
from django import forms
from django.core.exceptions import ValidationError
from django_tomselect.app_settings import TomSelectConfig
from django_tomselect.forms import TomSelectModelMultipleChoiceField

from .models import Route, Tag


def validate_gpx_file(file):
    """
    Validate GPX file upload for security and format.

    Protects against:
    - XXE (XML External Entity) attacks using defusedxml
    - Oversized files (DoS protection)
    - Invalid file extensions
    - Malformed XML
    """
    # Check file size (10MB max)
    max_size = 10 * 1024 * 1024  # 10MB in bytes
    if file.size > max_size:
        raise ValidationError(
            f"File size exceeds 10MB limit (file is {file.size / 1024 / 1024:.1f}MB)"
        )

    # Check file extension
    if not file.name.lower().endswith(".gpx"):
        raise ValidationError("File must have a .gpx extension")

    # Validate XML structure using defusedxml (protects against XXE attacks)
    try:
        file.seek(0)
        ET.parse(file)
        file.seek(0)  # Reset for later processing
    except ET.ParseError as e:
        raise ValidationError(f"Invalid GPX file: XML parsing error - {str(e)}")
    except Exception as e:
        raise ValidationError(f"Invalid GPX file: {str(e)}")

    return file


class TagCreationField(TomSelectModelMultipleChoiceField):
    """Custom field that handles both existing tags and new tag creation"""

    def _check_values(self, value):
        """Override validation to handle new tag creation"""
        if not value:
            return []

        # Get existing tags from queryset
        key = self.to_field_name or "pk"

        # Separate existing IDs from new tag names
        existing_ids = []
        new_names = []

        for item in value:
            try:
                # Try to parse as ID
                item_id = int(item)
                existing_ids.append(item_id)
            except (ValueError, TypeError):
                # It's a new tag name
                new_names.append(item)

        # Get existing tags
        result = list(self.queryset.filter(**{f"{key}__in": existing_ids}))

        # Create new tags
        for name in new_names:
            tag, created = Tag.objects.get_or_create(name=Tag.normalize_name(name))
            result.append(tag)

        return result


class RouteUploadForm(forms.ModelForm):
    gpx_file = forms.FileField(
        label="GPX File",
        help_text="Upload a .gpx file (max 10MB)",
        widget=forms.FileInput(attrs={"class": "form-control", "accept": ".gpx"}),
        validators=[validate_gpx_file],
    )
    tags_input = forms.CharField(
        required=False,
        label="Tags (comma-separated)",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "hiking, mountains, california",
            }
        ),
    )

    class Meta:
        model = Route
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Route name (optional)"}
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].required = False


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = []
            for d in data:
                cleaned = single_file_clean(d, initial)
                # Validate each file with our GPX validator
                validate_gpx_file(cleaned)
                result.append(cleaned)
        else:
            result = [single_file_clean(data, initial)]
            validate_gpx_file(result[0])
        return result


class BulkUploadForm(forms.Form):
    gpx_files = MultipleFileField(
        label="Select GPX files",
        help_text="You can select multiple files",
        widget=MultipleFileInput(attrs={"class": "form-control", "accept": ".gpx"}),
    )
    default_tags = forms.CharField(
        required=False,
        label="Default tags for all uploads (comma-separated)",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "hiking, 2024"}
        ),
    )


class TagForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize the field at runtime to avoid circular import
        self.fields["tags"] = TagCreationField(
            required=False,
            config=TomSelectConfig(
                url="tag-autocomplete",
                value_field="id",
                label_field="name",
                create=True,
                placeholder="Start typing to add tags...",
                max_items=None,
            ),
            label="Tags",
            help_text="Select existing tags or type to create new ones",
        )
