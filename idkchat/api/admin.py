from django.contrib import admin

from .models import Session, User, PendingAuth

admin.site.register(User)
admin.site.register(Session)
admin.site.register(PendingAuth)
