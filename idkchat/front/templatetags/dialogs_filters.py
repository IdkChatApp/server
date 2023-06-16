from django.template import Library

from api.models import Dialog, User

register = Library()


def other_user(dialog: Dialog, current_user: User) -> User:
    return dialog.other_user(current_user)


def unread_count(dialog: Dialog, current_user: User) -> int:
    return dialog.unread_count(current_user)


register.filter("other_user", other_user)
register.filter("unread_count", unread_count)
