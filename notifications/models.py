import secrets
import string

from django.conf import settings
from django.db import models

from habits.models import Habit


def generate_connection_code():
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


class TelegramProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="telegram_profile")
    chat_id = models.BigIntegerField(null=True, blank=True, unique=True)
    username = models.CharField(max_length=64, blank=True)
    connection_code = models.CharField(max_length=8, unique=True, default=generate_connection_code)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def rotate_code(self):
        self.connection_code = generate_connection_code()
        self.save(update_fields=["connection_code", "updated_at"])

    def __str__(self):
        return f"Telegram: {self.user}"


class NotificationLog(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        SENT = "sent", "Отправлено"
        FAILED = "failed", "Ошибка"

    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="notification_logs")
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    telegram_message_id = models.BigIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-scheduled_at",)
        constraints = [
            models.UniqueConstraint(fields=("habit", "scheduled_at"), name="unique_habit_scheduled_notification")
        ]
