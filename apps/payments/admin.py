from django.contrib import admin

from .models import Payment, SalaryRate


class _Ledger(admin.ModelAdmin):
    """Money records are read-only here: they change only through the API, which keeps the
    audit trail."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(_Ledger):
    list_display = ("receipt_number", "person", "kind", "amount", "paid_on", "mode")
    list_filter = ("kind", "mode")


@admin.register(SalaryRate)
class SalaryRateAdmin(_Ledger):
    list_display = ("person", "effective_from", "amount")
