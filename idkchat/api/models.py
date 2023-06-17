from __future__ import annotations
from os import urandom
from time import time
from typing import Optional

from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models.fields.files import ImageFieldFile

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
    avatar: ImageFieldFile = models.ImageField(null=True, upload_to="avatars")

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, login={self.login!r})"

    def is_authenticated(self) -> bool:
        return True


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
            "pubKey": self.user.pubKey,
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
    key_1: str = models.TextField(max_length=512)
    key_2: str = models.TextField(max_length=512)

    def other_user(self, current_user: User) -> User:
        return self.user_1 if self.user_2 == current_user else self.user_2

    def unread_count(self, current_user: User, context: dict=None) -> int:
        if context is None: context = {}
        read_state = context.get("read_state") or \
                     ReadState.objects.filter(dialog__id=self.id, user__id=current_user.id).first()
        if not read_state:
            return 1

        unread_count = Message.objects.filter(id__gt=read_state.message_id, dialog__id=self.id).count()
        if unread_count > 100: unread_count = 100

        return unread_count

    def last_message(self) -> Optional[Message]:
        return Message.objects.filter(dialog=self).order_by("-id").first()

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
    content: str = models.TextField(max_length=4096)

    def __repr__(self) -> str:
        return f"Message(id={self.id!r}, dialog.id={self.dialog.id!r}, author.id={self.author.id!r})"


class ReadState(BaseModel):
    dialog: Dialog = models.ForeignKey(Dialog, on_delete=models.CASCADE)
    user: User = models.ForeignKey(User, on_delete=models.CASCADE)
    message_id: int = models.BigIntegerField(default=0)

    def __repr__(self) -> str:
        return f"ReadState(user.id={self.user.id!r}, dialog.id={self.dialog.id!r}, message_id={self.message_id!r})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dialog", "user"], name="unique_read_state"
            )
        ]
