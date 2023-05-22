from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def index_page(request: HttpRequest) -> HttpResponse:
    return render(request, "index.html")

def auth_page(request: HttpRequest) -> HttpResponse:
    return render(request, "auth.html")

def dialogs_page(request: HttpRequest) -> HttpResponse:
    return render(request, "dialogs.html")

def profile_page(request: HttpRequest) -> HttpResponse:
    return render(request, "profile.html")

def feedback_page(request: HttpRequest) -> HttpResponse:
    return render(request, "feedback.html")
