from uuid import UUID

from apps.accounts.domain.capabilities import (
    ALLOT_CLASSES,
    MANAGE_STUDENTS,
    MANAGE_CLASSES,
    MANAGE_TEACHERS,
    RECORD_DAILY_LESSON,
)
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.errors import Forbidden
from apps.students.domain.ports import ClassAccess

from .repositories import AllotmentRepository


class TeachingScope:
    """Who may see whose allotments and lessons: those who run the teachers (Principal,
    or a Vice Principal given the right) see everyone's; a teacher sees only their own."""

    def __init__(self, authorizer: Authorizer):
        self._authorizer = authorizer

    def sees_all(self, actor: UserAccount) -> bool:
        held = self._authorizer.capabilities_of(actor)
        return ALLOT_CLASSES in held or MANAGE_TEACHERS in held

    def narrow(self, actor: UserAccount, teacher_id: UUID | None) -> UUID | None:
        """The teacher to look at: whoever was asked for if the actor sees all, otherwise
        only the actor."""
        if self.sees_all(actor):
            return teacher_id
        self._authorizer.require(actor, RECORD_DAILY_LESSON)
        if teacher_id not in (None, actor.id):
            raise Forbidden()
        return actor.id


class AllotmentClassAccess(ClassAccess):
    """A teacher sees the classes they are allotted. Whoever manages classes or students
    sees all of them."""

    def __init__(self, authorizer: Authorizer, allotments: AllotmentRepository):
        self._authorizer = authorizer
        self._allotments = allotments

    def visible_class_ids(self, actor: UserAccount) -> frozenset[UUID] | None:
        held = self._authorizer.capabilities_of(actor)
        if MANAGE_STUDENTS in held or MANAGE_CLASSES in held:
            return None
        return frozenset(a.class_id for a in self._allotments.list(teacher_id=actor.id))
