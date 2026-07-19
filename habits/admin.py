from django.contrib import admin

from .models import Habit


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    """Настраивает отображение привычек в админ-панели"""

    list_display = (
        "action",
        "owner",
        "time",
        "periodicity",
        "is_pleasant",
        "is_public",
    )
    list_filter = ("is_pleasant", "is_public", "periodicity")
    search_fields = ("action", "place", "owner__email")
