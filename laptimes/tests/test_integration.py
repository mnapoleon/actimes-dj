"""Integration tests for the laptimes application."""

import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Lap, Session


class IntegrationTests(TestCase):
    """Integration tests for the complete workflow"""

    def setUp(self):
        self.client = Client()

    def test_complete_upload_and_view_workflow(self):
        """Test complete workflow from upload to viewing session details"""
        # Create test JSON data
        data = {
            "track": "Monza",
            "players": [
                {"name": "Driver A", "car": "Ferrari"},
                {"name": "Driver B", "car": "Ferrari"},
            ],
            "sessions": [
                {
                    "type": 2,  # Qualifying
                    "laps": [
                        {
                            "lap": 1,
                            "car": 0,
                            "time": 85000,
                            "sectors": [28000, 28500, 28500],
                            "tyre": "S",
                            "cuts": 0,
                        },
                        {
                            "lap": 1,
                            "car": 1,
                            "time": 86000,
                            "sectors": [28200, 28600, 29200],
                            "tyre": "S",
                            "cuts": 1,
                        },
                    ],
                }
            ],
        }

        json_file = SimpleUploadedFile(
            "monza_quali.json",
            json.dumps(data).encode("utf-8"),
            content_type="application/json",
        )

        # Upload the file
        upload_response = self.client.post(reverse("home"), {"json_file": json_file})
        self.assertEqual(upload_response.status_code, 302)

        # Verify session was created
        session = Session.objects.get(track="Monza")
        self.assertEqual(session.session_type, "Qualifying")
        self.assertEqual(session.car, "Ferrari")

        # Verify laps were created
        laps = Lap.objects.filter(session=session)
        self.assertEqual(laps.count(), 2)

        # Check lap data conversion
        lap_a = laps.get(driver_name="Driver A")
        self.assertEqual(lap_a.total_time, 85.0)  # Converted from ms
        self.assertEqual(lap_a.sectors, [28.0, 28.5, 28.5])  # Converted from ms

        lap_b = laps.get(driver_name="Driver B")
        self.assertEqual(lap_b.cuts, 1)

        # View session detail page
        detail_response = self.client.get(
            reverse("session_detail", kwargs={"pk": session.pk})
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Monza")
        self.assertContains(detail_response, "Driver A")
        self.assertContains(detail_response, "Driver B")

        # Test API endpoint
        api_response = self.client.get(
            reverse("session_api", kwargs={"pk": session.pk})
        )
        self.assertEqual(api_response.status_code, 200)
        api_data = api_response.json()
        self.assertEqual(api_data["session"]["track"], "Monza")
        self.assertEqual(len(api_data["laps"]), 2)
