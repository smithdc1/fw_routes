from django import forms
from .models import Route, Tag


class RouteUploadForm(forms.ModelForm):
    gpx_file = forms.FileField(
        label='GPX File',
        help_text='Upload a .gpx file',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.gpx'})
    )
    tags_input = forms.CharField(
        required=False,
        label='Tags (comma-separated)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'hiking, mountains, california'
        })
    )

    class Meta:
        model = Route
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Route name (optional)'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = False


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result


class BulkUploadForm(forms.Form):
    gpx_files = MultipleFileField(
        label='Select GPX files',
        help_text='You can select multiple files',
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': '.gpx'
        })
    )
    default_tags = forms.CharField(
        required=False,
        label='Default tags for all uploads (comma-separated)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'hiking, 2024'
        })
    )


class TagForm(forms.Form):
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Add tags (comma-separated)'
        })
    )
