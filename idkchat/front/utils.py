from time import time

from django.conf import settings
from django.http import HttpRequest, HttpResponseRedirect

from api.models import Session
from api.utils import JWT


def _require_auth(func, self, request: HttpRequest, *args, **kwargs):
    auth_redirect = HttpResponseRedirect("/auth")
    auth_redirect.delete_cookie("token")
    auth_redirect.set_cookie("redirect_path", request.get_full_path())

    token = request.COOKIES.get("token")
    secret = getattr(settings, "JWT_KEY")
    if not token or (sess := JWT.decode(token, secret)) is None:
        return auth_redirect

    session: Session = Session.objects.filter(
        id=sess["session_id"], user__id=sess["user_id"], session_key=sess["session_key"],
        expire_timestamp__gt=int(time())
    ).first()
    if session is None:
        return auth_redirect

    return func(request, session, *args, **kwargs) if self is None else func(self, request, session, *args, **kwargs)


def require_auth(func):
    def wrapped(request: HttpRequest, *args, **kwargs):
        return _require_auth(func, None, request, *args, **kwargs)

    return wrapped


def require_auth_class(func):
    def wrapped(self, request: HttpRequest, *args, **kwargs):
        return _require_auth(func, self, request, *args, **kwargs)

    return wrapped