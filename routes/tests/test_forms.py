"""
Tests for routes forms and validators.
"""

from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from routes.forms import (
    BulkUploadForm,
    RouteUploadForm,
    TagCreationField,
    TagForm,
    validate_gpx_file,
)
from routes.models import Tag


def get_fixture_path(filename):
    """Get the full path to a test fixture file."""
    return Path(__file__).parent / "fixtures" / filename


class ValidateGPXFileTest(TestCase):
    """Tests for the validate_gpx_file validator."""

    def test_valid_gpx_file(self):
        """Test that a valid GPX file passes validation."""
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        # Should not raise an exception
        result = validate_gpx_file(gpx_file)
        self.assertEqual(result, gpx_file)

    def test_oversized_file_rejected(self):
        """Test that files over 10MB are rejected."""
        # Create a file larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        large_file = SimpleUploadedFile(
            "large.gpx", large_content, content_type="application/gpx+xml"
        )

        with self.assertRaises(ValidationError) as cm:
            validate_gpx_file(large_file)
        self.assertIn("File size exceeds 10MB", str(cm.exception))

    def test_non_gpx_extension_rejected(self):
        """Test that non-.gpx files are rejected."""
        txt_file = SimpleUploadedFile(
            "test.txt", b"Not a GPX file", content_type="text/plain"
        )

        with self.assertRaises(ValidationError) as cm:
            validate_gpx_file(txt_file)
        self.assertIn("must have a .gpx extension", str(cm.exception))

    def test_malformed_xml_rejected(self):
        """Test that malformed XML is rejected."""
        path = get_fixture_path("invalid.gpx")
        with open(path, "rb") as f:
            invalid_file = SimpleUploadedFile(
                "invalid.gpx", f.read(), content_type="application/gpx+xml"
            )

        with self.assertRaises(ValidationError) as cm:
            validate_gpx_file(invalid_file)
        self.assertIn("Invalid GPX file", str(cm.exception))

    def test_empty_file(self):
        """Test that empty GPX files are rejected."""
        empty_file = SimpleUploadedFile(
            "empty.gpx", b"", content_type="application/gpx+xml"
        )

        with self.assertRaises(ValidationError):
            validate_gpx_file(empty_file)

    def test_generic_exception_handling(self):
        """Test generic exception handling in validate_gpx_file."""
        from unittest.mock import patch

        gpx_file = SimpleUploadedFile(
            "test.gpx", b"<gpx></gpx>", content_type="application/gpx+xml"
        )

        # Mock defusedxml.ElementTree.parse to raise a non-ParseError exception
        with patch("defusedxml.ElementTree.parse") as mock_parse:
            mock_parse.side_effect = IOError("Simulated IO error")
            with self.assertRaises(ValidationError) as cm:
                validate_gpx_file(gpx_file)
            self.assertIn("Simulated IO error", str(cm.exception))


class RouteUploadFormTest(TestCase):
    """Tests for the RouteUploadForm."""

    def test_valid_form_with_all_fields(self):
        """Test form with all fields populated."""
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        form = RouteUploadForm(
            data={"name": "Test Route", "tags_input": "hiking, mountain"},
            files={"gpx_file": gpx_file},
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["name"], "Test Route")
        self.assertEqual(form.cleaned_data["tags_input"], "hiking, mountain")

    def test_valid_form_without_name(self):
        """Test form without optional name field."""
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        form = RouteUploadForm(data={"name": ""}, files={"gpx_file": gpx_file})

        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_form_without_tags(self):
        """Test form without tags."""
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "sample_track.gpx", f.read(), content_type="application/gpx+xml"
            )

        form = RouteUploadForm(
            data={"name": "Test Route", "tags_input": ""},
            files={"gpx_file": gpx_file},
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_gpx_file(self):
        """Test form with invalid GPX file."""
        path = get_fixture_path("invalid.gpx")
        with open(path, "rb") as f:
            invalid_file = SimpleUploadedFile(
                "invalid.gpx", f.read(), content_type="application/gpx+xml"
            )

        form = RouteUploadForm(
            data={"name": "Test Route"}, files={"gpx_file": invalid_file}
        )

        self.assertFalse(form.is_valid())
        self.assertIn("gpx_file", form.errors)

    def test_missing_gpx_file(self):
        """Test form without required GPX file."""
        form = RouteUploadForm(data={"name": "Test Route"})

        self.assertFalse(form.is_valid())
        self.assertIn("gpx_file", form.errors)


class BulkUploadFormTest(TestCase):
    """Tests for the BulkUploadForm."""

    def test_valid_form_with_multiple_files(self):
        """Test form with multiple valid GPX files."""
        path1 = get_fixture_path("sample_track.gpx")
        path2 = get_fixture_path("sample_route.gpx")

        with open(path1, "rb") as f1, open(path2, "rb") as f2:
            file1 = SimpleUploadedFile(
                "track.gpx", f1.read(), content_type="application/gpx+xml"
            )
            file2 = SimpleUploadedFile(
                "route.gpx", f2.read(), content_type="application/gpx+xml"
            )

            form = BulkUploadForm(
                data={"default_tags": "hiking, 2024"},
                files={"gpx_files": [file1, file2]},
            )

            self.assertTrue(form.is_valid(), form.errors)
            self.assertEqual(form.cleaned_data["default_tags"], "hiking, 2024")

    def test_valid_form_without_tags(self):
        """Test bulk upload form without default tags."""
        path = get_fixture_path("sample_track.gpx")
        with open(path, "rb") as f:
            gpx_file = SimpleUploadedFile(
                "track.gpx", f.read(), content_type="application/gpx+xml"
            )

            form = BulkUploadForm(
                data={"default_tags": ""}, files={"gpx_files": [gpx_file]}
            )

            self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_file_in_batch(self):
        """Test that invalid files in batch are caught."""
        path = get_fixture_path("invalid.gpx")
        with open(path, "rb") as f:
            invalid_file = SimpleUploadedFile(
                "invalid.gpx", f.read(), content_type="application/gpx+xml"
            )

            form = BulkUploadForm(
                data={"default_tags": ""}, files={"gpx_files": [invalid_file]}
            )

            self.assertFalse(form.is_valid())


class TagFormTest(TestCase):
    """Tests for the TagForm."""

    def test_form_with_existing_tags(self):
        """Test form with existing tags."""
        tag1 = Tag.objects.create(name="Hiking")
        tag2 = Tag.objects.create(name="Mountain")

        form = TagForm(data={"tags": [tag1.id, tag2.id]})

        self.assertTrue(form.is_valid(), form.errors)
        tags = form.cleaned_data["tags"]
        self.assertEqual(len(tags), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_form_with_new_tag_names(self):
        """Test form creating new tags."""
        form = TagForm(data={"tags": ["New Tag", "Another Tag"]})

        self.assertTrue(form.is_valid(), form.errors)
        tags = form.cleaned_data["tags"]
        self.assertEqual(len(tags), 2)

        # Verify tags were created with normalized names
        self.assertTrue(Tag.objects.filter(name="New Tag").exists())
        self.assertTrue(Tag.objects.filter(name="Another Tag").exists())

    def test_form_with_mixed_existing_and_new(self):
        """Test form with mix of existing tags and new tag names."""
        existing_tag = Tag.objects.create(name="Hiking")

        form = TagForm(data={"tags": [str(existing_tag.id), "New Tag"]})

        self.assertTrue(form.is_valid(), form.errors)
        tags = form.cleaned_data["tags"]
        self.assertEqual(len(tags), 2)
        self.assertIn(existing_tag, tags)

        # New tag should be created
        self.assertTrue(Tag.objects.filter(name="New Tag").exists())

    def test_form_with_empty_tags(self):
        """Test form with no tags selected."""
        form = TagForm(data={"tags": []})

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data["tags"]), 0)

    def test_tag_name_normalization_in_form(self):
        """Test that new tag names are normalized when created through form."""
        form = TagForm(data={"tags": ["  hiking   trail  "]})

        self.assertTrue(form.is_valid(), form.errors)
        tags = form.cleaned_data["tags"]

        # Tag should be normalized
        created_tag = Tag.objects.get(name="Hiking Trail")
        self.assertIn(created_tag, tags)


class TagCreationFieldTest(TestCase):
    """Tests for the TagCreationField."""

    def test_separate_existing_ids_from_new_names(self):
        """Test that field correctly separates existing IDs from new names."""
        tag1 = Tag.objects.create(name="Hiking")
        tag2 = Tag.objects.create(name="Mountain")

        from django_tomselect.app_settings import TomSelectConfig

        field = TagCreationField(
            required=False,
            config=TomSelectConfig(
                url="tag-autocomplete",
                value_field="id",
                label_field="name",
                create=True,
            ),
        )

        # Mix of existing IDs and new names
        values = [str(tag1.id), str(tag2.id), "New Tag"]
        result = field._check_values(values)

        self.assertEqual(len(result), 3)
        self.assertIn(tag1, result)
        self.assertIn(tag2, result)

        # New tag should be created
        new_tag = Tag.objects.get(name="New Tag")
        self.assertIn(new_tag, result)

    def test_empty_value_list(self):
        """Test field with empty value list."""
        from django_tomselect.app_settings import TomSelectConfig

        field = TagCreationField(
            required=False,
            config=TomSelectConfig(
                url="tag-autocomplete",
                value_field="id",
                label_field="name",
                create=True,
            ),
        )

        result = field._check_values([])
        self.assertEqual(result, [])
