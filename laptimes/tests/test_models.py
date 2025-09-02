"""Tests for the laptimes models."""

from ..models import Lap, Session
from .base import BaseTestCase, ModelTestMixin


class SessionModelTests(BaseTestCase, ModelTestMixin):
    """Test cases for the Session model"""

    def test_session_creation(self):
        """Test that a session can be created with required fields"""
        self.assertEqual(self.session.track.display_name, "Test Track")
        self.assertEqual(self.session.car.display_name, "Test Car")
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
        track2 = self.create_test_track(code="track_2", display_name="Track 2")
        car2 = self.create_test_car(code="car_2", display_name="Car 2")
        session2 = self.create_test_session(
            track=track2, car=car2, session_type="Race", file_name="test2.json"
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
        empty_track = self.create_test_track(code="empty_track", display_name="Empty Track")
        empty_car = self.create_test_car(code="empty_car", display_name="Empty Car")
        empty_session = self.create_test_session(
            track=empty_track,
            car=empty_car,
            session_type="Practice",
            file_name="empty.json",
        )

        stats = empty_session.get_driver_statistics()
        self.assertEqual(stats, {})


class LapModelTests(BaseTestCase, ModelTestMixin):
    """Test cases for the Lap model"""

    def setUp(self):
        super().setUp()
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
