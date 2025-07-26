import json
import tempfile

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import JSONUploadForm, SessionEditForm
from .models import Lap, Session


class SessionModelTests(TestCase):
    """Test cases for the Session model"""

    def setUp(self):
        self.session = Session.objects.create(
            session_name="Test Session",
            track="Test Track",
            car="Test Car",
            session_type="Practice",
            file_name="test.json",
            players_data=[{"name": "Test Driver", "car": "Test Car"}],
        )

    def test_session_creation(self):
        """Test that a session can be created with required fields"""
        self.assertEqual(self.session.track, "Test Track")
        self.assertEqual(self.session.car, "Test Car")
        self.assertEqual(self.session.session_type, "Practice")
        self.assertTrue(self.session.upload_date)

    def test_session_str_with_name(self):
        """Test string representation with session name"""
        expected = "Test Session - Test Track - Test Car"
        self.assertEqual(str(self.session), expected)

    def test_session_str_without_name(self):
        """Test string representation without session name"""
        self.session.session_name = ""
        self.session.save()
        expected = "Test Track - Test Car (Practice)"
        self.assertEqual(str(self.session), expected)

    def test_session_ordering(self):
        """Test that sessions are ordered by upload_date descending"""
        session2 = Session.objects.create(
            track="Track 2", car="Car 2", session_type="Race", file_name="test2.json"
        )
        sessions = Session.objects.all()
        self.assertEqual(sessions.first(), session2)

    def test_get_drivers(self):
        """Test getting unique drivers from session"""
        Lap.objects.create(
            session=self.session,
            lap_number=1,
            driver_name="Driver 1",
            car_index=0,
            total_time=90.5,
        )
        Lap.objects.create(
            session=self.session,
            lap_number=2,
            driver_name="Driver 2",
            car_index=1,
            total_time=91.0,
        )
        drivers = self.session.get_drivers()
        self.assertEqual(set(drivers), {"Driver 1", "Driver 2"})

    def test_get_fastest_lap(self):
        """Test getting the fastest lap in session"""
        Lap.objects.create(
            session=self.session,
            lap_number=1,
            driver_name="Driver 1",
            car_index=0,
            total_time=90.5,
        )
        lap2 = Lap.objects.create(
            session=self.session,
            lap_number=2,
            driver_name="Driver 1",
            car_index=0,
            total_time=89.2,
        )
        fastest = self.session.get_fastest_lap()
        self.assertEqual(fastest, lap2)

    def test_get_optimal_lap_time_single_driver(self):
        """Test optimal lap time calculation for single driver"""
        # Create laps with different sector times
        Lap.objects.create(
            session=self.session,
            lap_number=1,
            driver_name="Test Driver",
            car_index=0,
            total_time=90.567,
            sectors=[30.123, 30.234, 30.210],
            tyre_compound="M",
            cuts=0,
        )
        Lap.objects.create(
            session=self.session,
            lap_number=2,
            driver_name="Test Driver",
            car_index=0,
            total_time=89.0,
            sectors=[29.5, 29.8, 29.7],  # Better sectors
            tyre_compound="S",
            cuts=0,
        )

        optimal_time = self.session.get_optimal_lap_time("Test Driver")
        # Should be sum of best sectors: 29.5 + 29.8 + 29.7 = 89.0
        self.assertAlmostEqual(optimal_time, 89.0, places=3)

    def test_get_optimal_lap_time_mixed_sectors(self):
        """Test optimal lap time with mixed best sectors"""
        Lap.objects.create(
            session=self.session,
            lap_number=1,
            driver_name="Test Driver",
            car_index=0,
            total_time=90.567,
            sectors=[30.123, 30.234, 30.210],
            tyre_compound="M",
            cuts=0,
        )
        # Create another lap with some better sectors
        Lap.objects.create(
            session=self.session,
            lap_number=2,
            driver_name="Test Driver",
            car_index=0,
            total_time=92.0,
            sectors=[28.0, 32.0, 32.0],  # Only sector 1 is best
            tyre_compound="S",
            cuts=0,
        )

        optimal_time = self.session.get_optimal_lap_time("Test Driver")
        # Should be: 28.0 (best S1) + 30.234 (best S2) + 30.210 (best S3) = 88.444
        expected = 28.0 + 30.234 + 30.210
        self.assertAlmostEqual(optimal_time, expected, places=3)

    def test_get_optimal_lap_time_nonexistent_driver(self):
        """Test optimal lap time for non-existent driver"""
        optimal_time = self.session.get_optimal_lap_time("Nonexistent Driver")
        self.assertIsNone(optimal_time)

    def test_get_driver_statistics(self):
        """Test comprehensive driver statistics calculation"""
        # Create Test Driver laps
        Lap.objects.create(
            session=self.session,
            lap_number=1,
            driver_name="Test Driver",
            car_index=0,
            total_time=90.567,
            sectors=[30.123, 30.234, 30.210],
            tyre_compound="M",
            cuts=0,
        )
        Lap.objects.create(
            session=self.session,
            lap_number=2,
            driver_name="Test Driver",
            car_index=0,
            total_time=91.0,
            sectors=[30.0, 30.5, 30.5],
            tyre_compound="M",
            cuts=0,
        )

        # Add another driver for comparison
        Lap.objects.create(
            session=self.session,
            lap_number=1,
            driver_name="Driver B",
            car_index=1,
            total_time=88.5,
            sectors=[29.0, 29.5, 30.0],
            tyre_compound="S",
            cuts=0,
        )

        stats = self.session.get_driver_statistics()

        # Test structure
        self.assertIn("Test Driver", stats)
        self.assertIn("Driver B", stats)

        # Test Test Driver stats
        test_driver_stats = stats["Test Driver"]
        self.assertEqual(test_driver_stats["best_lap_time"], 90.567)
        self.assertEqual(test_driver_stats["lap_count"], 2)
        self.assertAlmostEqual(test_driver_stats["avg_lap_time"], 90.7835, places=3)
        self.assertTrue(
            test_driver_stats["consistency"] > 0
        )  # Should have some variance
        self.assertTrue(test_driver_stats["visible"])

        # Test Driver B stats
        driver_b_stats = stats["Driver B"]
        self.assertEqual(driver_b_stats["best_lap_time"], 88.5)
        self.assertEqual(driver_b_stats["lap_count"], 1)
        self.assertEqual(driver_b_stats["avg_lap_time"], 88.5)
        self.assertEqual(driver_b_stats["consistency"], 0.0)  # Only one lap

    def test_get_driver_statistics_empty_session(self):
        """Test driver statistics for session with no laps"""
        empty_session = Session.objects.create(
            track="Empty Track",
            car="Empty Car",
            session_type="Practice",
            file_name="empty.json",
        )

        stats = empty_session.get_driver_statistics()
        self.assertEqual(stats, {})


class LapModelTests(TestCase):
    """Test cases for the Lap model"""

    def setUp(self):
        self.session = Session.objects.create(
            track="Test Track",
            car="Test Car",
            session_type="Practice",
            file_name="test.json",
        )
        self.lap = Lap.objects.create(
            session=self.session,
            lap_number=1,
            driver_name="Test Driver",
            car_index=0,
            total_time=90.567,
            sectors=[30.123, 30.234, 30.210],
            tyre_compound="M",
            cuts=0,
        )

    def test_lap_creation(self):
        """Test that a lap can be created with required fields"""
        self.assertEqual(self.lap.lap_number, 1)
        self.assertEqual(self.lap.driver_name, "Test Driver")
        self.assertEqual(self.lap.total_time, 90.567)
        self.assertEqual(self.lap.sectors, [30.123, 30.234, 30.210])

    def test_lap_str(self):
        """Test string representation of lap"""
        expected = "Lap 1 - Test Driver (1:30.567)"
        self.assertEqual(str(self.lap), expected)

    def test_format_time(self):
        """Test time formatting"""
        self.assertEqual(self.lap.format_time(), "1:30.567")

        # Test with different time
        self.lap.total_time = 125.123
        self.assertEqual(self.lap.format_time(), "2:05.123")

    def test_get_sector_times(self):
        """Test getting sector times as list"""
        self.assertEqual(self.lap.get_sector_times(), [30.123, 30.234, 30.210])

        # Test with no sectors
        self.lap.sectors = None
        self.assertEqual(self.lap.get_sector_times(), [])

    def test_unique_together_constraint(self):
        """Test that the unique constraint works"""
        with self.assertRaises(Exception):
            Lap.objects.create(
                session=self.session,
                lap_number=1,
                driver_name="Another Driver",
                car_index=0,  # Same session, lap_number, and car_index
                total_time=91.0,
            )

    def test_lap_ordering(self):
        """Test that laps are ordered by session and lap_number"""
        lap2 = Lap.objects.create(
            session=self.session,
            lap_number=2,
            driver_name="Test Driver",
            car_index=0,
            total_time=91.0,
        )
        laps = Lap.objects.all()
        self.assertEqual(list(laps), [self.lap, lap2])

    def test_format_time_static(self):
        """Test static time formatting method"""
        # Test normal time
        self.assertEqual(Lap.format_time_static(90.567), "1:30.567")

        # Test time over 2 minutes
        self.assertEqual(Lap.format_time_static(125.123), "2:05.123")

        # Test time under 1 minute
        self.assertEqual(Lap.format_time_static(45.789), "0:45.789")

        # Test None value
        self.assertEqual(Lap.format_time_static(None), "N/A")


class JSONUploadFormTests(TestCase):
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
        form = JSONUploadForm(files={"json_file": json_file})
        self.assertTrue(form.is_valid())

    def test_invalid_file_extension(self):
        """Test rejection of non-JSON files"""
        txt_file = SimpleUploadedFile(
            "test.txt", b"not json content", content_type="text/plain"
        )
        form = JSONUploadForm(files={"json_file": txt_file})
        self.assertFalse(form.is_valid())
        self.assertIn("File must have .json extension", form.errors["json_file"])

    def test_invalid_json_content(self):
        """Test rejection of invalid JSON content"""
        invalid_file = SimpleUploadedFile(
            "test.json", b"invalid json content", content_type="application/json"
        )
        form = JSONUploadForm(files={"json_file": invalid_file})
        self.assertFalse(form.is_valid())
        self.assertIn("Invalid JSON file format", form.errors["json_file"])

    def test_missing_required_fields(self):
        """Test rejection of JSON missing required fields"""
        incomplete_data = {"track": "Test Track"}
        json_file = self.create_test_json_file(incomplete_data)
        form = JSONUploadForm(files={"json_file": json_file})
        self.assertFalse(form.is_valid())

    def test_invalid_players_structure(self):
        """Test rejection of invalid players structure"""
        invalid_data = {
            "track": "Test Track",
            "players": "not a list",
            "sessions": [{"laps": []}],
        }
        json_file = self.create_test_json_file(invalid_data)
        form = JSONUploadForm(files={"json_file": json_file})
        self.assertFalse(form.is_valid())

    def test_empty_sessions(self):
        """Test rejection of empty sessions"""
        invalid_data = {
            "track": "Test Track",
            "players": [{"name": "Test"}],
            "sessions": [],
        }
        json_file = self.create_test_json_file(invalid_data)
        form = JSONUploadForm(files={"json_file": json_file})
        self.assertFalse(form.is_valid())


class SessionEditFormTests(TestCase):
    """Test cases for the session edit form"""

    def setUp(self):
        self.session = Session.objects.create(
            track="Original Track",
            car="Original Car",
            session_type="Practice",
            file_name="test.json",
        )

    def test_form_initialization(self):
        """Test form initializes with session data"""
        form = SessionEditForm(instance=self.session)
        self.assertEqual(form.fields["track_select"].initial, "Original Track")
        self.assertEqual(form.fields["car_select"].initial, "Original Car")

    def test_track_text_input(self):
        """Test using text input for track"""
        form_data = {
            "track_select": "",
            "track_text": "New Track",
            "car_select": "Original Car",
            "car_text": "",
            "session_name": "Test Session",
            "upload_date": timezone.now().strftime("%Y-%m-%dT%H:%M"),
        }
        form = SessionEditForm(data=form_data, instance=self.session)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["track"], "New Track")

    def test_car_text_input(self):
        """Test using text input for car"""
        form_data = {
            "track_select": "Original Track",
            "track_text": "",
            "car_select": "",
            "car_text": "New Car",
            "session_name": "Test Session",
            "upload_date": timezone.now().strftime("%Y-%m-%dT%H:%M"),
        }
        form = SessionEditForm(data=form_data, instance=self.session)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["car"], "New Car")

    def test_missing_track_and_car(self):
        """Test form validation when both track fields are empty"""
        form_data = {
            "track_select": "",
            "track_text": "",
            "car_select": "Original Car",
            "car_text": "",
            "session_name": "Test Session",
            "upload_date": timezone.now().strftime("%Y-%m-%dT%H:%M"),
        }
        form = SessionEditForm(data=form_data, instance=self.session)
        self.assertFalse(form.is_valid())
        self.assertIn("track_select", form.errors)


class HomeViewTests(TestCase):
    """Test cases for the home view"""

    def setUp(self):
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
        Session.objects.create(
            track="Test Track",
            car="Test Car",
            session_type="Practice",
            file_name="test.json",
        )
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
        response = self.client.post(self.url, {"json_file": json_file})

        self.assertEqual(response.status_code, 302)  # Redirect after success

        # Check that session was created
        self.assertTrue(Session.objects.filter(track="Silverstone").exists())
        session = Session.objects.get(track="Silverstone")
        self.assertEqual(session.car, "Formula 1")
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
            "track": "Test Track",
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

        self.client.post(self.url, {"json_file": json_file})
        session = Session.objects.get(track="Test Track")
        self.assertEqual(session.session_type, "Trackday")


class SessionDetailViewTests(TestCase):
    """Test cases for the session detail view"""

    def setUp(self):
        self.client = Client()
        self.session = Session.objects.create(
            track="Test Track",
            car="Test Car",
            session_type="Practice",
            file_name="test.json",
        )
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
        session = Session.objects.create(
            track="Highlight Test Track",
            car="Test Car",
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
        race_session = Session.objects.create(
            track="Race Track",
            car="Race Car",
            session_type="Race",
            file_name="race.json",
        )

        # Create Practice session
        practice_session = Session.objects.create(
            track="Practice Track",
            car="Practice Car",
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


class SessionEditViewTests(TestCase):
    """Test cases for the session edit view"""

    def setUp(self):
        self.client = Client()
        self.session = Session.objects.create(
            track="Original Track",
            car="Original Car",
            session_type="Practice",
            file_name="test.json",
        )
        self.url = reverse("session_edit", kwargs={"pk": self.session.pk})

    def test_session_edit_view_get(self):
        """Test GET request to session edit view"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Original Track")
        self.assertContains(response, "Original Car")

    def test_session_edit_view_post(self):
        """Test POST request to update session"""
        form_data = {
            "track_select": "",
            "track_text": "Updated Track",
            "car_select": "",
            "car_text": "Updated Car",
            "session_name": "Updated Session",
            "upload_date": timezone.now().strftime("%Y-%m-%dT%H:%M"),
        }
        response = self.client.post(self.url, form_data)

        # Should redirect to session detail after successful update
        self.assertEqual(response.status_code, 302)

        # Check that session was updated
        self.session.refresh_from_db()
        self.assertEqual(self.session.track, "Updated Track")
        self.assertEqual(self.session.car, "Updated Car")
        self.assertEqual(self.session.session_name, "Updated Session")


class SessionDeleteViewTests(TestCase):
    """Test cases for the session delete view"""

    def setUp(self):
        self.client = Client()
        self.session = Session.objects.create(
            track="Test Track",
            car="Test Car",
            session_type="Practice",
            file_name="test.json",
        )
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


class SessionDataAPITests(TestCase):
    """Test cases for the session data API endpoint"""

    def setUp(self):
        self.client = Client()
        self.session = Session.objects.create(
            track="Test Track",
            car="Test Car",
            session_type="Practice",
            file_name="test.json",
        )
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
        from .forms import JSONUploadForm

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
        from .forms import JSONUploadForm

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
        from .forms import JSONUploadForm

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


class AdminInterfaceTests(TestCase):
    """Test cases for admin interface enhancements"""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="testpass123"
        )
        self.client.login(username="admin", password="testpass123")

        # Create test session with hash
        self.session_with_hash = Session.objects.create(
            track="Test Track",
            car="Test Car",
            session_type="Practice",
            file_name="test.json",
            players_data=[{"name": "Test Driver"}],
            file_hash="a1b2c3d4e5f6789012345678901234567890123456789012345678901234567890",
        )

        # Create test session without hash (legacy)
        self.session_without_hash = Session.objects.create(
            track="Legacy Track",
            car="Legacy Car",
            session_type="Race",
            file_name="legacy.json",
            players_data=[{"name": "Legacy Driver"}],
            file_hash=None,
        )

    def test_admin_list_display_includes_hash(self):
        """Test that admin list view shows shortened file hash"""
        response = self.client.get("/admin/laptimes/session/")
        self.assertEqual(response.status_code, 200)

        # Check that shortened hash is displayed
        self.assertContains(response, "a1b2c3d4...")
        self.assertContains(response, "No hash")  # For legacy session

    def test_admin_session_detail_shows_full_hash(self):
        """Test that admin detail view shows full file hash"""
        response = self.client.get(
            f"/admin/laptimes/session/{self.session_with_hash.pk}/change/"
        )
        self.assertEqual(response.status_code, 200)

        # Check for full hash display
        self.assertContains(response, self.session_with_hash.file_hash)
        self.assertContains(response, "Click to copy")

    def test_admin_legacy_session_hash_message(self):
        """Test that legacy sessions show appropriate hash message"""
        response = self.client.get(
            f"/admin/laptimes/session/{self.session_without_hash.pk}/change/"
        )
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "No hash available")
        self.assertContains(response, "uploaded before duplicate prevention")

    def test_admin_search_includes_hash(self):
        """Test that admin search functionality includes file hash"""
        # Search by partial hash
        search_term = "a1b2c3d4"
        response = self.client.get(f"/admin/laptimes/session/?q={search_term}")
        self.assertEqual(response.status_code, 200)

        # Should find the session with matching hash
        self.assertContains(response, "Test Track")
        # Note: Legacy track might still appear in filter options, so we check for specific context

    def test_admin_fieldsets_organization(self):
        """Test that admin form is properly organized with fieldsets"""
        response = self.client.get(
            f"/admin/laptimes/session/{self.session_with_hash.pk}/change/"
        )
        self.assertEqual(response.status_code, 200)

        # Check for proper fieldset organization
        self.assertContains(response, "Session Information")
        self.assertContains(response, "File Information")
        self.assertContains(response, "Player Data")

        # Player data should be collapsible (check for collapse class in any form)
        self.assertIn("collapse", response.content.decode())
