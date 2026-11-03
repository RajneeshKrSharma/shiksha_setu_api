from rest_framework import serializers

from ..domain.entities import LessonStatus


class TeacherInput(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class TeacherPatchInput(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=120)
    is_active = serializers.BooleanField(required=False)
    password = serializers.CharField(required=False, max_length=128, trim_whitespace=False)


class TeacherOut(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    email = serializers.EmailField()
    is_active = serializers.BooleanField()


class AllotmentInput(serializers.Serializer):
    teacher_id = serializers.UUIDField()
    class_id = serializers.UUIDField()
    subject = serializers.CharField(max_length=60)


class AllotmentOut(serializers.Serializer):
    id = serializers.UUIDField()
    teacher_id = serializers.UUIDField()
    teacher_name = serializers.CharField()
    class_id = serializers.UUIDField()
    class_name = serializers.CharField()
    subject = serializers.CharField()


class LessonInput(serializers.Serializer):
    allotment_id = serializers.UUIDField()
    topic = serializers.CharField(max_length=500)
    taught_on = serializers.DateField(required=False)


class LessonPatchInput(serializers.Serializer):
    topic = serializers.CharField(max_length=500)


class LessonOut(serializers.Serializer):
    id = serializers.UUIDField()
    allotment_id = serializers.UUIDField()
    teacher_id = serializers.UUIDField()
    teacher_name = serializers.CharField()
    class_id = serializers.UUIDField()
    class_name = serializers.CharField()
    subject = serializers.CharField()
    taught_on = serializers.DateField()
    topic = serializers.CharField()
    recorded_at = serializers.DateTimeField()


class LessonStatusOut(serializers.Serializer):
    """One allotment for the day: its lesson, or null while it is pending."""

    def to_representation(self, status: LessonStatus):
        allotment = status.allotment
        return {
            "allotment_id": str(allotment.id),
            "teacher_id": str(allotment.teacher_id),
            "teacher_name": allotment.teacher_name,
            "class_id": str(allotment.class_id),
            "class_name": allotment.class_name,
            "subject": allotment.subject,
            "recorded": status.recorded,
            "lesson": LessonOut(status.lesson).data if status.lesson else None,
        }
