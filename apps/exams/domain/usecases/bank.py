from uuid import UUID

from apps.accounts.domain.capabilities import MANAGE_QUESTION_BANK, PREPARE_QUESTIONS
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.errors import NotFound, RuleViolation
from apps.core.domain.usecase import UseCase
from apps.teachers.domain.repositories import AllotmentRepository

from ..entities import Question, QuestionType, QuestionUnit
from ..repositories import QuestionRepository, UnitRepository
from ..services import BankScope


class _UnitUseCase(UseCase):
    def __init__(self, units: UnitRepository, authorizer: Authorizer):
        self._units = units
        self._authorizer = authorizer

    def _own_unit(self, actor: UserAccount, unit_id: UUID) -> QuestionUnit:
        """The unit if it is the actor's own; someone else's looks the same as missing."""
        unit = self._units.get(unit_id)
        if unit is None or not unit.is_active or unit.teacher_id != actor.id:
            raise NotFound("This unit was not found.")
        return unit

    def _ensure_free(self, unit: QuestionUnit) -> None:
        twin = self._units.find_same(unit.teacher_id, unit.class_id, unit.subject, unit.name)
        if twin is not None and twin.id != unit.id:
            message = f"You already have a unit named {unit.name} for this class and subject."
            raise RuleViolation(message, errors={"name": [message]})


class ListUnits(_UnitUseCase):
    def __init__(self, units: UnitRepository, scope: BankScope, authorizer: Authorizer):
        super().__init__(units, authorizer)
        self._scope = scope

    def call(self, actor: UserAccount, *, teacher_id: UUID | None = None,
             class_id: UUID | None = None, subject: str | None = None) -> list[QuestionUnit]:
        teacher_id = self._scope.narrow(actor, teacher_id)
        return self._units.list(teacher_id=teacher_id, class_id=class_id, subject=subject)


class AddUnit(_UnitUseCase):
    """A teacher starts a unit for a class and subject they take."""

    def __init__(self, units: UnitRepository, allotments: AllotmentRepository,
                 authorizer: Authorizer):
        super().__init__(units, authorizer)
        self._allotments = allotments

    def call(self, actor: UserAccount, *, class_id: UUID, subject: str,
             name: str) -> QuestionUnit:
        self._authorizer.require(actor, MANAGE_QUESTION_BANK)
        holder = self._allotments.find_active(class_id, subject.strip())
        if holder is None or holder.teacher_id != actor.id:
            message = "You do not take this subject in this class."
            raise RuleViolation(message, errors={"subject": [message]})
        unit = QuestionUnit.create(teacher_id=actor.id, class_id=class_id,
                                   subject=holder.subject, name=name)
        self._ensure_free(unit)
        return self._units.add(unit)


class RenameUnit(_UnitUseCase):
    def call(self, actor: UserAccount, unit_id: UUID, *, name: str) -> QuestionUnit:
        self._authorizer.require(actor, MANAGE_QUESTION_BANK)
        unit = self._own_unit(actor, unit_id)
        unit.rename(name)
        self._ensure_free(unit)
        return self._units.update(unit)


class RemoveUnit(_UnitUseCase):
    """Hides the unit and its questions. Papers already made keep their copies."""

    def call(self, actor: UserAccount, unit_id: UUID) -> None:
        self._authorizer.require(actor, MANAGE_QUESTION_BANK)
        unit = self._own_unit(actor, unit_id)
        unit.remove()
        self._units.update(unit)


class _QuestionUseCase(_UnitUseCase):
    def __init__(self, units: UnitRepository, questions: QuestionRepository,
                 authorizer: Authorizer):
        super().__init__(units, authorizer)
        self._questions = questions

    def _own_question(self, actor: UserAccount, question_id: UUID) -> Question:
        question = self._questions.get(question_id)
        if question is None or not question.is_active:
            raise NotFound("This question was not found.")
        self._own_unit(actor, question.unit_id)
        return question


class ListQuestions(_QuestionUseCase):
    """The questions of a unit: its owner, or whoever can read every bank."""

    def __init__(self, units: UnitRepository, questions: QuestionRepository,
                 scope: BankScope, authorizer: Authorizer):
        super().__init__(units, questions, authorizer)
        self._scope = scope

    def call(self, actor: UserAccount, unit_id: UUID) -> list[Question]:
        unit = self._units.get(unit_id)
        if unit is None or not unit.is_active:
            raise NotFound("This unit was not found.")
        if unit.teacher_id != actor.id and not self._scope.sees_all(actor):
            raise NotFound("This unit was not found.")
        if unit.teacher_id == actor.id:
            self._authorizer.require_any(actor, MANAGE_QUESTION_BANK, PREPARE_QUESTIONS)
        return self._questions.list(unit_id)


class AddQuestion(_QuestionUseCase):
    def call(self, actor: UserAccount, unit_id: UUID, *, text: str, marks: int,
             question_type: QuestionType) -> Question:
        self._authorizer.require(actor, PREPARE_QUESTIONS)
        self._own_unit(actor, unit_id)
        return self._questions.add(
            Question.create(unit_id=unit_id, text=text, marks=marks, question_type=question_type)
        )


class UpdateQuestion(_QuestionUseCase):
    """`changes` holds only what to change, from text, marks and question_type."""

    ALLOWED = {"text", "marks", "question_type"}

    def call(self, actor: UserAccount, question_id: UUID, **changes) -> Question:
        self._authorizer.require(actor, PREPARE_QUESTIONS)
        if not changes or not set(changes) <= self.ALLOWED:
            raise RuleViolation("Nothing to change.")
        question = self._own_question(actor, question_id)
        question.change(
            text=changes.get("text", question.text), marks=changes.get("marks", question.marks),
            question_type=changes.get("question_type", question.question_type),
        )
        return self._questions.update(question)


class RemoveQuestion(_QuestionUseCase):
    def call(self, actor: UserAccount, question_id: UUID) -> None:
        self._authorizer.require(actor, PREPARE_QUESTIONS)
        question = self._own_question(actor, question_id)
        question.remove()
        self._questions.update(question)
