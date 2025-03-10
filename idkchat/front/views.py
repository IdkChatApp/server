from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect

from api.models import Session
from front.utils import require_auth


def index_page(request: HttpRequest) -> HttpResponse:
    #return render(request, "index.html")
    return redirect("/auth")


def auth_page(request: HttpRequest) -> HttpResponse:
    return render(request, "auth.html")


@require_auth
def dialogs_page(request: HttpRequest, session: Session) -> HttpResponse:
    user = session.user
    return render(request, "dialogs.html", context={
        "user": user,
    })


@require_auth
def profile_page(request: HttpRequest, session: Session) -> HttpResponse:
    return render(request, "profile.html", context={
        "user": session.user,
    })


@require_auth
def settings_page(request: HttpRequest, session: Session) -> HttpResponse:
    return render(request, "settings.html", context={
        "user": session.user,
    })
