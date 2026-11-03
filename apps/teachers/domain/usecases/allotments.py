from uuid import UUID

from apps.accounts.domain.capabilities import ALLOT_CLASSES, MANAGE_TEACHERS, RECORD_DAILY_LESSON
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.repositories import UserRepository
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import NotFound, RuleViolation
from apps.core.domain.usecase import UseCase
from apps.students.domain.repositories import ClassRepository

from ..entities import Allotment
from ..repositories import AllotmentRepository
from ..services import TeachingScope


class ListAllotments(UseCase):
    """A teacher gets their own allotments; the Principal can ask for any teacher or class."""

    def __init__(self, allotments: AllotmentRepository, scope: TeachingScope):
        self._allotments = allotments
        self._scope = scope

    def call(self, actor: UserAccount, *, teacher_id: UUID | None = None,
             class_id: UUID | None = None) -> list[Allotment]:
        teacher_id = self._scope.narrow(actor, teacher_id)
        return self._allotments.list(teacher_id=teacher_id, class_id=class_id)


class AllotClass(UseCase):
    """Gives a teacher a class and subject. Anyone who can record lessons can be allotted,
    which includes the Principal, who also teaches."""

    def __init__(self, allotments: AllotmentRepository, users: UserRepository,
                 classes: ClassRepository, authorizer: Authorizer, audit: AuditLogger):
        self._allotments = allotments
        self._users = users
        self._classes = classes
        self._authorizer = authorizer
        self._audit = audit

    def call(self, actor: UserAccount, *, teacher_id: UUID, class_id: UUID,
             subject: str) -> Allotment:
        self._authorizer.require(actor, ALLOT_CLASSES)
        teacher = self._users.get(teacher_id)
        if teacher is None or not teacher.is_active:
            raise NotFound("This teacher was not found.")
        if not self._authorizer.can(teacher, RECORD_DAILY_LESSON):
            raise RuleViolation("This person does not teach.",
                                errors={"teacher_id": ["Choose a teacher."]})
        school_class = self._classes.get(class_id)
        if school_class is None or not school_class.is_active:
            raise RuleViolation("This class does not exist.",
                                errors={"class_id": ["Choose an existing class."]})

        allotment = Allotment.allot(teacher_id=teacher_id, class_id=class_id, subject=subject)
        holder = self._allotments.find_active(class_id, allotment.subject)
        if holder is not None:
            message = (f"{school_class.name} {holder.subject} is already given to "
                       f"{holder.teacher_name}. Take it back first.")
            raise RuleViolation(message, errors={"subject": [message]})

        saved = self._allotments.add(allotment)
        self._audit.record(actor.id, "class_allotted", f"user:{teacher_id}", {
            "class": school_class.name, "subject": saved.subject,
        })
        return saved


class RemoveAllotment(UseCase):
    """Takes the class and subject back from the teacher. Lessons already recorded stay."""

    def __init__(self, allotments: AllotmentRepository, authorizer: Authorizer,
                 audit: AuditLogger):
        self._allotments = allotments
        self._authorizer = authorizer
        self._audit = audit

    def call(self, actor: UserAccount, allotment_id: UUID) -> None:
        self._authorizer.require(actor, ALLOT_CLASSES)
        allotment = self._allotments.get(allotment_id)
        if allotment is None or not allotment.is_active:
            raise NotFound("This allotment was not found.")
        allotment.remove()
        self._allotments.update(allotment)
        self._audit.record(actor.id, "allotment_removed", f"user:{allotment.teacher_id}", {
            "class": allotment.class_name, "subject": allotment.subject,
        })
