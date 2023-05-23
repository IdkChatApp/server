from os import urandom
from time import time

from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models

from .utils import JWT


class BaseModel(models.Model):
    objects = models.Manager()

    def __str__(self) -> str:
        return self.__repr__()

    class Meta:
        abstract = True


class User(BaseModel):
    id: int = models.BigAutoField(primary_key=True)
    login: str = models.CharField(unique=True, max_length=32,
                                  validators=[MinLengthValidator(5, 'the field must contain at least 5 characters')])
    salt: str = models.TextField(max_length=1024)
    verifier: str = models.TextField(max_length=4096)
    privKey: str = models.TextField(max_length=4096)
    pubKey: str = models.TextField(max_length=2048)
    avatar: str = models.TextField(max_length=4096, null=True)

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, login={self.login!r})"


def generate_random_key() -> str:
    return urandom(16).hex()


class Session(BaseModel):
    id: int = models.BigAutoField(primary_key=True)
    user: User = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key: str = models.CharField(max_length=32, default=generate_random_key)

    def __repr__(self) -> str:
        return f"Session(id={self.id!r}, session_key={self.session_key!r}, user={self.user!r})"

    def toJWT(self) -> str:
        secret = getattr(settings, "JWT_KEY")
        return JWT.encode({
            "user_id": self.user.id,
            "session_id": self.id,
            "session_key": self.session_key,
        }, secret, time() + 86400 * 2)


class PendingAuth(BaseModel):
    id: int = models.BigAutoField(primary_key=True)
    user: User = models.ForeignKey(User, on_delete=models.CASCADE)
    pubB: str = models.TextField(max_length=4096)
    privB: str = models.TextField(max_length=4096)
    expire_timestamp: int = models.BigIntegerField()

    def __repr__(self) -> str:
        return f"PendingAuth(id={self.id!r}, expire_timestamp={self.expire_timestamp!r})"