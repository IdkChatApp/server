from django.core.validators import RegexValidator
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import User


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
