from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from apps.core.domain.entity import Entity, Person
from apps.core.domain.errors import RuleViolation


class Role(StrEnum):
    PRINCIPAL = "principal"
    VICE_PRINCIPAL = "vice_principal"
    TEACHER = "teacher"
    STAFF = "staff"

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()


@dataclass(eq=False, kw_only=True)
class UserAccount(Person):
    """Someone who can sign in. `role` is None for an administrator of the admin
    portal, who has no part in running the school."""

    role: Role | None = None
    joined_on: datetime | None = None

    @classmethod
    def register(cls, *, name: str, email: str, role: Role) -> "UserAccount":
        email = email.strip().lower()
        if not email:
            raise RuleViolation("Email is required.", errors={"email": ["Email is required."]})
        account = cls(name="-", email=email, role=role)
        account.rename(name)
        return account


@dataclass(eq=False, kw_only=True)
class PermissionGrant(Entity):
    """One permission the Principal gave the Vice Principal, and why."""

    REASON_MAX = 300

    user_id: UUID
    capability: str
    reason: str
    granted_by_id: UUID | None = None
    is_active: bool = True
    created_at: datetime | None = None

    @classmethod
    def issue(cls, *, user_id: UUID, capability: str, reason: str,
              granted_by_id: UUID) -> "PermissionGrant":
        reason = reason.strip()
        if not reason or len(reason) > cls.REASON_MAX:
            message = f"A reason is required, up to {cls.REASON_MAX} characters."
            raise RuleViolation(message, errors={"reason": [message]})
        return cls(user_id=user_id, capability=capability, reason=reason,
                   granted_by_id=granted_by_id)

    def revoke(self) -> None:
        self.is_active = False
