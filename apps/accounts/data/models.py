import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.data.base_model import BaseModel

from ..domain.entities import Role


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("role", Role.TEACHER.value)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        # An administrator for the admin portal only: no school role.
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """The master list of people who can sign in. Identity and access only; what a
    person does at the school lives in their own module."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120)
    role = models.CharField(
        max_length=20, choices=[(r.value, r.label) for r in Role], blank=True
    )
    joined_on = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    # False blocks login immediately.
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} ({self.role or 'administrator'})"


class PermissionGrant(BaseModel):
    """A permission the Principal gave the Vice Principal, with the reason. Taking
    it back sets `is_active` to False; the row stays as the record."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="grants")
    capability = models.CharField(max_length=60)
    reason = models.CharField(max_length=300)
    granted_by = models.ForeignKey(
        User, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "capability"],
                condition=models.Q(is_active=True),
                name="one_active_grant_per_permission",
            )
        ]
