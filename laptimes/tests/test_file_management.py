"""Tests for file management and duplicate detection functionality."""

import json
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from ..models import Lap, Session
from ..forms import JSONUploadForm
from .base import BaseTestCase


class DriverDeletionTests(TestCase):
    """Test cases for driver deletion functionality"""

    def setUp(self):
        self.client = Client()
        self.session = Session.objects.create(
            track="Test Track",
            car="Test Car",
            session_type="Practice",
            file_name="test.json",
        )
        # Create multiple laps for the same driver
        for i in range(3):
            Lap.objects.create(
                session=self.session,
                lap_number=i + 1,
                driver_name="Test Driver",
                car_index=0,
                total_time=90.0 + i,
            )
        self.url = reverse(
            "delete_driver",
            kwargs={"session_pk": self.session.pk, "driver_name": "Test Driver"},
        )

    def test_delete_driver_success(self):
        """Test successful driver deletion"""
        # Verify laps exist before deletion
        self.assertEqual(
            Lap.objects.filter(session=self.session, driver_name="Test Driver").count(),
            3,
        )

        response = self.client.post(self.url)

        # Should redirect back to session detail
        self.assertEqual(response.status_code, 302)

        # Verify all laps for the driver were deleted
        self.assertEqual(
            Lap.objects.filter(session=self.session, driver_name="Test Driver").count(),
            0,
        )

    def test_delete_nonexistent_driver(self):
        """Test deletion of non-existent driver"""
        url = reverse(
            "delete_driver",
            kwargs={"session_pk": self.session.pk, "driver_name": "Nonexistent Driver"},
        )

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        # Original laps should still exist
        self.assertEqual(
            Lap.objects.filter(session=self.session, driver_name="Test Driver").count(),
            3,
        )


class DuplicateFileTests(TestCase):
    """Test cases for duplicate file detection functionality"""

    def setUp(self):
        self.client = Client()
        self.valid_json_data = {
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
                            "time": 85000,
                            "sectors": [28000, 28500, 28500],
                            "tyre": "M",
                            "cuts": 0,
                        }
                    ],
                }
            ],
        }

    def test_file_hash_generation_and_storage(self):
        """Test that file hash is correctly generated and stored"""
        json_content = json.dumps(self.valid_json_data)
        uploaded_file = SimpleUploadedFile(
            "test_session.json",
            json_content.encode("utf-8"),
            content_type="application/json",
        )

        response = self.client.post(reverse("home"), {"json_file": uploaded_file})

        # Should redirect on success
        self.assertEqual(response.status_code, 302)

        # Check session was created with hash
        session = Session.objects.first()
        self.assertIsNotNone(session.file_hash)
        self.assertEqual(len(session.file_hash), 64)  # SHA-256 hex length

    def test_duplicate_file_upload_prevention(self):
        """Test that uploading the same file twice is prevented"""
        json_content = json.dumps(self.valid_json_data)

        # Upload first time
        uploaded_file1 = SimpleUploadedFile(
            "test_session.json",
            json_content.encode("utf-8"),
            content_type="application/json",
        )

        response1 = self.client.post(reverse("home"), {"json_file": uploaded_file1})
        self.assertEqual(response1.status_code, 302)  # Success
        self.assertEqual(Session.objects.count(), 1)

        # Try to upload same content again
        uploaded_file2 = SimpleUploadedFile(
            "test_session_copy.json",
            json_content.encode("utf-8"),
            content_type="application/json",
        )

        response2 = self.client.post(reverse("home"), {"json_file": uploaded_file2})

        # Should not create duplicate session
        self.assertEqual(Session.objects.count(), 1)

        # Should show the form with errors (status 200, not redirect)
        self.assertEqual(response2.status_code, 200)
        self.assertContains(response2, "already been uploaded")

    def test_different_files_same_content_detection(self):
        """Test that files with identical content are detected as duplicates"""
        json_content = json.dumps(self.valid_json_data)

        # Upload with one filename
        uploaded_file1 = SimpleUploadedFile(
            "session1.json",
            json_content.encode("utf-8"),
            content_type="application/json",
        )

        response1 = self.client.post(reverse("home"), {"json_file": uploaded_file1})
        self.assertEqual(response1.status_code, 302)

        # Upload same content with different filename
        uploaded_file2 = SimpleUploadedFile(
            "session2.json",
            json_content.encode("utf-8"),
            content_type="application/json",
        )

        self.client.post(reverse("home"), {"json_file": uploaded_file2})

        # Should only have one session
        self.assertEqual(Session.objects.count(), 1)

    def test_different_content_allows_upload(self):
        """Test that files with different content can be uploaded"""
        # First file
        json_content1 = json.dumps(self.valid_json_data)
        uploaded_file1 = SimpleUploadedFile(
            "session1.json",
            json_content1.encode("utf-8"),
            content_type="application/json",
        )

        response1 = self.client.post(reverse("home"), {"json_file": uploaded_file1})
        self.assertEqual(response1.status_code, 302)

        # Second file with different content
        different_data = self.valid_json_data.copy()
        different_data["track"] = "Monza"
        json_content2 = json.dumps(different_data)

        uploaded_file2 = SimpleUploadedFile(
            "session2.json",
            json_content2.encode("utf-8"),
            content_type="application/json",
        )

        response2 = self.client.post(reverse("home"), {"json_file": uploaded_file2})
        self.assertEqual(response2.status_code, 302)

        # Should have two different sessions
        self.assertEqual(Session.objects.count(), 2)

        # Each should have different hashes
        sessions = Session.objects.all()
        hash1 = sessions[0].file_hash
        hash2 = sessions[1].file_hash
        self.assertNotEqual(hash1, hash2)

    def test_form_validation_error_message(self):
        """Test that meaningful error message is shown for duplicates"""
        json_content = json.dumps(self.valid_json_data)

        # Create a session first
        uploaded_file1 = SimpleUploadedFile(
            "test.json", json_content.encode("utf-8"), content_type="application/json"
        )

        # Upload first time through view to create session
        self.client.post(reverse("home"), {"json_file": uploaded_file1})

        # Now test form validation directly
        uploaded_file2 = SimpleUploadedFile(
            "test_duplicate.json",
            json_content.encode("utf-8"),
            content_type="application/json",
        )

        form = JSONUploadForm(files={"json_file": uploaded_file2})
        self.assertFalse(form.is_valid())
        self.assertIn("json_file", form.errors)

        error_message = form.errors["json_file"][0]
        self.assertIn("already been uploaded", error_message)
        self.assertIn("Existing session", error_message)

    def test_enhanced_error_message_with_link(self):
        """Test that error message includes clickable link to existing session"""
        json_content = json.dumps(self.valid_json_data)

        # Create a session first
        uploaded_file1 = SimpleUploadedFile(
            "test.json", json_content.encode("utf-8"), content_type="application/json"
        )

        # Upload first time through view to create session
        self.client.post(reverse("home"), {"json_file": uploaded_file1})
        session = Session.objects.first()

        # Now test form validation with enhanced error message
        uploaded_file2 = SimpleUploadedFile(
            "test_duplicate.json",
            json_content.encode("utf-8"),
            content_type="application/json",
        )

        form = JSONUploadForm(files={"json_file": uploaded_file2})
        self.assertFalse(form.is_valid())

        error_message = str(form.errors["json_file"][0])
        self.assertIn("already been uploaded", error_message)
        self.assertIn(f"/session/{session.pk}/", error_message)  # Check for URL
        self.assertIn('target="_blank"', error_message)  # Check for new tab
        self.assertIn("Click the link to view", error_message)

    def test_error_message_formatting(self):
        """Test that error message has proper date/time formatting"""
        json_content = json.dumps(self.valid_json_data)

        # Create a session first
        uploaded_file1 = SimpleUploadedFile(
            "test.json", json_content.encode("utf-8"), content_type="application/json"
        )

        self.client.post(reverse("home"), {"json_file": uploaded_file1})
        session = Session.objects.first()

        # Test form validation error message formatting
        uploaded_file2 = SimpleUploadedFile(
            "test_duplicate.json",
            json_content.encode("utf-8"),
            content_type="application/json",
        )

        form = JSONUploadForm(files={"json_file": uploaded_file2})
        self.assertFalse(form.is_valid())

        error_message = str(form.errors["json_file"][0])
        # Check for enhanced date format "YYYY-MM-DD at HH:MM"
        expected_date_format = session.upload_date.strftime("%Y-%m-%d at %H:%M")
        self.assertIn(expected_date_format, error_message)

    def test_duplicate_error_display_in_template(self):
        """Test that duplicate errors are displayed in enhanced red container"""
        json_content = json.dumps(self.valid_json_data)

        # Upload first time
        uploaded_file1 = SimpleUploadedFile(
            "test.json", json_content.encode("utf-8"), content_type="application/json"
        )

        response1 = self.client.post(reverse("home"), {"json_file": uploaded_file1})
        self.assertEqual(response1.status_code, 302)  # Success

        # Try to upload same content again
        uploaded_file2 = SimpleUploadedFile(
            "test_duplicate.json",
            json_content.encode("utf-8"),
            content_type="application/json",
        )

        response2 = self.client.post(reverse("home"), {"json_file": uploaded_file2})

        # Check that the enhanced error container appears
        self.assertEqual(response2.status_code, 200)
        self.assertContains(response2, "alert alert-danger")
        self.assertContains(response2, "Duplicate File Detected")
        self.assertContains(response2, "bi-exclamation-triangle-fill")
        self.assertContains(response2, "border-start border-danger border-4")
        self.assertContains(response2, "already been uploaded")

    def test_standard_error_display_for_non_duplicate_errors(self):
        """Test that non-duplicate errors still use standard display"""
        # Upload a file with invalid JSON structure to trigger different error
        invalid_json = '{"invalid": "structure"}'  # Missing required fields

        uploaded_file = SimpleUploadedFile(
            "invalid.json",
            invalid_json.encode("utf-8"),
            content_type="application/json",
        )

        response = self.client.post(reverse("home"), {"json_file": uploaded_file})

        # Should show standard error display, not the enhanced duplicate container
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Duplicate File Detected")
        self.assertNotContains(response, "alert alert-danger")
        self.assertContains(response, "text-danger")  # Standard error styling
        self.assertContains(response, "bi-exclamation-circle")  # Standard error icon