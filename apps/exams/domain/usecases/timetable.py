from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from uuid import UUID

from apps.accounts.domain.capabilities import SCHEDULE_EXAMS
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import RuleViolation
from apps.core.domain.usecase import UseCase
from apps.students.domain.repositories import ClassRepository
from apps.teachers.domain.repositories import AllotmentRepository

from ..entities import Exam, ExamSettings, ExamType, SameDayRule
from ..repositories import ExamRepository, ExamSettingsRepository, PaperRepository
from ..services import ExamLine, ExamScope


class GetExamSettings(UseCase):
    """The Principal reads how timetables are made in this school."""

    def __init__(self, settings: ExamSettingsRepository, authorizer: Authorizer):
        self._settings = settings
        self._authorizer = authorizer

    def call(self, actor: UserAccount) -> ExamSettings:
        self._authorizer.require(actor, SCHEDULE_EXAMS)
        return self._settings.get()


class UpdateExamSettings(UseCase):
    """The Principal changes any of the timetable settings; each value is checked."""

    def __init__(self, settings: ExamSettingsRepository, authorizer: Authorizer,
                 audit: AuditLogger):
        self._settings = settings
        self._authorizer = authorizer
        self._audit = audit

    def call(self, actor: UserAccount, **values) -> ExamSettings:
        self._authorizer.require(actor, SCHEDULE_EXAMS)
        settings = self._settings.get()
        settings.change(**values)
        saved = self._settings.save(settings)
        self._audit.record(actor.id, "exam_settings_updated", "exam_settings", {
            "same_day_rule": saved.same_day_rule.value, "min_gap_days": saved.min_gap_days,
        })
        return saved


@dataclass(frozen=True)
class TimetableEntry:
    """One subject's paper in a timetable. What is left empty falls back to the settings."""

    subject: str
    held_on: date
    max_marks: int | None = None
    starts_at: time | None = None
    duration_minutes: int | None = None


@dataclass(frozen=True)
class TimetableResult:
    lines: list[ExamLine]
    warnings: list[str]


class ScheduleTimetable(UseCase):
    """Saves a whole class's exam timetable at once: every paper is checked against the
    school's settings first, and either all are saved or none."""

    def __init__(self, exams: ExamRepository, papers: PaperRepository, scope: ExamScope,
                 settings: ExamSettingsRepository, authorizer: Authorizer,
                 classes: ClassRepository, allotments: AllotmentRepository,
                 audit: AuditLogger):
        self._exams = exams
        self._papers = papers
        self._scope = scope
        self._settings = settings
        self._authorizer = authorizer
        self._classes = classes
        self._allotments = allotments
        self._audit = audit

    def call(self, actor: UserAccount, *, exam_type: ExamType, class_id: UUID,
             entries: list[TimetableEntry]) -> TimetableResult:
        self._authorizer.require(actor, SCHEDULE_EXAMS)
        school_class = self._classes.get(class_id)
        if school_class is None or not school_class.is_active:
            raise RuleViolation("This class does not exist.",
                                errors={"class_id": ["Choose an existing class."]})
        if not entries:
            raise RuleViolation("Add at least one subject.",
                                errors={"entries": ["Add at least one subject."]})

        settings = self._settings.get()
        problems: list[str] = []
        exams = self._build(exam_type, class_id, entries, settings, problems)
        warnings = self._same_day(class_id, exams, settings, problems)
        self._gaps(exams, settings, problems)
        if problems:
            raise RuleViolation(
                f"The timetable was not saved: {len(problems)} problem(s) to fix.",
                errors={"entries": problems},
            )

        saved = self._exams.add_many(exams)
        self._audit.record(actor.id, "timetable_scheduled", f"class:{class_id}", {
            "class": school_class.name, "type": exam_type.value, "papers": len(saved),
        })
        return TimetableResult([self._scope.line(e, self._papers) for e in saved], warnings)

    def _build(self, exam_type: ExamType, class_id: UUID, entries: list[TimetableEntry],
               settings: ExamSettings, problems: list[str]) -> list[Exam]:
        exams: list[Exam] = []
        seen: set[str] = set()
        for entry in entries:
            name = entry.subject.strip()
            if name.lower() in seen:
                problems.append(f"{name}: listed twice.")
                continue
            seen.add(name.lower())
            if not name:
                problems.append("A subject has no name.")
                continue
            subject = name
            if settings.is_off_day(entry.held_on):
                problems.append(f"{subject}: {entry.held_on:%d %b %Y} is a holiday.")
                continue
            if self._exams.find_same(class_id, subject, exam_type, entry.held_on):
                problems.append(f"{subject}: already scheduled on that day.")
                continue
            try:
                exams.append(Exam.schedule(
                    exam_type=exam_type, class_id=class_id, subject=subject,
                    held_on=entry.held_on, max_marks=entry.max_marks or settings.default_max_marks,
                    starts_at=self._start(entry, settings),
                    duration_minutes=self._duration(entry, settings),
                ))
            except RuleViolation as error:
                problems.append(f"{subject}: {error.message}")
        return exams

    @staticmethod
    def _start(entry: TimetableEntry, settings: ExamSettings) -> time | None:
        if not settings.show_time:
            return None
        return entry.starts_at or settings.default_start_time

    @staticmethod
    def _duration(entry: TimetableEntry, settings: ExamSettings) -> int | None:
        if not settings.show_time:
            return None
        return entry.duration_minutes or settings.default_duration_minutes

    def _same_day(self, class_id: UUID, exams: list[Exam], settings: ExamSettings,
                  problems: list[str]) -> list[str]:
        if settings.same_day_rule is SameDayRule.ALLOW:
            return []
        already: dict[date, int] = {}
        for exam in self._exams.list(class_id=class_id):
            already[exam.held_on] = already.get(exam.held_on, 0) + 1
        added: dict[date, int] = {}
        for exam in exams:
            added[exam.held_on] = added.get(exam.held_on, 0) + 1
        warnings: list[str] = []
        for day in sorted(added):
            if already.get(day, 0) + added[day] < 2:
                continue
            message = f"{day:%d %b %Y}: this class has more than one paper on this day."
            (problems if settings.same_day_rule is SameDayRule.BLOCK else warnings).append(message)
        return warnings

    @staticmethod
    def _gaps(exams: list[Exam], settings: ExamSettings, problems: list[str]) -> None:
        if settings.min_gap_days <= 0:
            return
        days = sorted({e.held_on for e in exams})
        for earlier, later in zip(days, days[1:]):
            if (later - earlier).days - 1 < settings.min_gap_days:
                problems.append(
                    f"{earlier:%d %b} and {later:%d %b}: keep at least "
                    f"{settings.min_gap_days} free day(s) between papers."
                )
