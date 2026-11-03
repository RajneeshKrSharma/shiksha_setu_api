from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from apps.core.domain.entity import Entity, Person
from apps.core.domain.errors import RuleViolation


def _invalid(field: str, message: str) -> RuleViolation:
    return RuleViolation(message, errors={field: [message]})


class ClassLevel(StrEnum):
    NURSERY = "nursery"
    LKG = "lkg"
    UKG = "ukg"
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"

    @property
    def label(self) -> str:
        return {"nursery": "Nursery", "lkg": "LKG", "ukg": "UKG"}.get(self.value, self.value)

    @property
    def order(self) -> int:
        return list(ClassLevel).index(self)


@dataclass(eq=False, kw_only=True)
class SchoolClass(Entity):
    """A level and a section, such as 5-A. The section may be left blank."""

    SECTION_MAX = 3

    level: ClassLevel
    section: str = ""
    is_active: bool = True

    @classmethod
    def create(cls, *, level: ClassLevel, section: str = "") -> "SchoolClass":
        school_class = cls(level=level)
        school_class.reshape(level=level, section=section)
        return school_class

    def reshape(self, *, level: ClassLevel, section: str) -> None:
        section = section.strip().upper()
        if section and (len(section) > self.SECTION_MAX or not section.isalnum()):
            raise _invalid(
                "section", f"Letters or digits only, up to {self.SECTION_MAX} characters."
            )
        self.level, self.section = level, section

    @property
    def name(self) -> str:
        return f"{self.level.label}-{self.section}" if self.section else self.level.label

    def remove(self) -> None:
        self.is_active = False


@dataclass(eq=False, kw_only=True)
class Student(Person):
    """A pupil. Only what the school needs: name, roll number, class, guardian's name,
    and whether the student uses the school van."""

    ROLL_MAX = 10
    GUARDIAN_MAX = 120

    roll_number: str
    class_id: UUID
    guardian_name: str
    uses_van: bool = False
    # Filled in when read, so the app can show it.
    class_name: str = ""

    @classmethod
    def admit(cls, *, name: str, roll_number: str, class_id: UUID, guardian_name: str,
              uses_van: bool = False) -> "Student":
        student = cls(name="-", roll_number="-", class_id=class_id, guardian_name="-",
                      uses_van=uses_van)
        student.update_details(name=name, roll_number=roll_number, guardian_name=guardian_name)
        return student

    def update_details(self, *, name: str, roll_number: str, guardian_name: str) -> None:
        self.rename(name)
        roll_number, guardian_name = roll_number.strip(), guardian_name.strip()
        if not roll_number or len(roll_number) > self.ROLL_MAX:
            raise _invalid("roll_number", f"Required, up to {self.ROLL_MAX} characters.")
        if not guardian_name or len(guardian_name) > self.GUARDIAN_MAX:
            raise _invalid("guardian_name", f"Required, up to {self.GUARDIAN_MAX} characters.")
        self.roll_number, self.guardian_name = roll_number, guardian_name

    def move_to(self, class_id: UUID) -> None:
        self.class_id = class_id
