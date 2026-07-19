from django.apps import AppConfig


class HabitsConfig(AppConfig):
    """Настраивает приложение привычек"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "habits"
