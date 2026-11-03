from rest_framework import serializers

from ..domain.entities import (
    DayBoard,
    RosterLine,
    StudentStatus,
    StudentTally,
    WorkAttendance,
)

_HHMM = {"format": "%H:%M", "input_formats": ["%H:%M", "%H:%M:%S"]}


class StudentMarkInput(serializers.Serializer):
    student_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=[s.value for s in StudentStatus])


class ClassAttendanceInput(serializers.Serializer):
    class_id = serializers.UUIDField()
    day = serializers.DateField(required=False)
    marks = StudentMarkInput(many=True, allow_empty=True)


class RosterLineOut(serializers.Serializer):
    def to_representation(self, line: RosterLine):
        student = line.student
        return {
            "student_id": str(student.id),
            "name": student.name,
            "roll_number": student.roll_number,
            "status": line.mark.status.value if line.mark else None,
        }


class TallyOut(serializers.Serializer):
    def to_representation(self, tally: StudentTally):
        student = tally.student
        return {
            "student_id": str(student.id),
            "name": student.name,
            "roll_number": student.roll_number,
            "present": tally.present,
            "late": tally.late,
            "absent": tally.absent,
        }


class WorkRecordOut(serializers.Serializer):
    id = serializers.UUIDField()
    person_id = serializers.UUIDField()
    person_name = serializers.CharField()
    role = serializers.CharField()
    day = serializers.DateField()
    checked_in_at = serializers.TimeField(**{"format": "%H:%M:%S"})
    checked_out_at = serializers.TimeField(allow_null=True, **{"format": "%H:%M:%S"})
    status = serializers.CharField()
    corrected_by_id = serializers.UUIDField(allow_null=True)


class CorrectionInput(serializers.Serializer):
    person_id = serializers.UUIDField()
    day = serializers.DateField()
    checked_in_at = serializers.TimeField(**_HHMM)
    checked_out_at = serializers.TimeField(required=False, allow_null=True, default=None, **_HHMM)


class DayBoardOut(serializers.Serializer):
    def to_representation(self, board: DayBoard):
        return {
            "day": board.day.isoformat(),
            "is_holiday": board.is_holiday,
            "people": [
                {
                    "person_id": str(line.person_id),
                    "name": line.name,
                    "role": line.role,
                    "status": line.status.value,
                    "checked_in_at": self._time(line.record.checked_in_at) if line.record else None,
                    "checked_out_at": self._time(line.record.checked_out_at) if line.record else None,
                }
                for line in board.people
            ],
        }

    @staticmethod
    def _time(value):
        return value.strftime("%H:%M:%S") if value else None
