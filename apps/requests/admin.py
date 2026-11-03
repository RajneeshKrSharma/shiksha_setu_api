from django.contrib import admin

from .models import Request


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    """Requests are read-only here: they change only through the API, where each decision
    is recorded."""

    list_display = ("created_at", "kind", "requester", "status")
    list_filter = ("kind", "status")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
