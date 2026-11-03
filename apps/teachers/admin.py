from django.contrib import admin

from .models import Allotment, Lesson


@admin.register(Allotment)
class AllotmentAdmin(admin.ModelAdmin):
    list_display = ("teacher", "school_class", "subject", "is_active")
    list_filter = ("is_active",)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    """A record to read; lessons are written by teachers through the API."""

    list_display = ("taught_on", "allotment", "subject", "topic")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
