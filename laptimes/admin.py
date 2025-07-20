from django.contrib import admin
from .models import Session, Lap


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['track', 'car', 'session_type', 'upload_date', 'lap_count']
    list_filter = ['session_type', 'track', 'car', 'upload_date']
    search_fields = ['track', 'car', 'file_name']
    readonly_fields = ['upload_date']
    
    def lap_count(self, obj):
        return obj.laps.count()
    lap_count.short_description = 'Laps'


@admin.register(Lap)
class LapAdmin(admin.ModelAdmin):
    list_display = ['session', 'lap_number', 'driver_name', 
                   'format_time', 'tyre_compound', 'cuts']
    list_filter = ['session__track', 'driver_name', 'tyre_compound']
    search_fields = ['driver_name', 'session__track', 'session__car']
    list_select_related = ['session']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('session')
