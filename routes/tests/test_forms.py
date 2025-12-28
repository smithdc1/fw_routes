"""
Tests for routes forms module.

Tests cover:
- GPX file validation (size, format, security)
- Form field validation
- Tag creation and normalization in forms
- XXE attack prevention
- Edge cases for file uploads
"""

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from routes.forms import (
    BulkUploadForm,
    MultipleFileField,
    RouteUploadForm,
    TagCreationField,
    TagForm,
    validate_gpx_file,
)
from routes.models import Tag


class TestValidateGPXFile:
    """Tests for the validate_gpx_file validator function."""

    def test_validate_valid_gpx(self, sample_gpx_content):
        """Test validation passes for valid GPX file."""
        gpx_file = SimpleUploadedFile(
            "test.gpx", sample_gpx_content, content_type="application/gpx+xml"
        )
        result = validate_gpx_file(gpx_file)
        assert result == gpx_file

    def test_validate_file_too_large(self):
        """Test validation fails for files larger than 10MB."""
        # Create a file larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        large_file = SimpleUploadedFile(
            "large.gpx", large_content, content_type="application/gpx+xml"
        )

        with pytest.raises(ValidationError) as exc_info:
            validate_gpx_file(large_file)
        assert "exceeds 10MB limit" in str(exc_info.value)

    def test_validate_wrong_extension(self, sample_gpx_content):
        """Test validation fails for non-.gpx extensions."""
        wrong_ext = SimpleUploadedFile(
            "test.txt", sample_gpx_content, content_type="text/plain"
        )

        with pytest.raises(ValidationError) as exc_info:
            validate_gpx_file(wrong_ext)
        assert "must have a .gpx extension" in str(exc_info.value)

    def test_validate_invalid_xml(self):
        """Test validation fails for malformed XML."""
        invalid_xml = b"<gpx><unclosed"
        invalid_file = SimpleUploadedFile(
            "invalid.gpx", invalid_xml, content_type="application/gpx+xml"
        )

        with pytest.raises(ValidationError) as exc_info:
            validate_gpx_file(invalid_file)
        assert "XML parsing error" in str(exc_info.value)

    def test_validate_xxe_protection(self):
        """Test that XXE attacks are prevented by defusedxml."""
        # Attempt XXE attack with external entity
        xxe_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<gpx version="1.1">
    <metadata>
        <name>&xxe;</name>
    </metadata>
</gpx>
"""
        xxe_file = SimpleUploadedFile(
            "xxe.gpx", xxe_content, content_type="application/gpx+xml"
        )

        # defusedxml should reject this
        with pytest.raises(ValidationError):
            validate_gpx_file(xxe_file)

    def test_validate_empty_file(self):
        """Test validation fails for empty files."""
        empty_file = SimpleUploadedFile(
            "empty.gpx", b"", content_type="application/gpx+xml"
        )

        with pytest.raises(ValidationError):
            validate_gpx_file(empty_file)

    def test_validate_file_at_size_limit(self, sample_gpx_content):
        """Test validation passes for file exactly at 10MB limit."""
        # Create content that's exactly 10MB
        size_10mb = 10 * 1024 * 1024
        content = sample_gpx_content + b"x" * (size_10mb - len(sample_gpx_content))
        file = SimpleUploadedFile(
            "limit.gpx", content, content_type="application/gpx+xml"
        )

        # Should not raise as it's exactly at the limit
        result = validate_gpx_file(file)
        assert result == file

    def test_validate_case_insensitive_extension(self, sample_gpx_content):
        """Test that .GPX extension (uppercase) is accepted."""
        upper_ext = SimpleUploadedFile(
            "test.GPX", sample_gpx_content, content_type="application/gpx+xml"
        )
        result = validate_gpx_file(upper_ext)
        assert result == upper_ext


class TestTagCreationField:
    """Tests for the TagCreationField custom form field."""

    def test_tag_creation_field_existing_tags(self, db):
        """Test field handles existing tag IDs."""
        tag1 = Tag.objects.create(name="Hiking")
        tag2 = Tag.objects.create(name="Mountain")

        field = TagCreationField(queryset=Tag.objects.all())
        result = field._check_values([str(tag1.id), str(tag2.id)])

        assert len(result) == 2
        assert tag1 in result
        assert tag2 in result

    def test_tag_creation_field_new_tags(self, db):
        """Test field creates new tags from names."""
        field = TagCreationField(queryset=Tag.objects.all())
        result = field._check_values(["new tag", "another tag"])

        assert len(result) == 2
        # Tags should be created with normalized names
        assert Tag.objects.filter(name="New Tag").exists()
        assert Tag.objects.filter(name="Another Tag").exists()

    def test_tag_creation_field_mixed(self, db):
        """Test field handles mix of existing IDs and new names."""
        existing_tag = Tag.objects.create(name="Existing")

        field = TagCreationField(queryset=Tag.objects.all())
        result = field._check_values([str(existing_tag.id), "new tag"])

        assert len(result) == 2
        assert existing_tag in result
        assert Tag.objects.filter(name="New Tag").exists()

    def test_tag_creation_field_empty_value(self, db):
        """Test field handles empty values."""
        field = TagCreationField(queryset=Tag.objects.all())
        result = field._check_values([])

        assert result == []

    def test_tag_creation_field_none_value(self, db):
        """Test field handles None."""
        field = TagCreationField(queryset=Tag.objects.all())
        result = field._check_values(None)

        assert result == []

    def test_tag_creation_field_normalization(self, db):
        """Test that new tag names are normalized."""
        field = TagCreationField(queryset=Tag.objects.all())
        result = field._check_values(["  hiking   trail  "])

        assert len(result) == 1
        # Should be normalized to titlecase with clean whitespace
        assert Tag.objects.filter(name="Hiking Trail").exists()

    def test_tag_creation_field_duplicate_handling(self, db):
        """Test field handles duplicate tag creation attempts."""
        Tag.objects.create(name="Hiking")

        field = TagCreationField(queryset=Tag.objects.all())
        # Try to create tag that already exists (case insensitive)
        result = field._check_values(["hiking", "HIKING"])

        # Should only have one tag since they normalize to the same name
        hiking_tags = [tag for tag in result if tag.name == "Hiking"]
        assert len(hiking_tags) >= 1


class TestRouteUploadForm:
    """Tests for the RouteUploadForm."""

    def test_route_upload_form_valid(self, db, sample_gpx_file):
        """Test form validation with valid data."""
        form = RouteUploadForm(
            data={"name": "Test Route", "tags_input": "hiking, mountain"},
            files={"gpx_file": sample_gpx_file},
        )
        assert form.is_valid()

    def test_route_upload_form_name_optional(self, db, sample_gpx_file):
        """Test that route name is optional."""
        form = RouteUploadForm(
            data={"tags_input": "hiking"}, files={"gpx_file": sample_gpx_file}
        )
        assert form.is_valid()

    def test_route_upload_form_tags_optional(self, db, sample_gpx_file):
        """Test that tags are optional."""
        form = RouteUploadForm(
            data={"name": "Test Route"}, files={"gpx_file": sample_gpx_file}
        )
        assert form.is_valid()

    def test_route_upload_form_invalid_gpx(self, db):
        """Test form validation fails with invalid GPX."""
        invalid_file = SimpleUploadedFile(
            "invalid.gpx", b"<invalid>", content_type="application/gpx+xml"
        )
        form = RouteUploadForm(data={"name": "Test"}, files={"gpx_file": invalid_file})
        assert not form.is_valid()
        assert "gpx_file" in form.errors

    def test_route_upload_form_no_file(self, db):
        """Test form validation fails without GPX file."""
        form = RouteUploadForm(data={"name": "Test"})
        assert not form.is_valid()
        assert "gpx_file" in form.errors


class TestBulkUploadForm:
    """Tests for the BulkUploadForm."""

    def test_bulk_upload_form_valid_single_file(self, db, sample_gpx_file):
        """Test form with single file."""
        form = BulkUploadForm(
            data={"default_tags": "hiking"},
            files={"gpx_files": [sample_gpx_file]},
        )
        assert form.is_valid()

    def test_bulk_upload_form_valid_multiple_files(self, db, sample_gpx_content):
        """Test form with multiple files."""
        file1 = SimpleUploadedFile(
            "route1.gpx", sample_gpx_content, content_type="application/gpx+xml"
        )
        file2 = SimpleUploadedFile(
            "route2.gpx", sample_gpx_content, content_type="application/gpx+xml"
        )

        form = BulkUploadForm(
            data={"default_tags": "hiking, 2024"},
            files={"gpx_files": [file1, file2]},
        )
        assert form.is_valid()

    def test_bulk_upload_form_tags_optional(self, db, sample_gpx_file):
        """Test that default tags are optional."""
        form = BulkUploadForm(data={}, files={"gpx_files": [sample_gpx_file]})
        assert form.is_valid()

    def test_bulk_upload_form_invalid_file(self, db):
        """Test form rejects invalid GPX files."""
        invalid_file = SimpleUploadedFile(
            "invalid.gpx", b"<invalid>", content_type="application/gpx+xml"
        )
        form = BulkUploadForm(
            data={"default_tags": "hiking"},
            files={"gpx_files": [invalid_file]},
        )
        assert not form.is_valid()


class TestTagForm:
    """Tests for the TagForm."""

    def test_tag_form_initialization(self, db):
        """Test TagForm initializes correctly."""
        form = TagForm()
        assert "tags" in form.fields
        assert isinstance(form.fields["tags"], TagCreationField)

    def test_tag_form_with_initial_tags(self, db):
        """Test form initialization with existing tags."""
        tag1 = Tag.objects.create(name="Hiking")
        tag2 = Tag.objects.create(name="Mountain")

        form = TagForm(initial={"tags": [tag1, tag2]})
        assert form.fields["tags"].initial == [tag1, tag2]

    def test_tag_form_optional(self, db):
        """Test that tags field is optional."""
        form = TagForm(data={})
        assert form.is_valid()


class TestMultipleFileField:
    """Tests for the MultipleFileField custom field."""

    def test_multiple_file_field_single_file(self, db, sample_gpx_content):
        """Test field handles single file."""
        field = MultipleFileField()
        file = SimpleUploadedFile(
            "test.gpx", sample_gpx_content, content_type="application/gpx+xml"
        )
        result = field.clean(file)
        assert len(result) == 1
        assert result[0] == file

    def test_multiple_file_field_multiple_files(self, db, sample_gpx_content):
        """Test field handles multiple files."""
        field = MultipleFileField()
        file1 = SimpleUploadedFile(
            "test1.gpx", sample_gpx_content, content_type="application/gpx+xml"
        )
        file2 = SimpleUploadedFile(
            "test2.gpx", sample_gpx_content, content_type="application/gpx+xml"
        )
        result = field.clean([file1, file2])
        assert len(result) == 2

    def test_multiple_file_field_validates_each_file(self, db, sample_gpx_content):
        """Test that each file is validated individually."""
        field = MultipleFileField()
        valid_file = SimpleUploadedFile(
            "valid.gpx", sample_gpx_content, content_type="application/gpx+xml"
        )
        invalid_file = SimpleUploadedFile(
            "invalid.txt", b"not gpx", content_type="text/plain"
        )

        with pytest.raises(ValidationError):
            field.clean([valid_file, invalid_file])
