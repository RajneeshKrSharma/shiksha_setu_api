from __future__ import annotations

from uuid import UUID

from django.db.models import Q

from ..domain.entities import PermissionGrant, Role, UserAccount
from ..domain.repositories import GrantRepository, UserRepository
from .models import PermissionGrant as GrantRow
from .models import User


class UserMapper:
    def to_entity(self, row: User) -> UserAccount:
        return UserAccount(
            id=row.pk,
            name=row.name,
            email=row.email,
            is_active=row.is_active,
            role=Role(row.role) if row.role else None,
            joined_on=row.joined_on,
        )


class DjangoUserRepository(UserRepository):
    def __init__(self, mapper: UserMapper | None = None):
        self._mapper = mapper or UserMapper()

    def get(self, entity_id: UUID) -> UserAccount | None:
        row = User.objects.filter(pk=entity_id).first()
        return self._mapper.to_entity(row) if row else None

    def get_by_email(self, email: str) -> UserAccount | None:
        row = User.objects.filter(email__iexact=email.strip()).first()
        return self._mapper.to_entity(row) if row else None

    def add(self, account: UserAccount, password: str | None = None) -> UserAccount:
        row = User.objects.create_user(
            account.email,
            password,
            name=account.name,
            role=account.role.value if account.role else "",
            is_active=account.is_active,
        )
        return self._mapper.to_entity(row)

    def update(self, account: UserAccount) -> UserAccount:
        row = User.objects.get(pk=account.id)
        row.name = account.name
        row.is_active = account.is_active
        row.save(update_fields=["name", "is_active", "updated_at"])
        return self._mapper.to_entity(row)

    def list(self, *, role: Role, query: str = "", active: bool | None = None) -> list[UserAccount]:
        found = User.objects.filter(role=role.value)
        if active is not None:
            found = found.filter(is_active=active)
        if query:
            found = found.filter(Q(name__icontains=query) | Q(email__icontains=query))
        return [self._mapper.to_entity(row) for row in found.order_by("name")]

    def has_role(self, role: Role) -> bool:
        return User.objects.filter(role=role.value).exists()

    def check_password(self, user_id: UUID, password: str) -> bool:
        return User.objects.get(pk=user_id).check_password(password)

    def set_password(self, user_id: UUID, password: str) -> None:
        row = User.objects.get(pk=user_id)
        row.set_password(password)
        row.save(update_fields=["password", "updated_at"])


class DjangoGrantRepository(GrantRepository):
    def get(self, entity_id: UUID) -> PermissionGrant | None:
        row = GrantRow.objects.filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def add(self, grant: PermissionGrant) -> PermissionGrant:
        row = GrantRow.objects.create(
            user_id=grant.user_id,
            capability=grant.capability,
            reason=grant.reason,
            granted_by_id=grant.granted_by_id,
        )
        return self._entity(row)

    def update(self, grant: PermissionGrant) -> PermissionGrant:
        row = GrantRow.objects.get(pk=grant.id)
        row.is_active = grant.is_active
        row.save(update_fields=["is_active", "updated_at"])
        return self._entity(row)

    def list(self, *, user_id: UUID | None = None,
             active_only: bool = True) -> list[PermissionGrant]:
        rows = GrantRow.objects.all()
        if user_id is not None:
            rows = rows.filter(user_id=user_id)
        if active_only:
            rows = rows.filter(is_active=True)
        return [self._entity(row) for row in rows]

    def find_active(self, user_id: UUID, capability: str) -> PermissionGrant | None:
        row = GrantRow.objects.filter(
            user_id=user_id, capability=capability, is_active=True
        ).first()
        return self._entity(row) if row else None

    def _entity(self, row: GrantRow) -> PermissionGrant:
        return PermissionGrant(
            id=row.pk,
            user_id=row.user_id,
            capability=row.capability,
            reason=row.reason,
            granted_by_id=row.granted_by_id,
            is_active=row.is_active,
            created_at=row.created_at,
        )
