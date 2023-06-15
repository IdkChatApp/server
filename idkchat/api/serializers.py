from typing import Optional

from PIL.Image import Image
from django.core.files.images import get_image_dimensions
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.validators import RegexValidator
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator

from .models import User, Dialog, Message, ReadState


class RegisterSerializer(serializers.ModelSerializer):
    login: str = serializers.CharField(label="Login", required=True, min_length=5, max_length=32, validators=[
        RegexValidator(r'^[a-z0-9_]*$',
                       'the field must contain only lowercase letters, numbers or underscore'),
    ])
    salt: str = serializers.CharField(label="Salt", required=True)
    verifier: str = serializers.CharField(label="Verifier", required=True)
    privKey: str = serializers.CharField(label="Encrypted private key", required=True)
    pubKey: str = serializers.CharField(label="Public key", required=True)

    class Meta:
        model = User
        fields = ("login", "salt", "verifier", "privKey", "pubKey",)
        validators = [
            UniqueTogetherValidator(
                queryset=User.objects.all(),
                fields=["login"]
            )
        ]


class LoginStartSerializer(serializers.Serializer):
    login: str = serializers.CharField(label="Login", required=True, min_length=5, max_length=32, validators=[
        RegexValidator(r'^[a-z0-9_]*$',
                       'the field must contain only lowercase letters, numbers or underscore'),
    ])


class LoginSerializer(serializers.Serializer):
    A: str = serializers.CharField(label="Client A value", required=True)
    M: str = serializers.CharField(label="Client M value", required=True)
    ticket = serializers.CharField(label="SRP login ticket", required=True)


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


class UserPatchSerializer(serializers.Serializer):
    avatar = Base64ImageField(allow_null=True, validators=[userAvatarValidator])


class DialogSerializer(serializers.ModelSerializer): # TODO: Add `recipients` field instead of sending other user in `user` field
    user = serializers.SerializerMethodField("_other_user")
    key = serializers.SerializerMethodField("_key")
    new_messages = serializers.SerializerMethodField("_new_messages")

    def _other_user(self, obj: Dialog) -> Optional[dict]:
        current_user: Optional[User] = self.context.get("current_user")
        if not current_user:
            return None
        return UserSerializer(obj.other_user(current_user)).data

    def _new_messages(self, obj: Dialog) -> bool:
        current_user: Optional[User] = self.context.get("current_user")
        if not current_user:
            return True
        read_state = self.context.get("read_state") or \
                     ReadState.objects.filter(dialog__id=self.instance.id, user__id=current_user.id).first()
        if not read_state:
            return True
        last_message_id = self.context.get("last_message_id")
        if last_message_id is None:
            last_message_id = 0
            last_message = Message.objects.filter(dialog__id=self.instance.id).order_by("-id").first()
            if last_message is not None:
                last_message_id = last_message.id
        return last_message_id > read_state.message_id

    def _key(self, obj: Dialog) -> Optional[str]:
        current_user: Optional[User] = self.context.get("current_user")
        if not current_user: return
        return obj.key_1 if obj.user_1 == current_user else obj.key_2

    class Meta:
        model = Dialog
        fields = ("id", "user", "key", "new_messages",)


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


class MessageCreateSerializer(serializers.Serializer):
    content: str = serializers.CharField(label="Message content", required=True, min_length=1, max_length=4096)


class GetUserByNameSerializer(serializers.Serializer):
    username: str = serializers.CharField(label="Login", required=True, min_length=5, max_length=32, validators=[
        RegexValidator(r'^[a-z0-9_]*$',
                       'the field must contain only lowercase letters, numbers or underscore'),
    ])
