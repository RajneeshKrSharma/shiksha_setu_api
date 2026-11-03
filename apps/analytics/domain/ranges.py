from dataclasses import dataclass
from datetime import date, timedelta

from apps.core.domain.errors import RuleViolation


def _invalid(field: str, message: str) -> RuleViolation:
    return RuleViolation(message, errors={field: [message]})


@dataclass(frozen=True)
class DateRange:
    """The dates a graph covers, both days included. Left out, a graph covers the last 30
    days (daily graphs) or the last 6 months (monthly graphs), ending today."""

    start: date
    end: date

    @classmethod
    def daily(cls, start: date | None, end: date | None, *, today: date,
              default_days: int = 30, max_days: int = 92) -> "DateRange":
        end = end or today
        start = start or end - timedelta(days=default_days - 1)
        cls._check(start, end)
        if (end - start).days + 1 > max_days:
            raise _invalid("from", f"A daily graph covers up to {max_days} days.")
        return cls(start, end)

    @classmethod
    def monthly(cls, start: date | None, end: date | None, *, today: date,
                default_months: int = 6, max_months: int = 24) -> "DateRange":
        end = end or today
        start = start or cls._months_back(end, default_months - 1)
        cls._check(start, end)
        start = start.replace(day=1)
        count = (end.year - start.year) * 12 + end.month - start.month + 1
        if count > max_months:
            raise _invalid("from", f"A monthly graph covers up to {max_months} months.")
        return cls(start, end)

    def days(self, *, up_to: date | None = None) -> list[date]:
        last = min(self.end, up_to) if up_to else self.end
        return [self.start + timedelta(days=n) for n in range((last - self.start).days + 1)]

    def months(self) -> list[date]:
        """The first day of each month the range touches."""
        months, current = [], self.start.replace(day=1)
        while current <= self.end:
            months.append(current)
            current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        return months

    @staticmethod
    def _check(start: date, end: date) -> None:
        if end < start:
            raise _invalid("to", "The end cannot be before the start.")

    @staticmethod
    def _months_back(day: date, months: int) -> date:
        index = day.year * 12 + day.month - 1 - months
        return date(index // 12, index % 12 + 1, 1)
