"""
Unit tests for the statistics calculation module.
"""

from laptimes.models import Lap, Session
from laptimes.statistics import SessionStatisticsCalculator

from .base import BaseTestCase


class SessionStatisticsCalculatorTests(BaseTestCase):
    """Test the SessionStatisticsCalculator class"""

    def setUp(self):
        super().setUp()
        self.calculator = SessionStatisticsCalculator(self.session)

    def test_calculate_driver_statistics_matches_model_method(self):
        """Test that calculator results match the original model method"""
        # Calculate using both methods
        calculator_stats = self.calculator.calculate_driver_statistics()
        model_stats = self.session.get_driver_statistics()

        # Should have the same drivers
        self.assertEqual(set(calculator_stats.keys()), set(model_stats.keys()))

        # Check each driver's statistics match
        for driver in calculator_stats.keys():
            calc_driver = calculator_stats[driver]
            model_driver = model_stats[driver]

            self.assertAlmostEqual(
                calc_driver["best_lap_time"], model_driver["best_lap_time"], places=3
            )
            self.assertEqual(calc_driver["lap_count"], model_driver["lap_count"])
            self.assertEqual(
                calc_driver["racing_lap_count"], model_driver["racing_lap_count"]
            )
            self.assertAlmostEqual(
                calc_driver["avg_lap_time"], model_driver["avg_lap_time"], places=3
            )
            self.assertAlmostEqual(
                calc_driver["consistency"], model_driver["consistency"], places=3
            )

            # Handle None values for optimal lap time
            if calc_driver["optimal_lap_time"] is None:
                self.assertIsNone(model_driver["optimal_lap_time"])
            else:
                self.assertAlmostEqual(
                    calc_driver["optimal_lap_time"],
                    model_driver["optimal_lap_time"],
                    places=3,
                )

    def test_calculate_optimal_lap_time_matches_model_method(self):
        """Test that optimal lap time calculation matches original model method"""
        for driver in self.session.get_drivers():
            calculator_optimal = self.calculator.calculate_optimal_lap_time(driver)
            model_optimal = self.session.get_optimal_lap_time(driver)

            if calculator_optimal is None:
                self.assertIsNone(model_optimal)
            else:
                self.assertAlmostEqual(calculator_optimal, model_optimal, places=3)

    def test_calculate_fastest_lap_time_matches_model_method(self):
        """Test that fastest lap calculation matches original model method"""
        calculator_fastest = self.calculator.calculate_fastest_lap_time()
        model_fastest_lap = self.session.get_fastest_lap()

        if calculator_fastest is None:
            self.assertIsNone(model_fastest_lap)
        else:
            self.assertAlmostEqual(
                calculator_fastest, model_fastest_lap.total_time, places=3
            )

    def test_calculate_chart_data_structure(self):
        """Test that chart data has the expected structure"""
        chart_data = self.calculator.calculate_chart_data()

        # Should be a dictionary
        self.assertIsInstance(chart_data, dict)

        # Should have entries for each driver
        drivers = list(
            self.session.laps.values_list("driver_name", flat=True).distinct()
        )
        for driver in drivers:
            self.assertIn(driver, chart_data)

            # Each driver should have data for each lap number
            driver_data = chart_data[driver]
            self.assertIsInstance(driver_data, dict)

            # Check that lap numbers are present
            lap_numbers = list(
                self.session.laps.values_list("lap_number", flat=True)
                .distinct()
                .order_by("lap_number")
            )
            for lap_number in lap_numbers:
                self.assertIn(lap_number, driver_data)

    def test_calculate_sector_statistics_structure(self):
        """Test that sector statistics have the expected structure"""
        sector_stats = self.calculator.calculate_sector_statistics()

        # Should have the expected top-level keys
        self.assertIn("sector_highlights", sector_stats)
        self.assertIn("driver_pb_sectors", sector_stats)
        self.assertIn("lap_highlights", sector_stats)
        self.assertIn("sector_count", sector_stats)

        # Check lap highlights structure
        lap_highlights = sector_stats["lap_highlights"]
        self.assertIn("fastest_total", lap_highlights)
        self.assertIn("slowest_total", lap_highlights)
        self.assertIn("driver_pb_total", lap_highlights)

    def test_calculate_all_statistics_completeness(self):
        """Test that calculate_all_statistics returns all expected fields"""
        stats = self.calculator.calculate_all_statistics()

        expected_keys = {
            "session_statistics",
            "chart_data",
            "sector_statistics",
            "fastest_lap_time",
            "fastest_lap_driver",
            "total_laps",
            "total_drivers",
        }

        self.assertEqual(set(stats.keys()), expected_keys)

        # Verify types
        self.assertIsInstance(stats["session_statistics"], dict)
        self.assertIsInstance(stats["chart_data"], dict)
        self.assertIsInstance(stats["sector_statistics"], dict)
        self.assertIsInstance(stats["total_laps"], int)
        self.assertIsInstance(stats["total_drivers"], int)

        # Verify values make sense
        self.assertEqual(stats["total_laps"], self.session.laps.count())
        self.assertEqual(
            stats["total_drivers"],
            self.session.laps.values_list("driver_name", flat=True).distinct().count(),
        )

    def test_empty_session_statistics(self):
        """Test statistics calculation for an empty session"""
        empty_track = self.create_test_track(code="empty_track", display_name="Empty Track")
        empty_car = self.create_test_car(code="empty_car", display_name="Empty Car")
        empty_session = self.create_test_session(
            track=empty_track,
            car=empty_car,
            session_type="Practice",
            file_name="test.json",
        )

        calculator = SessionStatisticsCalculator(empty_session)
        stats = calculator.calculate_all_statistics()

        # Should handle empty session gracefully
        self.assertEqual(stats["total_laps"], 0)
        self.assertEqual(stats["total_drivers"], 0)
        self.assertIsNone(stats["fastest_lap_time"])
        self.assertEqual(stats["fastest_lap_driver"], "")
        self.assertEqual(stats["session_statistics"], {})

    def test_out_lap_exclusion(self):
        """Test that out laps (lap_number = 0) are properly excluded from performance calculations"""
        # Create a session with mix of out laps and racing laps
        outlap_track = self.create_test_track(code="outlap_track", display_name="Out Lap Track")
        outlap_car = self.create_test_car(code="outlap_car", display_name="Out Lap Car")
        session = self.create_test_session(
            track=outlap_track,
            car=outlap_car,
            session_type="Practice",
            file_name="test.json",
        )

        # Add out lap (should be excluded from performance stats)
        Lap.objects.create(
            session=session,
            lap_number=0,  # Out lap
            driver_name="TestDriver",
            car_index=0,
            total_time=130.0,  # Slower out lap
            sectors=[45.0, 45.0, 40.0],
            tyre_compound="M",
        )

        # Add racing laps
        Lap.objects.create(
            session=session,
            lap_number=1,
            driver_name="TestDriver",
            car_index=0,
            total_time=120.0,  # Faster racing lap
            sectors=[40.0, 40.0, 40.0],
            tyre_compound="M",
        )

        calculator = SessionStatisticsCalculator(session)
        stats = calculator.calculate_all_statistics()

        # Fastest lap should be the racing lap, not the out lap
        self.assertEqual(stats["fastest_lap_time"], 120.0)

        # Driver stats should use racing lap for best time
        driver_stats = stats["session_statistics"]["TestDriver"]
        self.assertEqual(driver_stats["best_lap_time"], 120.0)
        self.assertEqual(driver_stats["lap_count"], 2)  # Total includes out lap
        self.assertEqual(driver_stats["racing_lap_count"], 1)  # Only racing laps


class StatisticsAccuracyTests(BaseTestCase):
    """Test accuracy of statistics calculations"""

    def setUp(self):
        super().setUp()
        # Create additional test data for more comprehensive testing
        self.create_additional_test_data()

    def create_additional_test_data(self):
        """Create more complex test data"""
        # Add more laps with varying performance, using different car_index for different drivers
        test_laps = [
            {
                "lap": 1,
                "driver": "TestDriver1",
                "car_index": 0,
                "time": 120.0,
                "sectors": [40.0, 41.0, 40.0],
            },
            {
                "lap": 2,
                "driver": "TestDriver1",
                "car_index": 0,
                "time": 122.0,
                "sectors": [41.0, 41.0, 40.0],
            },
            {
                "lap": 3,
                "driver": "TestDriver1",
                "car_index": 0,
                "time": 121.5,
                "sectors": [40.5, 41.0, 40.0],
            },
            {
                "lap": 4,
                "driver": "TestDriver1",
                "car_index": 0,
                "time": 123.0,
                "sectors": [41.5, 41.0, 40.5],
            },
            {
                "lap": 1,
                "driver": "TestDriver2",
                "car_index": 1,
                "time": 125.0,
                "sectors": [42.0, 42.0, 41.0],
            },
            {
                "lap": 2,
                "driver": "TestDriver2",
                "car_index": 1,
                "time": 124.0,
                "sectors": [41.5, 42.0, 40.5],
            },
        ]

        for lap_data in test_laps:
            Lap.objects.create(
                session=self.session,
                lap_number=lap_data["lap"],
                driver_name=lap_data["driver"],
                car_index=lap_data["car_index"],
                total_time=lap_data["time"],
                sectors=lap_data["sectors"],
                tyre_compound="M",
            )

    def test_consistency_calculation_accuracy(self):
        """Test that consistency calculation is accurate"""
        calculator = SessionStatisticsCalculator(self.session)
        driver_stats = calculator.calculate_driver_statistics()

        # Manually calculate consistency for TestDriver1
        driver1_times = [122.0, 121.5, 123.0, 120.0]  # Including existing lap
        driver1_times.sort()
        # Remove two worst laps (123.0, 122.0)
        filtered_times = driver1_times[:-2]  # [120.0, 121.5]

        if len(filtered_times) > 1:
            avg = sum(filtered_times) / len(filtered_times)
            variance = sum((x - avg) ** 2 for x in filtered_times) / len(filtered_times)
            expected_consistency = variance**0.5

            calculated_consistency = driver_stats["TestDriver1"]["consistency"]
            self.assertAlmostEqual(
                calculated_consistency, expected_consistency, places=3
            )

    def test_optimal_lap_accuracy(self):
        """Test optimal lap time calculation accuracy"""
        calculator = SessionStatisticsCalculator(self.session)
        driver_stats = calculator.calculate_driver_statistics()

        # For TestDriver1, best sectors should be:
        # Sector 0: min(41.0, 40.5, 41.5, 40.0) = 40.0
        # Sector 1: min(41.0, 41.0, 41.0, 41.0) = 41.0
        # Sector 2: min(40.0, 40.0, 40.5, 40.0) = 40.0
        # Total optimal: 40.0 + 41.0 + 40.0 = 121.0

        expected_optimal = 121.0
        calculated_optimal = driver_stats["TestDriver1"]["optimal_lap_time"]
        self.assertAlmostEqual(calculated_optimal, expected_optimal, places=3)
