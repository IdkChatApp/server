from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect

from api.models import Session, Dialog
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
        "dialogs": Dialog.objects.filter(Q(user_1=user) | Q(user_2=user)),
        "messages_count": range(200),
    })


def profile_page(request: HttpRequest) -> HttpResponse:
    return render(request, "profile.html")
