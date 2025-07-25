import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import DeleteView, FormView, ListView, UpdateView

from .forms import JSONUploadForm, SessionEditForm
from .models import Lap, Session


class HomeView(FormView):
    """Main view for uploading JSON files and displaying sessions"""

    template_name = "laptimes/home.html"
    form_class = JSONUploadForm
    success_url = reverse_lazy("home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sessions"] = Session.objects.all().order_by("track")[
            :10
        ]  # Latest 10 sessions sorted by track
        return context

    def _extract_session_type(self, data, session_data):
        """Extract session type from __quickDrive or fallback to type field"""
        session_type = "Practice"  # Default

        # First try to extract from __quickDrive
        if "__quickDrive" in data:
            session_type = self._parse_quick_drive_mode(data["__quickDrive"])

        # Fall back to type field if __quickDrive parsing didn't work
        if session_type == "Practice" and "type" in session_data:
            # Map session type numbers to names
            type_map = {1: "Practice", 2: "Qualifying", 3: "Race"}
            session_type = type_map.get(session_data["type"], "Practice")

        return session_type

    def _parse_quick_drive_mode(self, quick_drive_str):
        """Parse the __quickDrive JSON string to extract mode"""
        try:
            quick_drive_data = json.loads(quick_drive_str)
            if "Mode" not in quick_drive_data:
                return "Practice"

            mode_path = quick_drive_data["Mode"]
            # Extract last node from path like
            # "/Pages/Drive/QuickDrive_Trackday.xaml"
            if "/" not in mode_path:
                return "Practice"

            # Get "QuickDrive_Trackday.xaml"
            last_part = mode_path.split("/")[-1]
            if last_part.endswith(".xaml"):
                last_part = last_part[:-5]  # Remove ".xaml"

            if last_part.startswith("QuickDrive_"):
                # Remove "QuickDrive_" prefix
                return last_part[11:]
            else:
                return last_part

        except (json.JSONDecodeError, KeyError):
            return "Practice"

    def form_valid(self, form):
        """Process uploaded JSON file and create Session/Lap objects"""
        json_file = form.cleaned_data["json_file"]
        try:
            # Parse JSON content
            content = json_file.read().decode("utf-8")
            data = json.loads(content)

            # Get the first session data
            session_data = data["sessions"][0]

            # Extract session type using helper method
            session_type = self._extract_session_type(data, session_data)

            # Get car model from the first player (assuming all use same car)
            car_model = "Unknown"
            if data["players"] and len(data["players"]) > 0:
                car_model = data["players"][0].get("car", "Unknown")

            # Use the file upload time as the default upload_date
            from django.utils import timezone

            upload_date = timezone.now()

            # Create Session object
            session = Session.objects.create(
                track=data["track"],
                car=car_model,
                session_type=session_type,
                file_name=json_file.name,
                players_data=data["players"],
                upload_date=upload_date,
                file_hash=getattr(json_file, "_file_hash", None),
            )

            # Create Lap objects from session laps
            for lap_data in session_data["laps"]:
                # Get driver name from car index
                car_index = lap_data.get("car", 0)
                driver_name = "Unknown"
                if car_index < len(data["players"]):
                    driver_name = data["players"][car_index].get("name", "Unknown")

                # Extract sector times (convert from milliseconds to seconds)
                sectors_raw = lap_data.get("sectors", [])
                sectors = [(s / 1000.0) for s in sectors_raw]

                Lap.objects.create(
                    session=session,
                    lap_number=lap_data.get("lap", 0),
                    driver_name=driver_name,
                    car_index=car_index,
                    total_time=lap_data.get("time", 0) / 1000.0,  # ms to sec
                    sectors=sectors,
                    tyre_compound=lap_data.get("tyre", "Unknown"),
                    cuts=lap_data.get("cuts", 0),
                )

            messages.success(self.request, f"Successfully uploaded session: {session}")

        except Exception as e:
            messages.error(self.request, f"Error processing file: {str(e)}")

        return super().form_valid(form)


class SessionDetailView(ListView):
    """View for displaying detailed lap times for a specific session"""

    model = Lap
    template_name = "laptimes/session_detail.html"
    context_object_name = "laps"
    paginate_by = 50

    def get_queryset(self):
        self.session = get_object_or_404(Session, pk=self.kwargs["pk"])
        queryset = Lap.objects.filter(session=self.session)

        # Apply driver filter if specified
        driver_filter = self.request.GET.get("driver")
        if driver_filter and driver_filter != "all":
            queryset = queryset.filter(driver_name=driver_filter)

        # Apply sorting
        sort_by = self.request.GET.get("sort", "driver_name")
        if sort_by.startswith("sector") and sort_by.endswith("_time"):
            try:
                sector_idx = int(sort_by.replace("sector", "").replace("_time", "")) - 1
                laps = list(queryset)
                laps.sort(
                    key=lambda lap: (
                        lap.sectors[sector_idx]
                        if len(lap.sectors) > sector_idx
                        else float("inf")
                    )
                )
                return laps
            except Exception:
                pass  # fallback to default
        elif sort_by in ["lap_number", "total_time", "driver_name"]:
            queryset = queryset.order_by(sort_by)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["session"] = self.session

        # Get all laps for the session (for chart)
        all_laps = self.session.laps.all().order_by("lap_number")
        context["all_laps"] = all_laps

        # Get unique drivers from the session
        context["drivers"] = list(
            self.session.laps.values_list("driver_name", flat=True)
            .distinct()
            .order_by("driver_name")
        )

        # Add driver lap counts for enhanced display
        driver_lap_counts = {}
        for driver in context["drivers"]:
            driver_lap_counts[driver] = all_laps.filter(driver_name=driver).count()
        context["driver_lap_counts"] = driver_lap_counts

        # Get unique lap numbers for chart labels (excluding lap 0)
        unique_lap_numbers = list(
            all_laps.filter(lap_number__gt=0)
            .values_list("lap_number", flat=True)
            .distinct()
            .order_by("lap_number")
        )
        context["unique_lap_numbers"] = unique_lap_numbers

        # Prepare chart data for each driver
        chart_data = {}
        for driver in context["drivers"]:
            chart_data[driver] = {}
            for lap_number in unique_lap_numbers:
                try:
                    lap = all_laps.get(driver_name=driver, lap_number=lap_number)
                    chart_data[driver][lap_number] = lap.total_time
                except Lap.DoesNotExist:
                    chart_data[driver][lap_number] = None
        context["chart_data"] = chart_data
        context["fastest_lap"] = self.session.get_fastest_lap()

        # Determine the maximum number of sectors in any lap for this session
        max_sectors = 0
        for lap in all_laps:
            if hasattr(lap, "sectors") and lap.sectors:
                max_sectors = max(max_sectors, len(lap.sectors))
        context["sector_count"] = max_sectors if max_sectors > 0 else 3

        # For each lap in the current page, build a sectors list
        for lap in context["laps"]:
            if hasattr(lap, "sectors") and lap.sectors:
                lap.sectors = list(lap.sectors)
            else:
                lap.sectors = []

        # Row-level highlighting for total time (fastest, slowest, pb)
        laps = context["laps"]
        if laps:
            context["fastest_total"] = min(lap.total_time for lap in all_laps)
            context["slowest_total"] = max(lap.total_time for lap in all_laps)
            # Personal best per driver
            driver_pb_total = {}
            for driver in context["drivers"]:
                driver_laps = [lap for lap in all_laps if lap.driver_name == driver]
                if driver_laps:
                    driver_pb_total[driver] = min(lap.total_time for lap in driver_laps)
            for lap in laps:
                lap.is_pb_total = (
                    driver_pb_total.get(lap.driver_name) is not None
                    and lap.total_time == driver_pb_total[lap.driver_name]
                )

        # Calculate sector highlights: fastest, slowest, and pb per driver
        sector_highlights = {}
        # Fastest and slowest overall for each sector
        for idx in range(context["sector_count"]):
            sector_times = [
                lap.sectors[idx] for lap in all_laps if len(lap.sectors) > idx
            ]
            if sector_times:
                sector_highlights[idx] = {
                    "fastest": min(sector_times),
                    "slowest": max(sector_times),
                    "pb": None,  # Will be set per lap below
                }

        # Personal best per driver for each sector
        # Build a dict: {driver: {sector_idx: pb_time}}
        driver_pb = {driver: {} for driver in context["drivers"]}
        for driver in context["drivers"]:
            driver_laps = [lap for lap in all_laps if lap.driver_name == driver]
            for idx in range(context["sector_count"]):
                sector_times = [
                    lap.sectors[idx] for lap in driver_laps if len(lap.sectors) > idx
                ]
                if sector_times:
                    driver_pb[driver][idx] = min(sector_times)

        # Attach per-lap sector highlight info for template
        for lap in context["laps"]:
            lap.sector_highlights = {}
            for idx in range(context["sector_count"]):
                lap.sector_highlights[idx] = {
                    "fastest": (
                        sector_highlights[idx]["fastest"]
                        if idx in sector_highlights
                        else None
                    ),
                    "slowest": (
                        sector_highlights[idx]["slowest"]
                        if idx in sector_highlights
                        else None
                    ),
                    "pb": driver_pb.get(lap.driver_name, {}).get(idx),
                }

        context["sector_highlights"] = sector_highlights
        return context


class SessionEditView(UpdateView):
    """View for editing session information"""

    model = Session
    form_class = SessionEditForm
    template_name = "laptimes/session_edit.html"
    context_object_name = "session"

    def get_success_url(self):
        messages.success(self.request, f'Session "{self.object}" updated successfully!')
        return reverse("session_detail", kwargs={"pk": self.object.pk})


class SessionDeleteView(DeleteView):
    """View for deleting sessions"""

    model = Session
    template_name = "laptimes/session_confirm_delete.html"
    context_object_name = "session"
    success_url = reverse_lazy("home")

    def delete(self, request, *args, **kwargs):
        session = self.get_object()
        messages.success(request, f'Session "{session}" has been deleted successfully.')
        return super().delete(request, *args, **kwargs)


def session_data_api(_request, pk):
    """API endpoint to get session data as JSON"""
    session = get_object_or_404(Session, pk=pk)
    laps = session.laps.all()

    data = {
        "session": {
            "id": session.id,
            "track": session.track,
            "car": session.car,
            "session_type": session.session_type,
        },
        "laps": [
            {
                "lap": lap.lap_number,
                "driver": lap.driver_name,
                "total_time": lap.total_time,
                "sectors": lap.get_sector_times(),
                "tyre": lap.tyre_compound,
                "cuts": lap.cuts,
            }
            for lap in laps
        ],
    }

    return JsonResponse(data)


@require_POST
def delete_driver_from_session(request, session_pk, driver_name):
    """Delete a specific driver and all their laps from a session"""
    session = get_object_or_404(Session, pk=session_pk)

    # Get the count of laps to be deleted for the message
    laps_to_delete = session.laps.filter(driver_name=driver_name)
    lap_count = laps_to_delete.count()

    if lap_count == 0:
        messages.warning(
            request, f'No laps found for driver "{driver_name}" in this session.'
        )
    else:
        # Delete all laps for this driver in this session
        laps_to_delete.delete()
        messages.success(
            request,
            f'Successfully deleted {lap_count} lap(s) for driver "{driver_name}".',
        )

    return redirect("session_detail", pk=session_pk)
