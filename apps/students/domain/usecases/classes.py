from uuid import UUID

from apps.accounts.domain.capabilities import MANAGE_CLASSES, MANAGE_STUDENTS, VIEW_STUDENTS
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import NotFound, RuleViolation
from apps.core.domain.usecase import UseCase

from ..entities import ClassLevel, SchoolClass
from ..ports import ClassAccess
from ..repositories import ClassRepository, StudentRepository

_READERS = (VIEW_STUDENTS, MANAGE_STUDENTS, MANAGE_CLASSES)


class _ClassUseCase(UseCase):
    def __init__(self, classes: ClassRepository, authorizer: Authorizer):
        self._classes = classes
        self._authorizer = authorizer

    def _existing(self, class_id: UUID) -> SchoolClass:
        school_class = self._classes.get(class_id)
        if school_class is None:
            raise NotFound("This class was not found.")
        return school_class

    def _ensure_free(self, candidate: SchoolClass) -> None:
        twin = self._classes.find_active(candidate.level, candidate.section)
        if twin is not None and twin.id != candidate.id:
            message = f"Class {candidate.name} already exists."
            raise RuleViolation(message, errors={"section": [message]})


class ListClasses(_ClassUseCase):
    """Everyone who manages classes sees all; a teacher sees the classes they are allotted."""

    def __init__(self, classes: ClassRepository, authorizer: Authorizer, access: ClassAccess):
        super().__init__(classes, authorizer)
        self._access = access

    def call(self, actor: UserAccount, *, active: bool | None = True) -> list[SchoolClass]:
        self._authorizer.require_any(actor, *_READERS)
        visible = self._access.visible_class_ids(actor)
        found = self._classes.list(active=active)
        return found if visible is None else [c for c in found if c.id in visible]


class GetClass(_ClassUseCase):
    def __init__(self, classes: ClassRepository, authorizer: Authorizer, access: ClassAccess):
        super().__init__(classes, authorizer)
        self._access = access

    def call(self, actor: UserAccount, class_id: UUID) -> SchoolClass:
        self._authorizer.require_any(actor, *_READERS)
        visible = self._access.visible_class_ids(actor)
        if visible is not None and class_id not in visible:
            raise NotFound("This class was not found.")
        return self._existing(class_id)


class _ClassWriter(_ClassUseCase):
    def __init__(self, classes: ClassRepository, authorizer: Authorizer, audit: AuditLogger):
        super().__init__(classes, authorizer)
        self._audit = audit


class AddClass(_ClassWriter):
    def call(self, actor: UserAccount, *, level: ClassLevel, section: str = "") -> SchoolClass:
        self._authorizer.require(actor, MANAGE_CLASSES)
        school_class = SchoolClass.create(level=level, section=section)
        self._ensure_free(school_class)
        saved = self._classes.add(school_class)
        self._audit.record(actor.id, "class_added", f"class:{saved.id}", {"name": saved.name})
        return saved


class UpdateClass(_ClassWriter):
    def call(self, actor: UserAccount, class_id: UUID, *, level: ClassLevel | None = None,
             section: str | None = None) -> SchoolClass:
        self._authorizer.require(actor, MANAGE_CLASSES)
        school_class = self._existing(class_id)
        school_class.reshape(
            level=school_class.level if level is None else level,
            section=school_class.section if section is None else section,
        )
        self._ensure_free(school_class)
        saved = self._classes.update(school_class)
        self._audit.record(actor.id, "class_updated", f"class:{saved.id}", {"name": saved.name})
        return saved


class RemoveClass(_ClassWriter):
    """A class that still has students cannot be removed."""

    def __init__(self, classes: ClassRepository, students: StudentRepository,
                 authorizer: Authorizer, audit: AuditLogger):
        super().__init__(classes, authorizer, audit)
        self._students = students

    def call(self, actor: UserAccount, class_id: UUID) -> None:
        self._authorizer.require(actor, MANAGE_CLASSES)
        school_class = self._existing(class_id)
        if self._students.count_active_in_class(class_id) > 0:
            raise RuleViolation("This class has students. Move or remove them first.")
        school_class.remove()
        self._classes.update(school_class)
        self._audit.record(actor.id, "class_removed", f"class:{class_id}",
                           {"name": school_class.name})
