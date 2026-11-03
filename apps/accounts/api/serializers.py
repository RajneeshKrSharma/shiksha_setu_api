from rest_framework import serializers

from ..domain.usecases.get_current_user import CurrentUser


class LoginInput(serializers.Serializer):
    email = serializers.CharField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class RefreshInput(serializers.Serializer):
    refresh = serializers.CharField()


class ChangePasswordInput(serializers.Serializer):
    current = serializers.CharField(max_length=128, trim_whitespace=False)
    new = serializers.CharField(max_length=128, trim_whitespace=False)


class UpdateMeInput(serializers.Serializer):
    name = serializers.CharField(max_length=120)


class AppointViceInput(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(max_length=120)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class VicePrincipalPatchInput(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=120)
    is_active = serializers.BooleanField(required=False)
    password = serializers.CharField(required=False, max_length=128, trim_whitespace=False)


class GrantInput(serializers.Serializer):
    user_id = serializers.UUIDField()
    capability = serializers.CharField(max_length=60)
    reason = serializers.CharField(allow_blank=True)


class TokenPairOut(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class AccountOut(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    name = serializers.CharField()
    role = serializers.CharField(allow_null=True)
    joined_on = serializers.DateTimeField()
    is_active = serializers.BooleanField()


class CurrentUserOut(serializers.Serializer):
    """The account, plus the permission codes the app uses to decide what to show."""

    def to_representation(self, current: CurrentUser):
        data = AccountOut(current.account).data
        data["capabilities"] = [c.code for c in current.capabilities]
        return data


class CapabilityOut(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()


class GrantOut(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    capability = serializers.CharField()
    reason = serializers.CharField()
    granted_by_id = serializers.UUIDField(allow_null=True)
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
