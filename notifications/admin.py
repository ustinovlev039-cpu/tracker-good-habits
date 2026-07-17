from django.contrib import admin

from .models import NotificationLog, TelegramProfile

admin.site.register(TelegramProfile)
admin.site.register(NotificationLog)
