from datetime import datetime, timedelta

from django.utils import timezone


def calculate_next_notification(habit_time, periodicity, from_dt=None):
    """Рассчитывает дату следующего напоминания"""

    now = timezone.localtime(from_dt or timezone.now())
    candidate = timezone.make_aware(
        datetime.combine(now.date(), habit_time),
        timezone.get_current_timezone(),
    )
    if candidate <= now:
        candidate += timedelta(days=periodicity)
    return candidate
