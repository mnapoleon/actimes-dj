import json

from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import (
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import JSONUploadForm, SessionEditForm
from .models import Lap, Session
from .statistics import SessionStatisticsCalculator


class HomeView(ListView):
    """Main view for uploading JSON files and displaying sessions with pagination"""

    model = Session
    template_name = "laptimes/home.html"
    context_object_name = "sessions"
    paginate_by = 20
    ordering = ["-upload_date"]

    def get_queryset(self):
        """Optimize queries with annotations and apply filters"""
        queryset = Session.objects.annotate(lap_count=Count("laps"))

        # Apply filters
        track = self.request.GET.get("track")
        if track and track != "all":
            queryset = queryset.filter(track=track)

        car = self.request.GET.get("car")
        if car and car != "all":
            queryset = queryset.filter(car=car)

        session_type = self.request.GET.get("session_type")
        if session_type and session_type != "all":
            queryset = queryset.filter(session_type=session_type)

        # Date range filtering
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")
        if date_from:
            queryset = queryset.filter(upload_date__gte=date_from)
        if date_to:
            # Add 23:59:59 to include the entire day
            from datetime import datetime, time

            from django.utils import timezone

            try:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
                date_to_end = timezone.make_aware(
                    datetime.combine(date_to_obj.date(), time.max)
                )
                queryset = queryset.filter(upload_date__lte=date_to_end)
            except ValueError:
                pass  # Invalid date format, ignore filter

        # Search functionality
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(session_name__icontains=search)
                | Q(track__icontains=search)
                | Q(car__icontains=search)
                | Q(laps__driver_name__icontains=search)
            ).distinct()

        # Sorting
        sort_by = self.request.GET.get("sort", "-upload_date")
        valid_sort_fields = [
            "upload_date",
            "-upload_date",
            "track",
            "-track",
            "car",
            "-car",
            "session_type",
            "-session_type",
            "lap_count",
            "-lap_count",
        ]
        if sort_by in valid_sort_fields:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by("-upload_date")

        return queryset

    def get_paginate_by(self, queryset):
        """Allow dynamic pagination based on URL parameter"""
        per_page = self.request.GET.get("per_page")
        if per_page in ["10", "20", "50", "100"]:
            return int(per_page)
        return self.paginate_by

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = JSONUploadForm()

        # Add current per_page value for the selector
        context["current_per_page"] = self.get_paginate_by(self.get_queryset())

        # Add per_page options
        context["per_page_options"] = [10, 20, 50, 100]

        # Add filter options
        context["tracks"] = (
            Session.objects.values_list("track", flat=True).distinct().order_by("track")
        )
        context["cars"] = (
            Session.objects.values_list("car", flat=True).distinct().order_by("car")
        )
        context["session_types"] = (
            Session.objects.values_list("session_type", flat=True)
            .distinct()
            .order_by("session_type")
        )

        # Current filter values
        context["current_filters"] = {
            "track": self.request.GET.get("track", "all"),
            "car": self.request.GET.get("car", "all"),
            "session_type": self.request.GET.get("session_type", "all"),
            "date_from": self.request.GET.get("date_from", ""),
            "date_to": self.request.GET.get("date_to", ""),
            "search": self.request.GET.get("search", ""),
            "sort": self.request.GET.get("sort", "-upload_date"),
        }

        # Add filter count for display
        active_filters = sum(
            1
            for key, value in context["current_filters"].items()
            if value and value != "all" and value != "-upload_date"
        )
        context["active_filter_count"] = active_filters

        return context

    def post(self, request, *args, **kwargs):
        """Handle file upload while maintaining pagination"""
        form = JSONUploadForm(request.POST, request.FILES)
        if form.is_valid():
            return self._process_upload(form)
        else:
            # Form has errors, redisplay with errors
            self.object_list = self.get_queryset()
            context = self.get_context_data(**kwargs)
            context["form"] = form
            return self.render_to_response(context)

    def _process_upload(self, form):
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

            # Calculate and store pre-computed statistics for performance optimization
            self._calculate_session_statistics(session)

            messages.success(self.request, f"Successfully uploaded session: {session}")

        except Exception as e:
            messages.error(self.request, f"Error processing file: {str(e)}")

        return redirect("home")

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
    
    def _calculate_session_statistics(self, session):
        """Calculate and store pre-computed statistics during ingestion"""
        try:
            calculator = SessionStatisticsCalculator(session)
            stats = calculator.calculate_all_statistics()
            
            # Update session with calculated statistics
            session.session_statistics = stats['session_statistics']
            session.chart_data = stats['chart_data']
            session.sector_statistics = stats['sector_statistics']
            session.fastest_lap_time = stats['fastest_lap_time']
            session.fastest_lap_driver = stats['fastest_lap_driver']
            session.total_laps = stats['total_laps']
            session.total_drivers = stats['total_drivers']
            
            session.save()
            
        except Exception as e:
            # Log the error but don't fail the upload
            print(f"Warning: Failed to calculate statistics for session {session.id}: {e}")
            # Statistics will be calculated later via management command or on-demand


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

        # Use pre-computed statistics for optimal performance
        context["driver_statistics"] = self._get_driver_statistics()
        context["chart_data"] = self._get_chart_data()
        context["fastest_lap_time"] = self._get_fastest_lap_time()
        
        # Calculate best optimal time from pre-computed driver stats if needed
        if context["driver_statistics"]:
            optimal_times = [
                stats["optimal_lap_time"]
                for stats in context["driver_statistics"].values()
                if stats.get("optimal_lap_time") is not None
            ]
            context["best_optimal_time"] = min(optimal_times) if optimal_times else None
        else:
            context["best_optimal_time"] = None

        # Get basic session data that's still needed for templates
        all_laps = self.session.laps.all().order_by("lap_number")
        context["all_laps"] = all_laps
        
        # Drivers list from pre-computed statistics or fallback to database
        if context["driver_statistics"]:
            context["drivers"] = list(context["driver_statistics"].keys())
        else:
            context["drivers"] = list(
                self.session.laps.values_list("driver_name", flat=True)
                .distinct()
                .order_by("driver_name")
            )

        # Driver lap counts - use pre-computed data when available
        driver_lap_counts = {}
        for driver in context["drivers"]:
            if driver in context["driver_statistics"]:
                driver_lap_counts[driver] = context["driver_statistics"][driver]["lap_count"]
            else:
                # Fallback to database query
                driver_lap_counts[driver] = all_laps.filter(driver_name=driver).count()
        context["driver_lap_counts"] = driver_lap_counts

        # Chart data from pre-computed or fallback
        unique_lap_numbers = list(
            all_laps.values_list("lap_number", flat=True)
            .distinct()
            .order_by("lap_number")
        )
        context["unique_lap_numbers"] = unique_lap_numbers

        # Fastest lap info - use pre-computed or fallback to database
        fastest_lap_time = self._get_fastest_lap_time()
        fastest_lap_driver = self._get_fastest_lap_driver()
        
        if fastest_lap_time:
            # Create a mock fastest lap object for template compatibility
            context["fastest_lap"] = type('MockLap', (), {
                'total_time': fastest_lap_time,
                'driver_name': fastest_lap_driver,
                'format_time': lambda: self._format_time(fastest_lap_time)
            })()
        else:
            context["fastest_lap"] = None

        # Use pre-computed sector statistics for highlighting
        sector_stats = self._get_sector_statistics()
        context["sector_count"] = sector_stats.get("sector_count", 3)
        context["sector_highlights"] = sector_stats.get("sector_highlights", {})
        
        # Lap highlights from pre-computed data
        lap_highlights = sector_stats.get("lap_highlights", {})
        context["fastest_total"] = lap_highlights.get("fastest_total")
        context["slowest_total"] = lap_highlights.get("slowest_total")
        
        # For each lap in the current page, build a sectors list and attach highlighting
        laps = context["laps"]
        driver_pb_total = lap_highlights.get("driver_pb_total", {})
        driver_pb_sectors = sector_stats.get("driver_pb_sectors", {})
        
        for lap in laps:
            # Ensure sectors are a list
            if hasattr(lap, "sectors") and lap.sectors:
                lap.sectors = list(lap.sectors)
            else:
                lap.sectors = []

            # Attach personal best flag
            lap.is_pb_total = (
                lap.driver_name in driver_pb_total
                and lap.total_time == driver_pb_total[lap.driver_name]
                and lap.lap_number > 0  # Only racing laps can be PB
            )

            # Attach sector highlight information
            lap.sector_highlights = {}
            for idx in range(context["sector_count"]):
                # Convert integer index to string for lookup
                idx_str = str(idx)
                lap.sector_highlights[idx] = {
                    "fastest": context["sector_highlights"].get(idx_str, {}).get("fastest"),
                    "slowest": context["sector_highlights"].get(idx_str, {}).get("slowest"),
                    "pb": driver_pb_sectors.get(lap.driver_name, {}).get(idx_str),
                }

        return context
    
    def _get_driver_statistics(self):
        """Get driver statistics using pre-computed data with fallback"""
        if self.session.session_statistics:
            return self.session.session_statistics
        
        # Fallback to on-demand calculation if pre-computed data not available
        return self.session.get_or_calculate_driver_statistics()
    
    def _get_chart_data(self):
        """Get chart data using pre-computed data with fallback"""
        if self.session.chart_data:
            return self.session.chart_data
        
        # Fallback to on-demand calculation
        from .statistics import SessionStatisticsCalculator
        calculator = SessionStatisticsCalculator(self.session)
        return calculator.calculate_chart_data()
    
    def _get_sector_statistics(self):
        """Get sector statistics using pre-computed data with fallback"""
        if self.session.sector_statistics:
            return self.session.sector_statistics
        
        # Fallback to on-demand calculation
        from .statistics import SessionStatisticsCalculator
        calculator = SessionStatisticsCalculator(self.session)
        return calculator.calculate_sector_statistics()
    
    def _get_fastest_lap_time(self):
        """Get fastest lap time using pre-computed data with fallback"""
        if self.session.fastest_lap_time:
            return self.session.fastest_lap_time
        
        # Fallback to database query
        fastest_lap = self.session.laps.filter(lap_number__gt=0).order_by('total_time').first()
        return fastest_lap.total_time if fastest_lap else None
    
    def _get_fastest_lap_driver(self):
        """Get fastest lap driver using pre-computed data with fallback"""
        if self.session.fastest_lap_driver:
            return self.session.fastest_lap_driver
        
        # Fallback to database query
        fastest_lap = self.session.laps.filter(lap_number__gt=0).order_by('total_time').first()
        return fastest_lap.driver_name if fastest_lap else ""
    
    def _format_time(self, time_seconds):
        """Format time as MM:SS.mmm for template compatibility"""
        if time_seconds is None:
            return "N/A"
        minutes = int(time_seconds // 60)
        seconds = time_seconds % 60
        return f"{minutes}:{seconds:06.3f}"


class SessionEditView(UpdateView):
    """View for editing session information"""

    model = Session
    form_class = SessionEditForm
    template_name = "laptimes/session_edit.html"
    context_object_name = "session"

    def get_success_url(self):
        messages.success(self.request, f'Session "{self.object}" updated successfully!')
        return reverse("session_detail", kwargs={"pk": self.object.pk})
    
    def form_valid(self, form):
        """Handle successful form submission"""
        response = super().form_valid(form)
        
        # Note: Session metadata editing (name, track, car, date) doesn't affect
        # lap-based statistics, so no recalculation is needed.
        # If we add editing of lap data in the future, we would recalculate here:
        # 
        # try:
        #     calculator = SessionStatisticsCalculator(self.object)
        #     stats = calculator.calculate_all_statistics()
        #     # Update session with recalculated statistics...
        # except Exception as e:
        #     messages.warning(self.request, f"Statistics recalculation failed: {e}")
        
        return response


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


class DriverDeleteView(TemplateView):
    """View for confirming driver deletion"""

    template_name = "laptimes/driver_confirm_delete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_pk = self.kwargs["session_pk"]
        driver_name = self.kwargs["driver_name"]

        context["session"] = get_object_or_404(Session, pk=session_pk)
        context["driver_name"] = driver_name

        # Get driver's laps for statistics
        driver_laps = context["session"].laps.filter(driver_name=driver_name)
        context["lap_count"] = driver_laps.count()
        context["driver_laps"] = driver_laps.order_by("lap_number")[
            :5
        ]  # Show first 5 laps

        return context

    def post(self, request, *args, **kwargs):
        """Handle the actual deletion"""
        session_pk = self.kwargs["session_pk"]
        driver_name = self.kwargs["driver_name"]

        session = get_object_or_404(Session, pk=session_pk)
        laps_to_delete = session.laps.filter(driver_name=driver_name)
        lap_count = laps_to_delete.count()

        if lap_count > 0:
            laps_to_delete.delete()
            
            # Explicitly recalculate statistics after driver deletion
            try:
                calculator = SessionStatisticsCalculator(session)
                stats = calculator.calculate_all_statistics()
                
                # Update session with recalculated statistics
                session.session_statistics = stats['session_statistics']
                session.chart_data = stats['chart_data']
                session.sector_statistics = stats['sector_statistics']
                session.fastest_lap_time = stats['fastest_lap_time']
                session.fastest_lap_driver = stats['fastest_lap_driver']
                session.total_laps = stats['total_laps']
                session.total_drivers = stats['total_drivers']
                session.save()
                
            except Exception as e:
                # Log error but don't fail the deletion
                print(f"Warning: Failed to recalculate statistics after driver deletion: {e}")
            
            messages.success(
                request,
                f'Successfully removed driver "{driver_name}" and all {lap_count} lap{"" if lap_count == 1 else "s"} from this session.',
            )
        else:
            messages.warning(
                request, f'No laps found for driver "{driver_name}" in this session.'
            )

        return redirect("session_detail", pk=session_pk)


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
            f'Successfully removed driver "{driver_name}" and all {lap_count} lap{"" if lap_count == 1 else "s"} from this session.',
        )

    return redirect("session_detail", pk=session_pk)


def driver_autocomplete(request):
    """API endpoint for driver name autocomplete"""
    term = request.GET.get("term", "")
    if len(term) < 2:  # Only search if at least 2 characters
        return JsonResponse([], safe=False)

    drivers = (
        Lap.objects.filter(driver_name__icontains=term)
        .values_list("driver_name", flat=True)
        .distinct()
        .order_by("driver_name")[:10]
    )

    return JsonResponse(list(drivers), safe=False)
