from django.contrib import admin

from .models import Car, Lap, Session, Track


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ["code", "display_name", "session_count", "created_at", "updated_at"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["code", "display_name"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["display_name", "code"]

    def session_count(self, obj):
        return obj.sessions.count()

    session_count.short_description = "Sessions"


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ["code", "display_name", "session_count", "created_at", "updated_at"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["code", "display_name"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["display_name", "code"]

    def session_count(self, obj):
        return obj.sessions.count()

    session_count.short_description = "Sessions"


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
    search_fields = [
        "track__code",
        "track__display_name",
        "car__code",
        "car__display_name",
        "file_name",
        "file_hash",
    ]
    list_select_related = ["track", "car"]
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
    list_filter = ["session__track", "session__car", "driver_name", "tyre_compound"]
    search_fields = [
        "driver_name",
        "session__track__code",
        "session__track__display_name",
        "session__car__code",
        "session__car__display_name",
    ]
    list_select_related = ["session"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("session", "session__track", "session__car")
        )
