from django.db import models


class BaseModel(models.Model):
    objects = models.Manager()

    def __str__(self) -> str:
        return self.__repr__()

    class Meta:
        abstract = True


class User(BaseModel):
    id: int = models.BigAutoField(primary_key=True)
    login: str = models.TextField(unique=True, max_length=32)
    password: str = models.TextField(max_length=1024)
    avatar: str = models.TextField(max_length=4096)

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, login={self.login!r})"


class Session(BaseModel):
    id: int = models.BigAutoField(primary_key=True)
    user: int = models.ForeignKey(User, on_delete=models.CASCADE)

    def __repr__(self) -> str:
        return f"Session(id={self.id!r}, user={self.user!r})"


class PendingAuth(BaseModel):
    id: int = models.BigAutoField(primary_key=True)
    pubB: str = models.TextField(max_length=4096)
    privB: str = models.TextField(max_length=4096)
    expire_timestamp: int = models.BigIntegerField()

    def __repr__(self) -> str:
        return f"PendingAuth(id={self.id!r}, expire_timestamp={self.expire_timestamp!r})"