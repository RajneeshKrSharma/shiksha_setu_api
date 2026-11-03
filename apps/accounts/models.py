"""Django looks for models here; they live in data/models.py."""
from .data.models import PermissionGrant, User, UserManager  # noqa: F401
from .domain.entities import Role  # noqa: F401
