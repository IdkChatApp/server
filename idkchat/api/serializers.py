from typing import Optional

from django.core.files.images import get_image_dimensions
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.validators import RegexValidator
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator

from .models import User, Dialog, Message


class RegisterSerializer(serializers.ModelSerializer):
    login = serializers.CharField(label="Login", required=True, min_length=5, max_length=32, validators=[
        RegexValidator(r'^[a-z0-9_]*$',
                       'the field must contain only lowercase letters, numbers or underscore'),
    ])
    salt = serializers.CharField(label="Salt", required=True)
    verifier = serializers.CharField(label="Verifier", required=True)
    privKey = serializers.CharField(label="Encrypted private key", required=True)
    pubKey = serializers.CharField(label="Public key", required=True)

    class Meta:
        model = User
        fields = ("login", "salt", "verifier", "privKey", "pubKey",)
        validators = [
            UniqueTogetherValidator(
                queryset=User.objects.all(),
                fields=["login"]
            )
        ]


# noinspection PyAbstractClass
class LoginStartSerializer(serializers.Serializer):
    login = serializers.CharField(label="Login", required=True, min_length=5, max_length=32, validators=[
        RegexValidator(r'^[a-z0-9_]*$',
                       'the field must contain only lowercase letters, numbers or underscore'),
    ])


# noinspection PyAbstractClass
class SrpSerializer(serializers.Serializer):
    A = serializers.CharField(label="Client A value", required=True)
    M = serializers.CharField(label="Client M value", required=True)
    ticket = serializers.CharField(label="SRP login ticket", required=True)


# noinspection PyAbstractClass
class LoginSerializer(SrpSerializer):
    pass


# noinspection PyAbstractClass
class ChangePasswordSerializer(SrpSerializer):
    new_salt = serializers.CharField(label="Salt", required=True)
    new_verifier = serializers.CharField(label="Verifier", required=True)
    new_privkey = serializers.CharField(label="Private key encrypted with new key", required=True)


class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="login")

    class Meta:
        model = User
        fields = ("id", "login", "username", "pubKey", "avatar",)


def userAvatarValidator(value: Optional[SimpleUploadedFile]) -> Optional[SimpleUploadedFile]:
    if value is None:
        return value
    if value.size > 4 * 1024 * 124:
        raise ValidationError("You cannot upload avatar more than 4mb")
    if any(s > 1024 for s in get_image_dimensions(value)):
        raise ValidationError("You cannot upload avatar more than 1024x1024 pixels")
    return value


# noinspection PyAbstractClass
class UserPatchSerializer(serializers.Serializer):
    avatar = Base64ImageField(allow_null=True, validators=[userAvatarValidator])


class DialogSerializer(serializers.ModelSerializer): # TODO: Add `recipients` field instead of sending other user in `user` field
    user = serializers.SerializerMethodField("_other_user")
    key = serializers.SerializerMethodField("_key")
    unread_count = serializers.SerializerMethodField("_unread_count")
    last_message = serializers.SerializerMethodField("_last_message")

    def _other_user(self, obj: Dialog) -> Optional[dict]:
        current_user: Optional[User] = self.context.get("current_user")
        if not current_user:
            return None
        return UserSerializer(obj.other_user(current_user)).data

    def _unread_count(self, obj: Dialog) -> int:
        if (unread := self.context.get("unread_count")) is not None:
            return unread

        current_user: Optional[User] = self.context.get("current_user")
        if not current_user:
            return 1

        unread_count = obj.unread_count(current_user, self.context)

        return unread_count

    def _key(self, obj: Dialog) -> Optional[str]:
        current_user: Optional[User] = self.context.get("current_user")
        if not current_user: return
        return obj.key_1 if obj.user_1 == current_user else obj.key_2

    def _last_message(self, obj: Dialog) -> Optional[dict]:
        last_message: Optional[Message] = self.context.get("last_message")
        if not last_message: last_message = obj.last_message()
        if last_message is not None: return MessageSerializer(last_message).data

    class Meta:
        model = Dialog
        fields = ("id", "user", "key", "unread_count", "last_message",)


# noinspection PyAbstractClass
class DialogCreateSerializer(serializers.Serializer):
    username: str = serializers.CharField(label="Login", required=True, min_length=5, max_length=32, validators=[
        RegexValidator(r'^[a-z0-9_]*$',
                       'the field must contain only lowercase letters, numbers or underscore'),
    ])
    keys = serializers.DictField()


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "content", "created_at", "author",)


# noinspection PyAbstractClass
class MessageCreateSerializer(serializers.Serializer):
    content: str = serializers.CharField(label="Message content", required=True, min_length=1, max_length=4096)


# noinspection PyAbstractClass
class GetUserByNameSerializer(serializers.Serializer):
    username: str = serializers.CharField(label="Login", required=True, min_length=5, max_length=32, validators=[
        RegexValidator(r'^[a-z0-9_]*$',
                       'the field must contain only lowercase letters, numbers or underscore'),
    ])
