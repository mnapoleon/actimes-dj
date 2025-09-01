import hashlib
import json

from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html

from .models import Session


class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget that supports multiple file uploads"""
    
    allow_multiple_selected = True
    
    def __init__(self, attrs=None):
        super().__init__(attrs)
        if attrs is None:
            attrs = {}
        attrs['multiple'] = True
        self.attrs.update(attrs)
        
    def value_from_datadict(self, data, files, name):
        """Return a list of files for multiple file upload"""
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        else:
            file_data = files.get(name)
            if isinstance(file_data, list):
                return file_data
            elif file_data:
                return [file_data]
            else:
                return []


class MultipleFileField(forms.FileField):
    """Custom field that handles multiple file uploads"""
    
    widget = MultipleFileInput
    
    def to_python(self, data):
        """Convert the uploaded data to a list of files"""
        if data in self.empty_values:
            return []
        elif not isinstance(data, list):
            data = [data]
            
        files = []
        for item in data:
            if item in self.empty_values:
                continue
            # Call parent's to_python for each file
            files.append(super().to_python(item))
        
        return files
        
    def validate(self, value):
        """Validate the list of files"""
        if not value and self.required:
            raise ValidationError(self.error_messages['required'], code='required')
        
        for file_obj in value:
            super().validate(file_obj)


class SessionEditForm(forms.ModelForm):
    """Form for editing session information"""

    track_select = forms.ChoiceField(
        label="Track (choose or enter new)",
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    track_text = forms.CharField(
        label="Or enter a new track",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Custom track name"}
        ),
    )
    track = forms.CharField(required=False, widget=forms.HiddenInput())

    car_select = forms.ChoiceField(
        label="Car (choose or enter new)",
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    car_text = forms.CharField(
        label="Or enter a new car",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Custom car name"}
        ),
    )
    car = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Session
        fields = ["session_name", "track", "car", "upload_date"]
        widgets = {
            "session_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter a custom session name (optional)",
                }
            ),
            "car": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Car model"}
            ),
            "upload_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
        }
        labels = {
            "session_name": "Session Name",
            "track": "Track",
            "car": "Car",
            "upload_date": "Upload Date",
        }
        help_texts = {
            "session_name": "Optional custom name for this session",
            "track": "The track where this session took place",
            "car": "The car model used in this session",
            "upload_date": "Date and time the session was uploaded",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate dropdown with all distinct track names
        tracks = (
            Session.objects.values_list("track", flat=True).distinct().order_by("track")
        )
        self.fields["track_select"].choices = [("", "— Select a track —")] + [
            (t, t) for t in tracks if t
        ]
        # Populate dropdown with all distinct car names
        cars = Session.objects.values_list("car", flat=True).distinct().order_by("car")
        self.fields["car_select"].choices = [("", "— Select a car —")] + [
            (c, c) for c in cars if c
        ]
        # Set initial values for the fields
        if self.instance:
            if self.instance.track:
                self.fields["track_select"].initial = self.instance.track
                self.fields["track_text"].initial = ""
                self.fields["track"].initial = self.instance.track
            if self.instance.car:
                self.fields["car_select"].initial = self.instance.car
                self.fields["car_text"].initial = ""
                self.fields["car"].initial = self.instance.car
            if self.instance.upload_date:
                # Format for datetime-local input
                self.fields["upload_date"].initial = self.instance.upload_date.strftime(
                    "%Y-%m-%dT%H:%M"
                )

    def clean(self):
        cleaned_data = super().clean()
        # Track logic
        track_select = cleaned_data.get("track_select")
        track_text = cleaned_data.get("track_text")
        if track_text:
            cleaned_data["track"] = track_text
        elif track_select:
            cleaned_data["track"] = track_select
        else:
            self.add_error("track_select", "Please select or enter a track name.")
        self.fields["track"].initial = cleaned_data.get("track", "")

        # Car logic
        car_select = cleaned_data.get("car_select")
        car_text = cleaned_data.get("car_text")
        if car_text:
            cleaned_data["car"] = car_text
        elif car_select:
            cleaned_data["car"] = car_select
        else:
            self.add_error("car_select", "Please select or enter a car name.")
        self.fields["car"].initial = cleaned_data.get("car", "")

        return cleaned_data

    def save(self, commit=True):
        # Ensure the correct track and car values are set on the instance
        self.instance.track = self.cleaned_data.get("track", self.instance.track)
        self.instance.car = self.cleaned_data.get("car", self.instance.car)
        return super().save(commit=commit)


class JSONUploadForm(forms.Form):
    """Form for uploading JSON race data files or directories"""

    json_files = MultipleFileField(
        label="Race Data Files",
        help_text="Upload JSON files containing race session data (supports multiple files or directories)",
        widget=MultipleFileInput(attrs={
            "class": "form-control", 
            "accept": ".json",
            "webkitdirectory": False,  # Will be toggled via JavaScript
        }),
        required=False,
    )
    
    upload_type = forms.ChoiceField(
        choices=[
            ('files', 'Upload Files'),
            ('directory', 'Upload Directory')
        ],
        initial='files',
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        help_text="Choose whether to upload individual files or an entire directory"
    )

    def clean_json_files(self):
        """Validate uploaded files are valid JSON with expected structure"""
        files = self.cleaned_data.get('json_files', [])
        
        if not files:
            raise ValidationError("Please select at least one file to upload")

        validated_files = []
        errors = []

        for file in files:
            try:
                # Check file extension
                if not file.name.endswith(".json"):
                    errors.append(f"{file.name}: File must have .json extension")
                    continue

                # Read and parse JSON content
                file.seek(0)  # Reset file pointer
                content = file.read().decode("utf-8")
                data = json.loads(content)

                # Validate basic structure
                required_fields = ["track", "players", "sessions"]
                for field in required_fields:
                    if field not in data:
                        errors.append(f"{file.name}: Missing required field '{field}'")
                        break
                else:
                    # Validate that players is a list
                    if not isinstance(data["players"], list):
                        errors.append(f"{file.name}: Players data must be a list")
                        continue

                    # Validate that sessions is a list and has at least one session
                    if not isinstance(data["sessions"], list) or len(data["sessions"]) == 0:
                        errors.append(f"{file.name}: Sessions data must be a list with at least one session")
                        continue

                    # Validate that the first session has laps
                    if "laps" not in data["sessions"][0]:
                        errors.append(f"{file.name}: Session data missing laps field")
                        continue

                    if not isinstance(data["sessions"][0]["laps"], list):
                        errors.append(f"{file.name}: Session laps data must be a list")
                        continue

                    # Generate file hash for duplicate detection
                    file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

                    # Check for duplicate hash
                    if Session.objects.filter(file_hash=file_hash).exists():
                        existing_session = Session.objects.get(file_hash=file_hash)
                        session_url = reverse(
                            "session_detail", kwargs={"pk": existing_session.pk}
                        )

                        error_message = format_html(
                            "{}: Already uploaded. "
                            'Existing session: <a href="{}" target="_blank">"{}"</a> '
                            "(uploaded on {})",
                            file.name,
                            session_url,
                            existing_session,
                            existing_session.upload_date.strftime("%Y-%m-%d at %H:%M"),
                        )
                        errors.append(error_message)
                        continue

                    # Store hash for later use in the view
                    file._file_hash = file_hash

                    # Reset file pointer for later use
                    file.seek(0)
                    validated_files.append(file)

            except json.JSONDecodeError:
                errors.append(f"{file.name}: Invalid JSON file format")
            except UnicodeDecodeError:
                errors.append(f"{file.name}: File encoding not supported")
            except Exception as e:
                errors.append(f"{file.name}: Error processing file - {str(e)}")

        if errors:
            raise ValidationError(errors)

        if not validated_files:
            raise ValidationError("No valid JSON files found")

        return validated_files

    def clean(self):
        """Additional form validation"""
        cleaned_data = super().clean()
        upload_type = cleaned_data.get("upload_type")
        
        # Check if files are provided (the custom field handles this, but double-check)
        json_files = cleaned_data.get('json_files', [])
        if not json_files:
            raise ValidationError("Please select files to upload")
            
        return cleaned_data
