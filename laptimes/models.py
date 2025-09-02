import warnings

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone


class Track(models.Model):
    """Model representing a racing track"""

    code = models.CharField(
        max_length=200, unique=True, help_text="Track name as imported from JSON files"
    )
    display_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Human-readable track name for display",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_name", "code"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["display_name"]),
        ]

    def __str__(self):
        return self.display_name if self.display_name else self.code

    def get_display_name(self):
        """Get the display name, falling back to code if display_name is empty"""
        return self.display_name if self.display_name else self.code


class Car(models.Model):
    """Model representing a racing car"""

    code = models.CharField(
        max_length=200, unique=True, help_text="Car name as imported from JSON files"
    )
    display_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Human-readable car name for display",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_name", "code"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["display_name"]),
        ]

    def __str__(self):
        return self.display_name if self.display_name else self.code

    def get_display_name(self):
        """Get the display name, falling back to code if display_name is empty"""
        return self.display_name if self.display_name else self.code


class Session(models.Model):
    """Model representing a racing session"""

    session_name = models.CharField(max_length=200, blank=True)
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="sessions")
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="sessions")
    # e.g., 'Practice', 'Qualifying', 'Race'
    session_type = models.CharField(max_length=50)
    upload_date = models.DateTimeField(default=timezone.now)
    file_name = models.CharField(max_length=255)
    players_data = models.JSONField(default=dict)  # Store player information
    file_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)

    # Pre-computed session statistics for performance optimization
    fastest_lap_time = models.FloatField(null=True, blank=True)
    fastest_lap_driver = models.CharField(max_length=200, blank=True)
    total_laps = models.IntegerField(default=0)
    total_drivers = models.IntegerField(default=0)
    session_statistics = models.JSONField(default=dict)  # Driver statistics
    chart_data = models.JSONField(default=dict)  # Pre-computed chart data
    sector_statistics = models.JSONField(default=dict)  # Sector highlights
    last_calculated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-upload_date"]
        indexes = [
            models.Index(fields=["file_hash"]),
            models.Index(fields=["-upload_date"]),  # For pagination ordering
            models.Index(fields=["track"]),  # For filtering/searching by track
            models.Index(fields=["car"]),  # For filtering/searching by car
            models.Index(fields=["session_type"]),  # For session type filtering
            models.Index(
                fields=["track", "-upload_date"]
            ),  # Compound index for track + date
            models.Index(
                fields=["car", "-upload_date"]
            ),  # Compound index for car + date
            models.Index(
                fields=["session_type", "-upload_date"]
            ),  # Compound index for session type + date
            models.Index(fields=["last_calculated"]),  # For recalculation queries
        ]

    def __str__(self):
        track_name = self.track.get_display_name() if self.track else "Unknown Track"
        car_name = self.car.get_display_name() if self.car else "Unknown Car"
        if self.session_name:
            return f"{self.session_name} - {track_name} - {car_name}"
        return f"{track_name} - {car_name} ({self.session_type})"

    def get_fastest_lap(self):
        """
        Get the fastest lap in this session - exclude out laps
        DEPRECATED: Use pre-computed fastest_lap_time and fastest_lap_driver fields instead
        """
        warnings.warn(
            "Session.get_fastest_lap() is deprecated. Use pre-computed fastest_lap_time and fastest_lap_driver fields instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.laps.filter(lap_number__gt=0).order_by("total_time").first()

    def get_drivers(self):
        """Get list of unique drivers in this session"""
        return self.laps.values_list("driver_name", flat=True).distinct()

    def get_optimal_lap_time(self, driver_name):
        """
        Calculate optimal lap time (sum of best sectors) for a driver - exclude out laps
        DEPRECATED: Use pre-computed session_statistics field instead
        """
        warnings.warn(
            "Session.get_optimal_lap_time() is deprecated. Use pre-computed session_statistics field instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Try to use pre-computed data first
        if self.session_statistics and driver_name in self.session_statistics:
            return self.session_statistics[driver_name].get("optimal_lap_time")

        # Fallback to calculation
        driver_laps = self.laps.filter(driver_name=driver_name, lap_number__gt=0)
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
        """
        Calculate comprehensive statistics for each driver - exclude out laps
        DEPRECATED: Use pre-computed session_statistics field instead
        """
        warnings.warn(
            "Session.get_driver_statistics() is deprecated. Use pre-computed session_statistics field instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Try to use pre-computed data first
        if self.session_statistics:
            return self.session_statistics
        stats = {}

        for driver_name in self.get_drivers():
            # Get all laps for total count display
            all_driver_laps = self.laps.filter(driver_name=driver_name)
            # Get only racing laps for performance calculations
            driver_racing_laps = self.laps.filter(
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

            # Get optimal lap time (already excludes out laps)
            optimal_lap_time = self.get_optimal_lap_time(driver_name)

            stats[driver_name] = {
                "best_lap_time": best_lap_time,
                "optimal_lap_time": optimal_lap_time,
                "lap_count": all_driver_laps.count(),  # Show total lap count including out laps
                "racing_lap_count": len(racing_lap_times),  # Count of racing laps only
                "avg_lap_time": avg_lap_time,
                "consistency": consistency,
                "visible": True,  # Default visibility state
            }

        return stats

    def is_statistics_current(self):
        """Check if pre-computed statistics are current"""
        if not self.last_calculated:
            return False

        # Check if any laps have been modified after last calculation
        latest_lap_update = self.laps.aggregate(
            latest=models.Max("id")  # Use id as proxy for creation time
        )["latest"]

        return latest_lap_update is not None

    def get_or_calculate_driver_statistics(self):
        """Get driver statistics, using pre-computed if available, otherwise calculate"""
        if self.session_statistics and self.is_statistics_current():
            return self.session_statistics
        return self.get_driver_statistics()

    def invalidate_statistics(self):
        """Mark statistics as needing recalculation"""
        self.session_statistics = {}
        self.chart_data = {}
        self.sector_statistics = {}
        self.fastest_lap_time = None
        self.fastest_lap_driver = ""
        self.total_laps = 0
        self.total_drivers = 0
        self.save(
            update_fields=[
                "session_statistics",
                "chart_data",
                "sector_statistics",
                "fastest_lap_time",
                "fastest_lap_driver",
                "total_laps",
                "total_drivers",
                "last_calculated",
            ]
        )

    def clean(self):
        """Validate model fields"""
        super().clean()

        # Validate fastest_lap_time is positive
        if self.fastest_lap_time is not None and self.fastest_lap_time <= 0:
            raise ValidationError("Fastest lap time must be positive")

        # Validate total_laps and total_drivers are non-negative
        if self.total_laps < 0:
            raise ValidationError("Total laps cannot be negative")
        if self.total_drivers < 0:
            raise ValidationError("Total drivers cannot be negative")

        # Validate JSON field structures
        if self.session_statistics and not isinstance(self.session_statistics, dict):
            raise ValidationError("Session statistics must be a dictionary")

        if self.chart_data and not isinstance(self.chart_data, dict):
            raise ValidationError("Chart data must be a dictionary")

        if self.sector_statistics and not isinstance(self.sector_statistics, dict):
            raise ValidationError("Sector statistics must be a dictionary")

    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.clean()
        super().save(*args, **kwargs)


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


@receiver(post_delete, sender=Lap)
def invalidate_session_statistics_on_lap_delete(sender, instance, **kwargs):
    """Invalidate pre-computed statistics when a lap is deleted"""
    if instance.session_id:
        try:
            session = Session.objects.get(pk=instance.session_id)
            session.invalidate_statistics()
        except Session.DoesNotExist:
            pass  # Session was already deleted


@receiver(post_save, sender=Lap)
def invalidate_session_statistics_on_lap_change(sender, instance, **kwargs):
    """Invalidate pre-computed statistics when a lap is modified"""
    if instance.session_id and not kwargs.get("created", False):
        # Only invalidate on updates, not on creation (creation handled in upload process)
        try:
            session = Session.objects.get(pk=instance.session_id)
            session.invalidate_statistics()
        except Session.DoesNotExist:
            pass
