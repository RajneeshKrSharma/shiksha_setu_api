from datetime import date
from enum import Enum
from uuid import UUID

from apps.core.domain.errors import RuleViolation


class QueryParams:
    """Reads the ?filters of a request. A bad value is a 400 that names the filter."""

    def __init__(self, request):
        self._query = request.query_params

    def text(self, name: str) -> str:
        return self._query.get(name, "").strip()

    def uuid(self, name: str) -> UUID | None:
        raw = self._query.get(name)
        if not raw:
            return None
        try:
            return UUID(raw)
        except ValueError:
            raise self._bad(name, "Not a valid id.")

    def date(self, name: str) -> date | None:
        raw = self._query.get(name)
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            raise self._bad(name, "Use the form YYYY-MM-DD.")

    def choice(self, name: str, options: type[Enum]) -> Enum | None:
        raw = self._query.get(name)
        if not raw:
            return None
        try:
            return options(raw)
        except ValueError:
            allowed = ", ".join(option.value for option in options)
            raise self._bad(name, f"Choose one of: {allowed}.")

    def flag(self, name: str, *, default: bool) -> bool:
        raw = self._query.get(name)
        if raw is None or raw == "":
            return default
        if raw.lower() in ("true", "1", "yes"):
            return True
        if raw.lower() in ("false", "0", "no"):
            return False
        raise self._bad(name, "Use true or false.")

    def active(self, name: str = "active") -> bool | None:
        """true (the default), false, or all."""
        raw = self._query.get(name, "true").lower()
        if raw == "all":
            return None
        return self.flag(name, default=True)

    @staticmethod
    def _bad(name: str, message: str) -> RuleViolation:
        return RuleViolation(f"{name}: {message}", errors={name: [message]})
