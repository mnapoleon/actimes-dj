from django.contrib import admin

from .models import Lap, Session


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = [
        "track",
        "car",
        "session_type",
        "upload_date",
        "lap_count",
        "file_hash_short",
    ]
    list_filter = ["session_type", "track", "car", "upload_date"]
    search_fields = ["track", "car", "file_name", "file_hash"]
    readonly_fields = ["upload_date", "file_hash", "file_hash_display"]
    fieldsets = [
        (
            "Session Information",
            {"fields": ["session_name", "track", "car", "session_type"]},
        ),
        (
            "File Information",
            {"fields": ["file_name", "upload_date", "file_hash_display"]},
        ),
        ("Player Data", {"fields": ["players_data"], "classes": ["collapse"]}),
    ]

    def lap_count(self, obj):
        return obj.laps.count()

    lap_count.short_description = "Laps"

    def file_hash_short(self, obj):
        """Display shortened file hash for list view"""
        if obj.file_hash:
            return f"{obj.file_hash[:8]}..."
        return "No hash"

    file_hash_short.short_description = "File Hash"

    def file_hash_display(self, obj):
        """Display full file hash with copy functionality"""
        if obj.file_hash:
            return f"{obj.file_hash} (Click to copy)"
        return "No hash available (uploaded before duplicate prevention)"

    file_hash_display.short_description = "File Hash (Full)"


@admin.register(Lap)
class LapAdmin(admin.ModelAdmin):
    list_display = [
        "session",
        "lap_number",
        "driver_name",
        "format_time",
        "tyre_compound",
        "cuts",
    ]
    list_filter = ["session__track", "driver_name", "tyre_compound"]
    search_fields = ["driver_name", "session__track", "session__car"]
    list_select_related = ["session"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("session")
