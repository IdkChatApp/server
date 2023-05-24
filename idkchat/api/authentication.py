from time import time

from django.conf import settings
from rest_framework import authentication, exceptions
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from .models import Session, User
from .utils import JWT


class IdkAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request: Request) -> tuple[User, None]:
        secret = getattr(settings, "JWT_KEY")
        if not (token := request.META.get('HTTP_AUTHORIZATION')) or (sess := JWT.decode(token, secret)) is None:
            raise exceptions.AuthenticationFailed('No such session')

        session = Session.objects.filter(
            id=sess["session_id"], user__id=sess["user_id"], session_key=sess["session_key"],
            expire_timestamp__gt=int(time())
        ).first()
        if session is None:
            raise exceptions.AuthenticationFailed('No such session')

        return session.user, session


class IdkIsAuthenticated(BasePermission):
    def has_permission(self, request: Request, view):
        return bool(request.user)