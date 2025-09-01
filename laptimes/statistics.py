"""
Session statistics calculation module.

This module contains all the logic for calculating pre-computed statistics
that were previously calculated on-demand in views and models.
"""

from django.db.models import Max
from .models import Lap


class SessionStatisticsCalculator:
    """
    Calculator for session statistics that can be pre-computed during ingestion
    and stored in the database for performance optimization.
    """
    
    def __init__(self, session):
        self.session = session
    
    def calculate_all_statistics(self):
        """Calculate and return all statistics for the session"""
        return {
            'session_statistics': self.calculate_driver_statistics(),
            'chart_data': self.calculate_chart_data(),
            'sector_statistics': self.calculate_sector_statistics(),
            'fastest_lap_time': self.calculate_fastest_lap_time(),
            'fastest_lap_driver': self.calculate_fastest_lap_driver(),
            'total_laps': self.calculate_total_laps(),
            'total_drivers': self.calculate_total_drivers(),
        }
    
    def calculate_driver_statistics(self):
        """
        Calculate comprehensive driver statistics.
        Extracted from Session.get_driver_statistics()
        """
        stats = {}
        drivers = self.session.laps.values_list("driver_name", flat=True).distinct()

        for driver_name in drivers:
            # Get all laps for total count display
            all_driver_laps = self.session.laps.filter(driver_name=driver_name)
            # Get only racing laps for performance calculations
            driver_racing_laps = self.session.laps.filter(
                driver_name=driver_name, lap_number__gt=0
            )
            racing_lap_times = [lap.total_time for lap in driver_racing_laps]

            # Use all laps count for display, but racing laps for calculations
            if not racing_lap_times:
                # If no racing laps, skip this driver or use all laps as fallback
                if not all_driver_laps.exists():
                    continue
                # Fallback to all laps if only out laps exist
                lap_times = [lap.total_time for lap in all_driver_laps]
                racing_lap_times = lap_times

            # Calculate basic statistics using racing laps only
            best_lap_time = min(racing_lap_times)
            avg_lap_time = sum(racing_lap_times) / len(racing_lap_times)

            # Calculate consistency (standard deviation) - drop two worst laps
            if len(racing_lap_times) > 3:
                # Sort lap times and drop the two worst (highest) times
                sorted_times = sorted(racing_lap_times)
                filtered_times = sorted_times[:-2]  # Remove two worst laps
                filtered_avg = sum(filtered_times) / len(filtered_times)
                variance = sum((x - filtered_avg) ** 2 for x in filtered_times) / len(
                    filtered_times
                )
                consistency = variance**0.5
            elif len(racing_lap_times) > 1:
                # If 3 or fewer laps, use all racing laps for consistency
                variance = sum((x - avg_lap_time) ** 2 for x in racing_lap_times) / len(
                    racing_lap_times
                )
                consistency = variance**0.5
            else:
                consistency = 0.0

            # Get optimal lap time
            optimal_lap_time = self.calculate_optimal_lap_time(driver_name)

            stats[driver_name] = {
                "best_lap_time": best_lap_time,
                "optimal_lap_time": optimal_lap_time,
                "lap_count": all_driver_laps.count(),
                "racing_lap_count": len(racing_lap_times),
                "avg_lap_time": avg_lap_time,
                "consistency": consistency,
                "visible": True,  # Default visibility state
            }

        return stats

    def calculate_optimal_lap_time(self, driver_name):
        """
        Calculate optimal lap time (sum of best sectors) for a driver - exclude out laps.
        Extracted from Session.get_optimal_lap_time()
        """
        driver_laps = self.session.laps.filter(driver_name=driver_name, lap_number__gt=0)
        if not driver_laps.exists():
            return None

        # Get all sector times for this driver
        sector_count = 0
        for lap in driver_laps:
            if lap.sectors and len(lap.sectors) > sector_count:
                sector_count = len(lap.sectors)

        if sector_count == 0:
            return None

        # Find best time for each sector
        best_sectors = []
        for sector_idx in range(sector_count):
            sector_times = []
            for lap in driver_laps:
                if lap.sectors and len(lap.sectors) > sector_idx:
                    sector_times.append(lap.sectors[sector_idx])

            if sector_times:
                best_sectors.append(min(sector_times))

        return sum(best_sectors) if best_sectors else None

    def calculate_chart_data(self):
        """
        Calculate chart data for lap time visualization.
        Extracted from SessionDetailView chart data logic
        """
        all_laps = self.session.laps.all().order_by("lap_number")
        drivers = self.session.laps.values_list("driver_name", flat=True).distinct()
        
        unique_lap_numbers = list(
            all_laps.values_list("lap_number", flat=True)
            .distinct()
            .order_by("lap_number")
        )

        # Prepare chart data for each driver
        chart_data = {}
        for driver in drivers:
            chart_data[driver] = {}
            for lap_number in unique_lap_numbers:
                try:
                    lap = all_laps.get(driver_name=driver, lap_number=lap_number)
                    chart_data[driver][lap_number] = lap.total_time
                except Lap.DoesNotExist:
                    chart_data[driver][lap_number] = None
        
        return chart_data

    def calculate_sector_statistics(self):
        """
        Calculate sector statistics including highlights and personal bests.
        Extracted from SessionDetailView sector highlighting logic
        """
        all_laps = self.session.laps.all().order_by("lap_number")
        drivers = self.session.laps.values_list("driver_name", flat=True).distinct()
        
        # Determine the maximum number of sectors
        max_sectors = 0
        for lap in all_laps:
            if hasattr(lap, "sectors") and lap.sectors:
                max_sectors = max(max_sectors, len(lap.sectors))
        sector_count = max_sectors if max_sectors > 0 else 3

        # Calculate sector highlights: fastest, slowest, and pb per driver - exclude out laps
        sector_highlights = {}
        racing_laps = [lap for lap in all_laps if lap.lap_number > 0]
        
        # Fastest and slowest overall for each sector - exclude out laps
        for idx in range(sector_count):
            racing_sector_times = [
                lap.sectors[idx]
                for lap in racing_laps
                if len(lap.sectors) > idx
            ]
            if racing_sector_times:
                sector_highlights[idx] = {
                    "fastest": min(racing_sector_times),
                    "slowest": max(racing_sector_times),
                }
            else:
                # Fallback if no racing laps (only out laps)
                all_sector_times = [
                    lap.sectors[idx] for lap in all_laps if len(lap.sectors) > idx
                ]
                if all_sector_times:
                    sector_highlights[idx] = {
                        "fastest": min(all_sector_times),
                        "slowest": max(all_sector_times),
                    }

        # Personal best per driver for each sector - exclude out laps
        driver_pb_sectors = {driver: {} for driver in drivers}
        for driver in drivers:
            driver_racing_laps = [
                lap
                for lap in racing_laps
                if lap.driver_name == driver
            ]
            for idx in range(sector_count):
                racing_sector_times = [
                    lap.sectors[idx]
                    for lap in driver_racing_laps
                    if len(lap.sectors) > idx
                ]
                if racing_sector_times:
                    driver_pb_sectors[driver][idx] = min(racing_sector_times)

        # Calculate lap highlights
        if racing_laps:
            fastest_total = min(lap.total_time for lap in racing_laps)
            slowest_total = max(lap.total_time for lap in racing_laps)
        else:
            # Fallback if no racing laps (only out laps)
            fastest_total = min(lap.total_time for lap in all_laps) if all_laps else None
            slowest_total = max(lap.total_time for lap in all_laps) if all_laps else None

        # Personal best per driver - exclude out laps
        driver_pb_total = {}
        for driver in drivers:
            driver_racing_laps = [
                lap
                for lap in racing_laps
                if lap.driver_name == driver
            ]
            if driver_racing_laps:
                driver_pb_total[driver] = min(
                    lap.total_time for lap in driver_racing_laps
                )

        return {
            "sector_highlights": sector_highlights,
            "driver_pb_sectors": driver_pb_sectors,
            "lap_highlights": {
                "fastest_total": fastest_total,
                "slowest_total": slowest_total,
                "driver_pb_total": driver_pb_total,
            },
            "sector_count": sector_count,
        }

    def calculate_fastest_lap_time(self):
        """Calculate the fastest lap time in the session (excluding out laps)"""
        fastest_lap = self.session.laps.filter(lap_number__gt=0).order_by('total_time').first()
        return fastest_lap.total_time if fastest_lap else None

    def calculate_fastest_lap_driver(self):
        """Calculate the driver with the fastest lap time (excluding out laps)"""
        fastest_lap = self.session.laps.filter(lap_number__gt=0).order_by('total_time').first()
        return fastest_lap.driver_name if fastest_lap else ""

    def calculate_total_laps(self):
        """Calculate total number of laps in the session"""
        return self.session.laps.count()

    def calculate_total_drivers(self):
        """Calculate total number of unique drivers in the session"""
        return self.session.laps.values_list('driver_name', flat=True).distinct().count()