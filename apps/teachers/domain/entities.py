from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from apps.accounts.domain.entities import UserAccount
from apps.core.domain.entity import Entity, Person
from apps.core.domain.errors import RuleViolation


def _invalid(field: str, message: str) -> RuleViolation:
    return RuleViolation(message, errors={field: [message]})


@dataclass(eq=False, kw_only=True)
class Teacher(Person):
    """A teacher is a person who can sign in, so the id is the sign-in account's id."""

    @classmethod
    def from_account(cls, account: UserAccount) -> "Teacher":
        return cls(id=account.id, name=account.name, email=account.email,
                   is_active=account.is_active)


@dataclass(eq=False, kw_only=True)
class Allotment(Entity):
    """One class and subject a teacher takes, such as 5-A Maths."""

    SUBJECT_MAX = 60

    teacher_id: UUID
    class_id: UUID
    subject: str
    is_active: bool = True
    # Filled in when read, so the app can show them.
    teacher_name: str = ""
    class_name: str = ""

    @classmethod
    def allot(cls, *, teacher_id: UUID, class_id: UUID, subject: str) -> "Allotment":
        subject = subject.strip()
        if not subject or len(subject) > cls.SUBJECT_MAX:
            raise _invalid("subject", f"Required, up to {cls.SUBJECT_MAX} characters.")
        return cls(teacher_id=teacher_id, class_id=class_id, subject=subject)

    def remove(self) -> None:
        self.is_active = False


@dataclass(eq=False, kw_only=True)
class Lesson(Entity):
    """What a teacher taught in one class and subject on one day."""

    TOPIC_MAX = 500

    allotment_id: UUID
    teacher_id: UUID
    class_id: UUID
    subject: str
    taught_on: date
    topic: str
    recorded_at: datetime | None = None
    teacher_name: str = ""
    class_name: str = ""

    @classmethod
    def record(cls, *, allotment: Allotment, taught_on: date, topic: str, today: date) -> "Lesson":
        if taught_on > today:
            raise _invalid("taught_on", "A lesson cannot be recorded for a future day.")
        lesson = cls(allotment_id=allotment.id, teacher_id=allotment.teacher_id,
                     class_id=allotment.class_id, subject=allotment.subject,
                     taught_on=taught_on, topic="-")
        lesson.revise(topic)
        return lesson

    def revise(self, topic: str) -> None:
        topic = topic.strip()
        if not topic or len(topic) > self.TOPIC_MAX:
            raise _invalid("topic", f"Required, up to {self.TOPIC_MAX} characters.")
        self.topic = topic


@dataclass(frozen=True)
class LessonStatus:
    """One allotment's lesson for a day: recorded, or still pending."""

    allotment: Allotment
    lesson: Lesson | None

    @property
    def recorded(self) -> bool:
        return self.lesson is not None
