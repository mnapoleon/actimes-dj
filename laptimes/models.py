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
    
    class Meta:
        ordering = ['-upload_date']
    
    def __str__(self):
        if self.session_name:
            return f"{self.session_name} - {self.track} - {self.car}"
        return f"{self.track} - {self.car} ({self.session_type})"
    
    def get_fastest_lap(self):
        """Get the fastest lap in this session"""
        return self.laps.order_by('total_time').first()
    
    def get_drivers(self):
        """Get list of unique drivers in this session"""
        return self.laps.values_list('driver_name', flat=True).distinct()


class Lap(models.Model):
    """Model representing an individual lap"""
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name='laps'
    )
    lap_number = models.IntegerField()
    driver_name = models.CharField(max_length=200)
    car_index = models.IntegerField()  # Index in the original players array
    total_time = models.FloatField()  # Total lap time in seconds
    sectors = models.JSONField(default=list)  # List of sector times in seconds
    tyre_compound = models.CharField(max_length=50)
    cuts = models.IntegerField(default=0)  # Number of track limit violations
    
    class Meta:
        ordering = ['session', 'lap_number']
        unique_together = ['session', 'lap_number', 'car_index']
    
    def __str__(self):
        return (f"Lap {self.lap_number} - {self.driver_name} "
                f"({self.format_time()})")
    
    def format_time(self):
        """Format lap time as MM:SS.mmm"""
        minutes = int(self.total_time // 60)
        seconds = self.total_time % 60
        return f"{minutes}:{seconds:06.3f}"
    
    def get_sector_times(self):
        """Return sector times as a list"""
        return list(self.sectors) if self.sectors else []

# NOTE: After this change, you must create and run a migration, and update all code that creates or accesses Lap sector times.
