from typing import Optional

from django.core.validators import RegexValidator
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import User, Dialog, Message


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


class DialogSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField("_other_user")
    new_messages = serializers.SerializerMethodField("_new_messages")

    def _other_user(self, obj: Dialog) -> Optional[dict]:
        current_user: Optional[User] = self.context.get("current_user")
        if not current_user:
            return None
        return UserSerializer(obj.other_user(current_user)).data

    def _new_messages(self, obj: Dialog) -> bool:
        return True # TODO: check for unread messages

    class Meta:
        model = Dialog
        fields = ("id", "user", "new_messages",)


class DialogCreateSerializer(serializers.Serializer):
    username: str = serializers.CharField(label="Login", required=True, min_length=5, max_length=32, validators=[
        RegexValidator(r'^[a-z0-9_]*$',
                       'the field must contain only lowercase letters, numbers or underscore'),
    ])


class MessageSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField("_message_type")

    def _message_type(self, obj: Message) -> int:
        current_user: Optional[User] = self.context.get("current_user")
        if not current_user: return 1
        return 1 if obj.author != current_user else 0

    class Meta:
        model = Dialog
        fields = ("id", "text", "time", "type",)


class MessageCreateSerializer(serializers.Serializer):
    text: str = serializers.CharField(label="Message text", required=True, min_length=1, max_length=1024)