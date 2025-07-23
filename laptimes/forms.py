from django import forms
from django.core.exceptions import ValidationError
import json
import hashlib

from .models import Session


class SessionEditForm(forms.ModelForm):
    """Form for editing session information"""
    track_select = forms.ChoiceField(
        label='Track (choose or enter new)',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    track_text = forms.CharField(
        label='Or enter a new track',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Custom track name'
        })
    )
    track = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    car_select = forms.ChoiceField(
        label='Car (choose or enter new)',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    car_text = forms.CharField(
        label='Or enter a new car',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Custom car name'
        })
    )
    car = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    class Meta:
        model = Session
        fields = ['session_name', 'track', 'car', 'upload_date']
        widgets = {
            'session_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a custom session name (optional)'
            }),
            'car': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Car model'
            }),
            'upload_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }, format='%Y-%m-%dT%H:%M'),
        }
        labels = {
            'session_name': 'Session Name',
            'track': 'Track',
            'car': 'Car',
            'upload_date': 'Upload Date',
        }
        help_texts = {
            'session_name': 'Optional custom name for this session',
            'track': 'The track where this session took place',
            'car': 'The car model used in this session',
            'upload_date': 'Date and time the session was uploaded',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate dropdown with all distinct track names
        tracks = Session.objects.values_list(
            'track', flat=True).distinct().order_by('track')
        self.fields['track_select'].choices = (
            [('', '— Select a track —')] +
            [(t, t) for t in tracks if t])
        # Populate dropdown with all distinct car names
        cars = Session.objects.values_list(
            'car', flat=True).distinct().order_by('car')
        self.fields['car_select'].choices = (
            [('', '— Select a car —')] +
            [(c, c) for c in cars if c])
        # Set initial values for the fields
        if self.instance:
            if self.instance.track:
                self.fields['track_select'].initial = self.instance.track
                self.fields['track_text'].initial = ''
                self.fields['track'].initial = self.instance.track
            if self.instance.car:
                self.fields['car_select'].initial = self.instance.car
                self.fields['car_text'].initial = ''
                self.fields['car'].initial = self.instance.car
            if self.instance.upload_date:
                # Format for datetime-local input
                self.fields['upload_date'].initial = (
                    self.instance.upload_date.strftime('%Y-%m-%dT%H:%M'))

    def clean(self):
        cleaned_data = super().clean()
        # Track logic
        track_select = cleaned_data.get('track_select')
        track_text = cleaned_data.get('track_text')
        if track_text:
            cleaned_data['track'] = track_text
        elif track_select:
            cleaned_data['track'] = track_select
        else:
            self.add_error(
                'track_select', 'Please select or enter a track name.')
        self.fields['track'].initial = cleaned_data.get('track', '')

        # Car logic
        car_select = cleaned_data.get('car_select')
        car_text = cleaned_data.get('car_text')
        if car_text:
            cleaned_data['car'] = car_text
        elif car_select:
            cleaned_data['car'] = car_select
        else:
            self.add_error('car_select', 'Please select or enter a car name.')
        self.fields['car'].initial = cleaned_data.get('car', '')

        return cleaned_data

    def save(self, commit=True):
        # Ensure the correct track and car values are set on the instance
        self.instance.track = self.cleaned_data.get(
            'track', self.instance.track)
        self.instance.car = self.cleaned_data.get(
            'car', self.instance.car)
        return super().save(commit=commit)


class JSONUploadForm(forms.Form):
    """Form for uploading JSON race data files"""
    json_file = forms.FileField(
        label='Race Data File',
        help_text='Upload a JSON file containing race session data',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.json'
        })
    )

    def clean_json_file(self):
        """Validate uploaded file is valid JSON with expected structure"""
        file = self.cleaned_data['json_file']

        if not file.name.endswith('.json'):
            raise ValidationError('File must have .json extension')

        try:
            # Read and parse JSON content
            file.seek(0)  # Reset file pointer
            content = file.read().decode('utf-8')
            data = json.loads(content)

            # Validate basic structure
            required_fields = ['track', 'players', 'sessions']
            for field in required_fields:
                if field not in data:
                    raise ValidationError(
                        f'JSON file missing required field: {field}'
                    )

            # Validate that players is a list
            if not isinstance(data['players'], list):
                raise ValidationError('Players data must be a list')

            # Validate that sessions is a list and has at least one session
            if (not isinstance(data['sessions'], list) or
                    len(data['sessions']) == 0):
                raise ValidationError(
                    'Sessions data must be a list with at least one session'
                )

            # Validate that the first session has laps
            if 'laps' not in data['sessions'][0]:
                raise ValidationError('Session data missing laps field')

            if not isinstance(data['sessions'][0]['laps'], list):
                raise ValidationError('Session laps data must be a list')

            # Generate file hash for duplicate detection
            file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Check for duplicate hash
            if Session.objects.filter(file_hash=file_hash).exists():
                existing_session = Session.objects.get(file_hash=file_hash)
                raise ValidationError(
                    f'This file has already been uploaded. '
                    f'Existing session: "{existing_session}" '
                    f'(uploaded on {existing_session.upload_date.strftime("%Y-%m-%d %H:%M")})'
                )
            
            # Store hash for later use in the view
            file._file_hash = file_hash

            # Reset file pointer for later use
            file.seek(0)

        except json.JSONDecodeError:
            raise ValidationError('Invalid JSON file format')
        except UnicodeDecodeError:
            raise ValidationError('File encoding not supported')

        return file


