"""CRUD written once for every kind of member. A kind that needs more (a teacher
also gets a login) subclasses the use case and overrides only that step."""
from typing import Generic
from uuid import UUID

from ..entity import Person
from ..errors import NotFound
from ..repository import MemberRepository, P
from ..usecase import UseCase


class _MemberUseCase(UseCase, Generic[P]):
    def __init__(self, members: MemberRepository[P]):
        self._members = members

    def _existing(self, member_id: UUID) -> P:
        member = self._members.get(member_id)
        if member is None:
            raise NotFound("This person was not found.")
        return member


class AddMember(_MemberUseCase[P]):
    def call(self, member: P) -> P:
        return self._members.add(member)


class GetMember(_MemberUseCase[P]):
    def call(self, member_id: UUID) -> P:
        return self._existing(member_id)


class ListMembers(_MemberUseCase[P]):
    def call(self, *, query: str = "", active: bool | None = None) -> list[P]:
        return self._members.list(query=query.strip(), active=active)


class UpdateMember(_MemberUseCase[P]):
    def call(self, member: P) -> P:
        self._existing(member.id)
        return self._members.update(member)


class DeactivateMember(_MemberUseCase[P]):
    """Delete means inactive: the person and their history stay."""

    def call(self, member_id: UUID) -> Person:
        member = self._existing(member_id)
        member.deactivate()
        return self._members.update(member)
