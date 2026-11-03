from dataclasses import dataclass
from uuid import UUID

from apps.accounts.domain.entities import UserAccount
from apps.core.domain.entity import Entity, Person
from apps.core.domain.errors import RuleViolation


def _invalid(field: str, message: str) -> RuleViolation:
    return RuleViolation(message, errors={field: [message]})


@dataclass(eq=False, kw_only=True)
class StaffMember(Person):
    """A driver, helper or other non-teaching worker who signs in with an email. The id
    is the sign-in account's id."""

    TITLE_MAX = 60

    job_title: str

    @classmethod
    def clean_title(cls, title: str) -> str:
        title = title.strip()
        if not title or len(title) > cls.TITLE_MAX:
            raise _invalid("job_title", f"Required, up to {cls.TITLE_MAX} characters.")
        return title

    @classmethod
    def from_account(cls, account: UserAccount, job_title: str) -> "StaffMember":
        return cls(id=account.id, name=account.name, email=account.email,
                   is_active=account.is_active, job_title=job_title)

    def retitle(self, title: str) -> None:
        self.job_title = self.clean_title(title)


@dataclass(eq=False, kw_only=True)
class Van(Entity):
    """A school van with a name and, when one is allotted, its driver."""

    NAME_MAX = 60

    name: str
    driver_id: UUID | None = None
    is_active: bool = True
    # Filled in when read, so the app can show it.
    driver_name: str = ""

    @classmethod
    def create(cls, *, name: str, driver_id: UUID | None = None) -> "Van":
        van = cls(name="-", driver_id=driver_id)
        van.rename(name)
        return van

    def rename(self, name: str) -> None:
        name = name.strip()
        if not name or len(name) > self.NAME_MAX:
            raise _invalid("name", f"Required, up to {self.NAME_MAX} characters.")
        self.name = name

    def assign_driver(self, driver_id: UUID | None) -> None:
        self.driver_id = driver_id

    def remove(self) -> None:
        self.is_active = False
