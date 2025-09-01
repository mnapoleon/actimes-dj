from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.db import models

from laptimes.models import Session, Lap


class Command(BaseCommand):
    help = 'Recalculate pre-computed statistics for sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--session-id',
            type=int,
            help='Recalculate statistics for a specific session ID',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Recalculate statistics for all sessions',
        )
        parser.add_argument(
            '--outdated-only',
            action='store_true',
            help='Only recalculate statistics for sessions without pre-computed data',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        if options['session_id']:
            sessions = Session.objects.filter(id=options['session_id'])
        elif options['all']:
            sessions = Session.objects.all()
        elif options['outdated_only']:
            # Find sessions without pre-computed statistics
            sessions = Session.objects.filter(
                models.Q(session_statistics__isnull=True) |
                models.Q(session_statistics__exact={}) |
                models.Q(fastest_lap_time__isnull=True)
            )
        else:
            self.stdout.write(
                self.style.ERROR('Must specify --session-id, --all, or --outdated-only')
            )
            return

        if not sessions.exists():
            self.stdout.write(
                self.style.WARNING('No sessions found matching criteria.')
            )
            return

        total_sessions = sessions.count()
        self.stdout.write(
            f'Found {total_sessions} session(s) to process.'
        )

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No changes will be made')
            )
            for session in sessions:
                self.stdout.write(f'Would recalculate: {session}')
            return

        success_count = 0
        error_count = 0

        for i, session in enumerate(sessions, 1):
            try:
                with transaction.atomic():
                    self._calculate_session_statistics(session)
                    success_count += 1
                    
                self.stdout.write(
                    f'[{i}/{total_sessions}] ✓ Calculated statistics for: {session}'
                )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'[{i}/{total_sessions}] ✗ Failed to calculate statistics for {session}: {e}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Complete: {success_count} successful, {error_count} failed'
            )
        )

    def _calculate_session_statistics(self, session):
        """Calculate and store all session statistics"""
        # Calculate driver statistics
        session.session_statistics = self._calculate_driver_statistics(session)
        
        # Calculate chart data
        session.chart_data = self._calculate_chart_data(session)
        
        # Calculate sector statistics  
        session.sector_statistics = self._calculate_sector_statistics(session)
        
        # Calculate session-level stats
        fastest_lap = session.laps.filter(lap_number__gt=0).order_by('total_time').first()
        if fastest_lap:
            session.fastest_lap_time = fastest_lap.total_time
            session.fastest_lap_driver = fastest_lap.driver_name
        else:
            session.fastest_lap_time = None
            session.fastest_lap_driver = ""
        
        session.total_laps = session.laps.count()
        session.total_drivers = session.laps.values_list('driver_name', flat=True).distinct().count()
        
        session.save()

    def _calculate_driver_statistics(self, session):
        """Calculate driver statistics - extracted from Session.get_driver_statistics()"""
        stats = {}
        drivers = session.laps.values_list("driver_name", flat=True).distinct()

        for driver_name in drivers:
            # Get all laps for total count display
            all_driver_laps = session.laps.filter(driver_name=driver_name)
            # Get only racing laps for performance calculations
            driver_racing_laps = session.laps.filter(
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
            optimal_lap_time = self._calculate_optimal_lap_time(session, driver_name)

            stats[driver_name] = {
                "best_lap_time": best_lap_time,
                "optimal_lap_time": optimal_lap_time,
                "lap_count": all_driver_laps.count(),
                "racing_lap_count": len(racing_lap_times),
                "avg_lap_time": avg_lap_time,
                "consistency": consistency,
                "visible": True,
            }

        return stats

    def _calculate_optimal_lap_time(self, session, driver_name):
        """Calculate optimal lap time (sum of best sectors) for a driver - exclude out laps"""
        driver_laps = session.laps.filter(driver_name=driver_name, lap_number__gt=0)
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

    def _calculate_chart_data(self, session):
        """Calculate chart data - extracted from SessionDetailView"""
        all_laps = session.laps.all().order_by("lap_number")
        drivers = session.laps.values_list("driver_name", flat=True).distinct()
        
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

    def _calculate_sector_statistics(self, session):
        """Calculate sector statistics - extracted from SessionDetailView"""
        all_laps = session.laps.all().order_by("lap_number")
        drivers = session.laps.values_list("driver_name", flat=True).distinct()
        
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
            }
        }