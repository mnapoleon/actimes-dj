"""Tests for the laptimes API endpoints."""

from django.test import Client
from django.urls import reverse

from ..models import Lap
from .base import BaseTestCase


class SessionDataAPITests(BaseTestCase):
    """Test cases for the session data API endpoint"""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.lap = Lap.objects.create(
            session=self.session,
            lap_number=1,
            driver_name="Test Driver",
            car_index=0,
            total_time=90.5,
            sectors=[30.1, 30.2, 30.2],
            tyre_compound="M",
            cuts=0,
        )
        self.url = reverse("session_api", kwargs={"pk": self.session.pk})

    def test_session_data_api(self):
        """Test session data API returns correct JSON"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["content-type"], "application/json")

        data = response.json()
        self.assertIn("session", data)
        self.assertIn("laps", data)
        self.assertEqual(data["session"]["track"], "Test Track")
        self.assertEqual(len(data["laps"]), 1)
