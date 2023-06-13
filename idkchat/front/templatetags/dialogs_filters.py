from django.template import Library

from api.models import Dialog, User

register = Library()


def other_user(dialog: Dialog, current_user: User) -> User:
    return dialog.other_user(current_user)


register.filter("other_user", other_user)