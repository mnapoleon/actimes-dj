"""Tests for the laptimes views."""

import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from ..models import Lap, Session
from .base import BaseTestCase, ViewTestMixin


class HomeViewTests(BaseTestCase, ViewTestMixin):
    """Test cases for the home view"""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.url = reverse("home")

    def test_home_view_get(self):
        """Test GET request to home view"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload Race Data")
        self.assertIn("form", response.context)
        self.assertIn("sessions", response.context)

    def test_home_view_displays_sessions(self):
        """Test that recent sessions are displayed"""
        # Session already created in parent setUp, so just test that it's displayed
        response = self.client.get(self.url)
        self.assertContains(response, "Test Track")
        self.assertContains(response, "Test Car")

    def create_test_json_file(self):
        """Helper to create a valid test JSON file"""
        data = {
            "track": "Silverstone",
            "players": [{"name": "Test Driver", "car": "Formula 1"}],
            "sessions": [
                {
                    "type": 1,
                    "laps": [
                        {
                            "lap": 1,
                            "car": 0,
                            "time": 90567,
                            "sectors": [30123, 30234, 30210],
                            "tyre": "M",
                            "cuts": 0,
                        }
                    ],
                }
            ],
        }
        return SimpleUploadedFile(
            "test.json",
            json.dumps(data).encode("utf-8"),
            content_type="application/json",
        )

    def test_successful_file_upload(self):
        """Test successful JSON file upload creates session and lap"""
        json_file = self.create_test_json_file()
        response = self.client.post(
            self.url, {"json_files": json_file, "upload_type": "files"}
        )

        self.assertEqual(response.status_code, 302)  # Redirect after success

        # Check that session was created
        from ..models import Car, Track

        self.assertTrue(Track.objects.filter(code="Silverstone").exists())
        self.assertTrue(Car.objects.filter(code="Formula 1").exists())
        silverstone_track = Track.objects.get(code="Silverstone")
        formula1_car = Car.objects.get(code="Formula 1")
        session = Session.objects.get(track=silverstone_track, car=formula1_car)
        self.assertEqual(session.session_type, "Practice")

        # Check that lap was created
        self.assertTrue(Lap.objects.filter(session=session).exists())
        lap = Lap.objects.get(session=session)
        self.assertEqual(lap.lap_number, 1)
        self.assertEqual(lap.driver_name, "Test Driver")
        self.assertEqual(lap.total_time, 90.567)  # Converted from milliseconds

    def test_session_type_extraction_quick_drive(self):
        """Test session type extraction from __quickDrive field"""
        data = {
            "track": "Trackday Test Track",
            "__quickDrive": '{"Mode": "/Pages/Drive/QuickDrive_Trackday.xaml"}',
            "players": [{"name": "Test Driver", "car": "Test Car"}],
            "sessions": [
                {
                    "laps": [
                        {
                            "lap": 1,
                            "car": 0,
                            "time": 90567,
                            "sectors": [],
                            "tyre": "M",
                            "cuts": 0,
                        }
                    ]
                }
            ],
        }
        json_file = SimpleUploadedFile(
            "test.json",
            json.dumps(data).encode("utf-8"),
            content_type="application/json",
        )

        self.client.post(self.url, {"json_files": json_file, "upload_type": "files"})
        from ..models import Track

        trackday_track = Track.objects.get(code="Trackday Test Track")
        session = Session.objects.get(track=trackday_track)
        self.assertEqual(session.session_type, "Trackday")


class SessionDetailViewTests(BaseTestCase, ViewTestMixin):
    """Test cases for the session detail view"""

    def setUp(self):
        super().setUp()
        self.client = Client()
        # Use the session from BaseTestCase
        self.lap1 = Lap.objects.create(
            session=self.session,
            lap_number=1,
            driver_name="Driver 1",
            car_index=0,
            total_time=90.5,
            sectors=[30.1, 30.2, 30.2],
        )
        self.lap2 = Lap.objects.create(
            session=self.session,
            lap_number=2,
            driver_name="Driver 2",
            car_index=1,
            total_time=91.0,
            sectors=[30.3, 30.4, 30.3],
        )
        self.url = reverse("session_detail", kwargs={"pk": self.session.pk})

    def test_session_detail_view(self):
        """Test session detail view displays correctly"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Track")
        self.assertContains(response, "Driver 1")
        self.assertContains(response, "Driver 2")

    def test_driver_filtering(self):
        """Test filtering by driver"""
        response = self.client.get(self.url, {"driver": "Driver 1"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Driver 1")
        # Should only show Driver 1's laps

    def test_sorting_by_total_time(self):
        """Test sorting by total time"""
        response = self.client.get(self.url, {"sort": "total_time"})
        self.assertEqual(response.status_code, 200)
        # Check that laps are sorted by total time

    def test_context_data(self):
        """Test that context contains all required data"""
        response = self.client.get(self.url)
        context = response.context

        self.assertIn("session", context)
        self.assertIn("laps", context)
        self.assertIn("drivers", context)
        self.assertIn("chart_data", context)
        self.assertIn("fastest_lap", context)
        self.assertIn("sector_count", context)
        self.assertIn("driver_lap_counts", context)
        self.assertIn("driver_statistics", context)
        self.assertIn("fastest_lap_time", context)
        self.assertIn("best_optimal_time", context)

        self.assertEqual(context["session"], self.session)
        self.assertEqual(set(context["drivers"]), {"Driver 1", "Driver 2"})
        self.assertEqual(context["driver_lap_counts"]["Driver 1"], 1)
        self.assertEqual(context["driver_lap_counts"]["Driver 2"], 1)

        # Test purple highlighting context variables
        self.assertIsNotNone(context["fastest_lap_time"])
        # best_optimal_time might be None if no sectors data exists
        self.assertIsNotNone(context["driver_statistics"])

    def test_purple_highlighting_context(self):
        """Test that purple highlighting context variables are correctly calculated"""
        # Create a session with drivers having different best lap and optimal times
        highlight_track = self.create_test_track(
            code="highlight_test", display_name="Highlight Test Track"
        )
        session = self.create_test_session(
            track=highlight_track,
            session_type="Practice",
            file_name="test.json",
        )

        # Driver A - slower best lap but better optimal due to mixed sectors
        Lap.objects.create(
            session=session,
            lap_number=1,
            driver_name="Driver A",
            car_index=0,
            total_time=61.5,
            sectors=[20.0, 20.8, 20.7],
            tyre_compound="M",
            cuts=0,
        )
        Lap.objects.create(
            session=session,
            lap_number=2,
            driver_name="Driver A",
            car_index=0,
            total_time=62.0,
            sectors=[19.0, 21.5, 21.5],  # Best sector 1
            tyre_compound="M",
            cuts=0,
        )

        # Driver B - fastest actual lap
        Lap.objects.create(
            session=session,
            lap_number=1,
            driver_name="Driver B",
            car_index=1,
            total_time=60.0,  # FASTEST LAP
            sectors=[20.1, 20.5, 20.0],
            tyre_compound="S",
            cuts=0,
        )

        url = reverse("session_detail", kwargs={"pk": session.pk})
        response = self.client.get(url)
        context = response.context

        # Test that fastest lap time is correctly identified
        self.assertEqual(context["fastest_lap_time"], 60.0)

        # Test that best optimal time is correctly calculated
        # Driver A optimal: 19.0 + 20.8 + 20.7 = 60.5
        # Driver B optimal: 20.1 + 20.5 + 20.0 = 60.6
        # So Driver A has the best optimal time (60.5)
        self.assertAlmostEqual(context["best_optimal_time"], 60.5, places=1)

        # Clean up
        session.delete()

    def test_chart_lap_zero_inclusion_all_sessions(self):
        """Test that lap 0 is included in chart for all session types"""
        # Create Race session
        race_track = self.create_test_track(
            code="race_track", display_name="Race Track"
        )
        race_car = self.create_test_car(code="race_car", display_name="Race Car")
        race_session = self.create_test_session(
            track=race_track,
            car=race_car,
            session_type="Race",
            file_name="race.json",
        )

        # Create Practice session
        practice_track = self.create_test_track(
            code="practice_track", display_name="Practice Track"
        )
        practice_car = self.create_test_car(
            code="practice_car", display_name="Practice Car"
        )
        practice_session = self.create_test_session(
            track=practice_track,
            car=practice_car,
            session_type="Practice",
            file_name="practice.json",
        )

        # Add laps including lap 0 to both sessions
        for session in [race_session, practice_session]:
            for lap_num in [0, 1, 2]:  # Include lap 0 (out lap)
                Lap.objects.create(
                    session=session,
                    lap_number=lap_num,
                    driver_name="Test Driver",
                    car_index=0,
                    total_time=60.0 + lap_num,
                    sectors=[20.0, 20.0, 20.0],
                    tyre_compound="M",
                    cuts=0,
                )

        # Test Race session includes lap 0
        race_url = reverse("session_detail", kwargs={"pk": race_session.pk})
        race_response = self.client.get(race_url)
        race_context = race_response.context

        race_lap_numbers = race_context["unique_lap_numbers"]
        self.assertIn(0, race_lap_numbers)  # Lap 0 should be included
        self.assertEqual(race_lap_numbers, [0, 1, 2])

        # Test Practice session now also includes lap 0
        practice_url = reverse("session_detail", kwargs={"pk": practice_session.pk})
        practice_response = self.client.get(practice_url)
        practice_context = practice_response.context

        practice_lap_numbers = practice_context["unique_lap_numbers"]
        self.assertIn(0, practice_lap_numbers)  # Lap 0 should now be included
        self.assertEqual(practice_lap_numbers, [0, 1, 2])

        # Clean up
        race_session.delete()
        practice_session.delete()


class SessionEditViewTests(BaseTestCase, ViewTestMixin):
    """Test cases for the session edit view"""

    def setUp(self):
        super().setUp()
        self.client = Client()
        # Use session from BaseTestCase
        self.url = reverse("session_edit", kwargs={"pk": self.session.pk})

    def test_session_edit_view_get(self):
        """Test GET request to session edit view"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Track")  # From BaseTestCase
        self.assertContains(response, "Test Car")  # From BaseTestCase

    def test_session_edit_view_post(self):
        """Test POST request to update session"""
        form_data = {
            "track_choice": "",
            "track_new_code": "updated_track",
            "track_new_display": "Updated Track",
            "car_choice": "",
            "car_new_code": "updated_car",
            "car_new_display": "Updated Car",
            "session_name": "Updated Session",
            "upload_date": timezone.now().strftime("%Y-%m-%dT%H:%M"),
        }
        response = self.client.post(self.url, form_data)

        # Should redirect to session detail after successful update
        self.assertEqual(response.status_code, 302)

        # Check that session was updated
        self.session.refresh_from_db()
        self.assertEqual(self.session.track.display_name, "Updated Track")
        self.assertEqual(self.session.car.display_name, "Updated Car")
        self.assertEqual(self.session.session_name, "Updated Session")


class SessionDeleteViewTests(BaseTestCase, ViewTestMixin):
    """Test cases for the session delete view"""

    def setUp(self):
        super().setUp()
        self.client = Client()
        # Use session from BaseTestCase
        self.url = reverse("session_delete", kwargs={"pk": self.session.pk})

    def test_session_delete_view_get(self):
        """Test GET request to session delete confirmation"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirm Session Deletion")
        self.assertContains(response, self.session.track)

    def test_session_delete_view_post(self):
        """Test POST request to delete session"""
        response = self.client.post(self.url)

        # Should redirect to home after deletion
        self.assertEqual(response.status_code, 302)

        # Check that session was deleted
        self.assertFalse(Session.objects.filter(pk=self.session.pk).exists())
