from django.contrib import admin

from .models import StudentAttendance, WorkAttendance


class _Record(admin.ModelAdmin):
    """Attendance is read-only here: it changes only through the API, which keeps the audit trail."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StudentAttendance)
class StudentAttendanceAdmin(_Record):
    list_display = ("day", "student", "school_class", "status")
    list_filter = ("status", "day")


@admin.register(WorkAttendance)
class WorkAttendanceAdmin(_Record):
    list_display = ("day", "person", "checked_in_at", "checked_out_at", "status")
    list_filter = ("status", "day")
