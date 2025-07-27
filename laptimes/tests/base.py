"""Shared test utilities and base classes for the laptimes test suite."""

import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from ..models import Lap, Session


class BaseTestCase(TestCase):
    """Base test case with common setup and utilities."""

    def setUp(self):
        """Set up common test data."""
        self.session = Session.objects.create(
            session_name="Test Session",
            track="Test Track",
            car="Test Car",
            session_type="Practice",
            file_name="test.json",
            players_data=[{"name": "Test Driver", "car": "Test Car"}],
        )

    def create_test_lap(self, session=None, **kwargs):
        """Helper to create test lap with default values."""
        defaults = {
            "session": session or self.session,
            "lap_number": 1,
            "driver_name": "Test Driver",
            "car_index": 0,
            "total_time": 90.123,
            "sectors": [30.1, 30.2, 29.823],
            "tyre_compound": "M",
            "cuts": 0,
        }
        defaults.update(kwargs)
        return Lap.objects.create(**defaults)

    def create_test_json_file(self, filename="test.json", content=None):
        """Helper to create test JSON file for upload."""
        if content is None:
            content = {
                "track": "Silverstone",
                "car": "Ferrari SF70H",
                "players": [{"name": "Test Driver", "car": "Ferrari SF70H"}],
                "sessions": [
                    {
                        "type": 2,
                        "laps": [
                            {
                                "lap": 1,
                                "car": 0,
                                "time": 90123,
                                "sectors": [30100, 30200, 29823],
                                "tyre": "M",
                                "cuts": 0,
                            }
                        ],
                    }
                ],
            }
        json_content = json.dumps(content).encode("utf-8")
        return SimpleUploadedFile(
            filename, json_content, content_type="application/json"
        )


class ModelTestMixin:
    """Mixin providing model-specific test utilities."""

    def assertSessionEqual(self, session, expected_data):
        """Assert session matches expected data."""
        for field, value in expected_data.items():
            self.assertEqual(getattr(session, field), value)

    def assertLapEqual(self, lap, expected_data):
        """Assert lap matches expected data."""
        for field, value in expected_data.items():
            self.assertEqual(getattr(lap, field), value)


class ViewTestMixin:
    """Mixin providing view-specific test utilities."""

    def assertRedirectsToHome(self, response):
        """Assert response redirects to home page."""
        self.assertRedirects(response, "/")

    def assertContainsMessage(self, response, message_text, level="success"):
        """Assert response contains specific message."""
        messages = list(response.context["messages"])
        message_found = any(
            message_text in str(message) and message.level_tag == level
            for message in messages
        )
        self.assertTrue(message_found, f"Message '{message_text}' not found")


class FormTestMixin:
    """Mixin providing form-specific test utilities."""

    def assertFormValid(self, form):
        """Assert form is valid and show errors if not."""
        if not form.is_valid():
            self.fail(f"Form should be valid. Errors: {form.errors}")

    def assertFormInvalid(self, form, expected_errors=None):
        """Assert form is invalid with optional error checking."""
        self.assertFalse(form.is_valid())
        if expected_errors:
            for field, errors in expected_errors.items():
                self.assertIn(field, form.errors)
                for error in errors:
                    self.assertIn(error, form.errors[field])
