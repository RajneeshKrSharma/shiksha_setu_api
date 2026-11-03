from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import (
    AdminPasswordChangeForm,
    AdminUserCreationForm,
    UserChangeForm,
)

from .models import PermissionGrant, User


class UserCreationForm(AdminUserCreationForm):
    """Add form: only who they are and how they sign in."""

    class Meta:
        model = User
        fields = ("email", "name", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Everyone signs in with a password, so there is no "no password" choice.
        self.fields["usable_password"].widget = forms.HiddenInput()
        self.fields["usable_password"].initial = "true"


class UserEditForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


class PasswordChangeForm(AdminPasswordChangeForm):
    """The page that sets a user's new password."""

    class Media:
        js = ("accounts/password_toggle.js",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserEditForm
    change_password_form = PasswordChangeForm
    change_user_password_template = "accounts/admin/change_password.html"
    ordering = ("name",)
    list_display = ("name", "email", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("name", "email")
    readonly_fields = ("joined_on",)

    class Media:
        # An eye button to show or hide what is typed in the password boxes.
        js = ("accounts/password_toggle.js",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("name", "role", "joined_on")}),
        ("Access", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "role", "usable_password", "password1", "password2"),
            },
        ),
    )


@admin.register(PermissionGrant)
class PermissionGrantAdmin(admin.ModelAdmin):
    """A record to read. Permissions are given and taken back through the API."""

    list_display = ("user", "capability", "reason", "is_active", "created_at")
    list_filter = ("is_active", "capability")
    readonly_fields = [f.name for f in PermissionGrant._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
