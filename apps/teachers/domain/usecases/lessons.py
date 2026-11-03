from datetime import date
from uuid import UUID

from apps.accounts.domain.capabilities import RECORD_DAILY_LESSON
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.clock import Clock
from apps.core.domain.errors import Forbidden, NotFound, RuleViolation
from apps.core.domain.usecase import UseCase

from ..entities import Lesson, LessonStatus
from ..repositories import AllotmentRepository, LessonRepository
from ..services import TeachingScope


class RecordLesson(UseCase):
    """The teacher says what they taught today in one of their own classes and subjects."""

    def __init__(self, allotments: AllotmentRepository, lessons: LessonRepository,
                 authorizer: Authorizer, clock: Clock):
        self._allotments = allotments
        self._lessons = lessons
        self._authorizer = authorizer
        self._clock = clock

    def call(self, actor: UserAccount, *, allotment_id: UUID, topic: str,
             taught_on: date | None = None) -> Lesson:
        self._authorizer.require(actor, RECORD_DAILY_LESSON)
        allotment = self._allotments.get(allotment_id)
        if allotment is None or not allotment.is_active:
            raise NotFound("This class and subject was not found.")
        if allotment.teacher_id != actor.id:
            raise Forbidden("This class and subject is not yours.")

        today = self._clock.today()
        lesson = Lesson.record(allotment=allotment, taught_on=taught_on or today,
                               topic=topic, today=today)
        if self._lessons.find(allotment_id, lesson.taught_on) is not None:
            raise RuleViolation("This day's lesson is already recorded. Change it instead.")
        return self._lessons.add(lesson)


class ReviseLesson(UseCase):
    def __init__(self, lessons: LessonRepository, authorizer: Authorizer):
        self._lessons = lessons
        self._authorizer = authorizer

    def call(self, actor: UserAccount, lesson_id: UUID, *, topic: str) -> Lesson:
        self._authorizer.require(actor, RECORD_DAILY_LESSON)
        lesson = self._lessons.get(lesson_id)
        if lesson is None:
            raise NotFound("This lesson was not found.")
        if lesson.teacher_id != actor.id:
            raise Forbidden("This lesson is not yours.")
        lesson.revise(topic)
        return self._lessons.update(lesson)


class ListLessons(UseCase):
    """A teacher gets their own lessons; the Principal can ask for any teacher or class."""

    def __init__(self, lessons: LessonRepository, scope: TeachingScope):
        self._lessons = lessons
        self._scope = scope

    def call(self, actor: UserAccount, *, teacher_id: UUID | None = None,
             class_id: UUID | None = None, from_date: date | None = None,
             to_date: date | None = None) -> list[Lesson]:
        teacher_id = self._scope.narrow(actor, teacher_id)
        return self._lessons.list(teacher_id=teacher_id, class_id=class_id,
                                  from_date=from_date, to_date=to_date)


class LessonBoard(UseCase):
    """For the Principal: for one day, every active allotment and whether its lesson was
    recorded. Teachers who can no longer sign in are left out."""

    def __init__(self, allotments: AllotmentRepository, lessons: LessonRepository,
                 scope: TeachingScope, clock: Clock):
        self._allotments = allotments
        self._lessons = lessons
        self._scope = scope
        self._clock = clock

    def call(self, actor: UserAccount, *, day: date | None = None) -> list[LessonStatus]:
        if not self._scope.sees_all(actor):
            raise Forbidden()
        recorded = self._lessons.on_day(day or self._clock.today())
        return [
            LessonStatus(allotment, recorded.get(allotment.id))
            for allotment in self._allotments.list(teacher_active=True)
        ]
