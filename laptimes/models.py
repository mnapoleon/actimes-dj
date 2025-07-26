from django.db import models
from django.utils import timezone


class Session(models.Model):
    """Model representing a racing session"""

    session_name = models.CharField(max_length=200, blank=True)
    track = models.CharField(max_length=200)
    car = models.CharField(max_length=200)
    # e.g., 'Practice', 'Qualifying', 'Race'
    session_type = models.CharField(max_length=50)
    upload_date = models.DateTimeField(default=timezone.now)
    file_name = models.CharField(max_length=255)
    players_data = models.JSONField(default=dict)  # Store player information
    file_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        ordering = ["-upload_date"]
        indexes = [
            models.Index(fields=["file_hash"]),
        ]

    def __str__(self):
        if self.session_name:
            return f"{self.session_name} - {self.track} - {self.car}"
        return f"{self.track} - {self.car} ({self.session_type})"

    def get_fastest_lap(self):
        """Get the fastest lap in this session"""
        return self.laps.order_by("total_time").first()

    def get_drivers(self):
        """Get list of unique drivers in this session"""
        return self.laps.values_list("driver_name", flat=True).distinct()

    def get_optimal_lap_time(self, driver_name):
        """Calculate optimal lap time (sum of best sectors) for a driver"""
        driver_laps = self.laps.filter(driver_name=driver_name)
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

    def get_driver_statistics(self):
        """Calculate comprehensive statistics for each driver"""
        stats = {}

        for driver_name in self.get_drivers():
            driver_laps = self.laps.filter(driver_name=driver_name)
            lap_times = [lap.total_time for lap in driver_laps]

            if not lap_times:
                continue

            # Calculate basic statistics
            best_lap_time = min(lap_times)
            avg_lap_time = sum(lap_times) / len(lap_times)

            # Calculate consistency (standard deviation)
            if len(lap_times) > 1:
                variance = sum((x - avg_lap_time) ** 2 for x in lap_times) / len(lap_times)
                consistency = variance ** 0.5
            else:
                consistency = 0.0

            # Get optimal lap time
            optimal_lap_time = self.get_optimal_lap_time(driver_name)

            stats[driver_name] = {
                'best_lap_time': best_lap_time,
                'optimal_lap_time': optimal_lap_time,
                'lap_count': len(lap_times),
                'avg_lap_time': avg_lap_time,
                'consistency': consistency,
                'visible': True  # Default visibility state
            }

        return stats


class Lap(models.Model):
    """Model representing an individual lap"""

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="laps")
    lap_number = models.IntegerField()
    driver_name = models.CharField(max_length=200)
    car_index = models.IntegerField()  # Index in the original players array
    total_time = models.FloatField()  # Total lap time in seconds
    sectors = models.JSONField(default=list)  # List of sector times in seconds
    tyre_compound = models.CharField(max_length=50)
    cuts = models.IntegerField(default=0)  # Number of track limit violations

    class Meta:
        ordering = ["session", "lap_number"]
        unique_together = ["session", "lap_number", "car_index"]

    def __str__(self):
        return f"Lap {self.lap_number} - {self.driver_name} " f"({self.format_time()})"

    def format_time(self):
        """Format lap time as MM:SS.mmm"""
        minutes = int(self.total_time // 60)
        seconds = self.total_time % 60
        return f"{minutes}:{seconds:06.3f}"

    def get_sector_times(self):
        """Return sector times as a list"""
        return list(self.sectors) if self.sectors else []

    @staticmethod
    def format_time_static(time_seconds):
        """Static method to format time as MM:SS.mmm"""
        if time_seconds is None:
            return "N/A"
        minutes = int(time_seconds // 60)
        seconds = time_seconds % 60
        return f"{minutes}:{seconds:06.3f}"


# NOTE: After this change, you must create and run a migration, and update
# all code that creates or accesses Lap sector times.
