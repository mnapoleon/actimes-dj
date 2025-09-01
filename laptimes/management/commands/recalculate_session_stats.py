from django.core.management.base import BaseCommand
from django.db import transaction
from django.db import models

from laptimes.models import Session
from laptimes.statistics import SessionStatisticsCalculator


class Command(BaseCommand):
    help = "Recalculate pre-computed statistics for sessions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--session-id",
            type=int,
            help="Recalculate statistics for a specific session ID",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Recalculate statistics for all sessions",
        )
        parser.add_argument(
            "--outdated-only",
            action="store_true",
            help="Only recalculate statistics for sessions without pre-computed data",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args, **options):
        if options["session_id"]:
            sessions = Session.objects.filter(id=options["session_id"])
        elif options["all"]:
            sessions = Session.objects.all()
        elif options["outdated_only"]:
            # Find sessions without pre-computed statistics
            sessions = Session.objects.filter(
                models.Q(session_statistics__isnull=True)
                | models.Q(session_statistics__exact={})
                | models.Q(fastest_lap_time__isnull=True)
            )
        else:
            self.stdout.write(
                self.style.ERROR("Must specify --session-id, --all, or --outdated-only")
            )
            return

        if not sessions.exists():
            self.stdout.write(
                self.style.WARNING("No sessions found matching criteria.")
            )
            return

        total_sessions = sessions.count()
        self.stdout.write(f"Found {total_sessions} session(s) to process.")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
            for session in sessions:
                self.stdout.write(f"Would recalculate: {session}")
            return

        success_count = 0
        error_count = 0

        for i, session in enumerate(sessions, 1):
            try:
                with transaction.atomic():
                    self._calculate_session_statistics(session)
                    success_count += 1

                self.stdout.write(
                    f"[{i}/{total_sessions}] ✓ Calculated statistics for: {session}"
                )

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"[{i}/{total_sessions}] ✗ Failed to calculate statistics for {session}: {e}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Complete: {success_count} successful, {error_count} failed"
            )
        )

    def _calculate_session_statistics(self, session):
        """Calculate and store all session statistics using the dedicated calculator"""
        calculator = SessionStatisticsCalculator(session)
        stats = calculator.calculate_all_statistics()

        # Update session with calculated statistics
        session.session_statistics = stats["session_statistics"]
        session.chart_data = stats["chart_data"]
        session.sector_statistics = stats["sector_statistics"]
        session.fastest_lap_time = stats["fastest_lap_time"]
        session.fastest_lap_driver = stats["fastest_lap_driver"]
        session.total_laps = stats["total_laps"]
        session.total_drivers = stats["total_drivers"]

        session.save()
