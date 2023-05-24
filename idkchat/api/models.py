from os import urandom
from time import time

from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models

from .utils import JWT


def generate_random_key() -> str:
    return urandom(16).hex()


def generate_exp_time() -> int:
    return int(time() + 86400 * 2)


def time_int() -> int:
    return int(time())


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


class Session(BaseModel):
    id: int = models.BigAutoField(primary_key=True)
    user: User = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key: str = models.CharField(max_length=32, default=generate_random_key)
    expire_timestamp: int = models.BigIntegerField(default=generate_exp_time)

    def __repr__(self) -> str:
        return f"Session(id={self.id!r}, session_key={self.session_key!r}, user={self.user!r})"

    def toJWT(self) -> str:
        secret = getattr(settings, "JWT_KEY")
        return JWT.encode({
            "user_id": self.user.id,
            "session_id": self.id,
            "session_key": self.session_key,
        }, secret, self.expire_timestamp)


class PendingAuth(BaseModel):
    id: int = models.BigAutoField(primary_key=True)
    user: User = models.ForeignKey(User, on_delete=models.CASCADE)
    pubB: str = models.TextField(max_length=4096)
    privB: str = models.TextField(max_length=4096)
    expire_timestamp: int = models.BigIntegerField()

    def __repr__(self) -> str:
        return f"PendingAuth(id={self.id!r}, expire_timestamp={self.expire_timestamp!r})"


class Dialog(BaseModel):
    id: int = models.BigAutoField(primary_key=True)
    user_1: User = models.ForeignKey(User, related_name="user_1", on_delete=models.CASCADE)
    user_2: User = models.ForeignKey(User, related_name="user_2", on_delete=models.CASCADE)

    def other_user(self, current_user: User) -> User:
        return self.user_1 if self.user_2 == current_user else self.user_2

    def __repr__(self) -> str:
        return f"Dialog(id={self.id!r}, user_1.id={self.user_1.id!r}, user_2.id={self.user_2.id!r})"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user_1", "user_2"], name="unique_dialog_between_users1"),
            models.UniqueConstraint(fields=["user_2", "user_1"], name="unique_dialog_between_users2"),
        ]


class Message(BaseModel):
    id: int = models.BigAutoField(primary_key=True)
    dialog: Dialog = models.ForeignKey(Dialog, on_delete=models.CASCADE)
    author: User = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at: int = models.BigIntegerField(default=time_int)
    text: str = models.TextField(max_length=4096)

    def __repr__(self) -> str:
        return f"Message(id={self.id!r}, dialog.id={self.dialog.id!r}, author.id={self.author.id!r})"


class ReadState(BaseModel):
    dialog: Dialog = models.ForeignKey(Dialog, on_delete=models.CASCADE)
    user: User = models.ForeignKey(User, on_delete=models.CASCADE)
    message_id: int = models.BigIntegerField()

    def __repr__(self) -> str:
        return f"ReadState(user.id={self.user.id!r}, dialog.id={self.dialog.id!r}, message_id={self.message_id!r})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dialog", "user"], name="unique_read_state"
            )
        ]
