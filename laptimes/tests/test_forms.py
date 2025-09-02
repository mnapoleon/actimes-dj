"""Tests for the laptimes forms."""

import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from ..forms import JSONUploadForm, SessionEditForm
from .base import BaseTestCase, FormTestMixin


class JSONUploadFormTests(BaseTestCase, FormTestMixin):
    """Test cases for the JSON upload form"""

    def create_test_json_file(self, data=None):
        """Helper to create a test JSON file"""
        if data is None:
            data = {
                "track": "Test Track",
                "players": [{"name": "Test Driver", "car": "Test Car"}],
                "sessions": [
                    {
                        "laps": [
                            {
                                "lap": 1,
                                "car": 0,
                                "time": 90567,
                                "sectors": [30123, 30234, 30210],
                                "tyre": "M",
                                "cuts": 0,
                            }
                        ]
                    }
                ],
            }
        return SimpleUploadedFile(
            "test.json",
            json.dumps(data).encode("utf-8"),
            content_type="application/json",
        )

    def test_valid_json_upload(self):
        """Test valid JSON file upload"""
        json_file = self.create_test_json_file()
        form = JSONUploadForm(
            data={"upload_type": "files"}, files={"json_files": [json_file]}
        )
        self.assertFormValid(form)

    def test_invalid_file_extension(self):
        """Test rejection of non-JSON files"""
        txt_file = SimpleUploadedFile(
            "test.txt", b"not json content", content_type="text/plain"
        )
        form = JSONUploadForm(
            data={"upload_type": "files"}, files={"json_files": [txt_file]}
        )
        self.assertFormInvalid(
            form, {"json_files": ["test.txt: File must have .json extension"]}
        )

    def test_invalid_json_content(self):
        """Test rejection of invalid JSON content"""
        invalid_file = SimpleUploadedFile(
            "test.json", b"invalid json content", content_type="application/json"
        )
        form = JSONUploadForm(
            data={"upload_type": "files"}, files={"json_files": [invalid_file]}
        )
        self.assertFormInvalid(
            form, {"json_files": ["test.json: Invalid JSON file format"]}
        )

    def test_missing_required_fields(self):
        """Test rejection of JSON missing required fields"""
        incomplete_data = {"track": "Test Track"}
        json_file = self.create_test_json_file(incomplete_data)
        form = JSONUploadForm(
            data={"upload_type": "files"}, files={"json_files": [json_file]}
        )
        self.assertFormInvalid(form)

    def test_invalid_players_structure(self):
        """Test rejection of invalid players structure"""
        invalid_data = {
            "track": "Test Track",
            "players": "not a list",
            "sessions": [{"laps": []}],
        }
        json_file = self.create_test_json_file(invalid_data)
        form = JSONUploadForm(
            data={"upload_type": "files"}, files={"json_files": [json_file]}
        )
        self.assertFormInvalid(form)

    def test_empty_sessions(self):
        """Test rejection of empty sessions"""
        invalid_data = {
            "track": "Test Track",
            "players": [{"name": "Test"}],
            "sessions": [],
        }
        json_file = self.create_test_json_file(invalid_data)
        form = JSONUploadForm(
            data={"upload_type": "files"}, files={"json_files": [json_file]}
        )
        self.assertFormInvalid(form)


class SessionEditFormTests(BaseTestCase, FormTestMixin):
    """Test cases for the session edit form"""

    def setUp(self):
        super().setUp()
        # Override the default session for this test
        original_track = self.create_test_track(code="original_track", display_name="Original Track")
        original_car = self.create_test_car(code="original_car", display_name="Original Car")
        self.session = self.create_test_session(
            track=original_track,
            car=original_car,
            session_type="Practice",
            file_name="test.json",
        )

    def test_form_initialization(self):
        """Test form initializes with session data"""
        form = SessionEditForm(instance=self.session)
        self.assertEqual(form.fields["track_choice"].initial, self.session.track)
        self.assertEqual(form.fields["car_choice"].initial, self.session.car)

    def test_track_text_input(self):
        """Test using text input for track"""
        form_data = {
            "track_choice": "",
            "track_new_code": "new_track_code",
            "track_new_display": "New Track",
            "car_choice": self.session.car.id,
            "car_new_code": "",
            "car_new_display": "",
            "session_name": "Test Session",
            "upload_date": timezone.now().strftime("%Y-%m-%dT%H:%M"),
        }
        form = SessionEditForm(data=form_data, instance=self.session)
        self.assertFormValid(form)
        self.assertEqual(form.cleaned_data["track"].display_name, "New Track")

    def test_car_text_input(self):
        """Test using text input for car"""
        form_data = {
            "track_choice": self.session.track.id,
            "track_new_code": "",
            "track_new_display": "",
            "car_choice": "",
            "car_new_code": "new_car_code",
            "car_new_display": "New Car",
            "session_name": "Test Session",
            "upload_date": timezone.now().strftime("%Y-%m-%dT%H:%M"),
        }
        form = SessionEditForm(data=form_data, instance=self.session)
        self.assertFormValid(form)
        self.assertEqual(form.cleaned_data["car"].display_name, "New Car")

    def test_missing_track_and_car(self):
        """Test form validation when both track fields are empty"""
        form_data = {
            "track_choice": "",
            "track_new_code": "",
            "track_new_display": "",
            "car_choice": self.session.car.id,
            "car_new_code": "",
            "car_new_display": "",
            "session_name": "Test Session",
            "upload_date": timezone.now().strftime("%Y-%m-%dT%H:%M"),
        }
        form = SessionEditForm(data=form_data, instance=self.session)
        self.assertFormInvalid(
            form, {"__all__": ["Please select an existing track or provide a code for a new track."]}
        )
