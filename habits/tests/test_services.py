from datetime import datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone

from habits.services import calculate_next_notification


class CalculateNextNotificationTests(TestCase):
    """Проверяет расчёт следующего напоминания"""

    def aware(self, value):
        """Добавляет текущий часовой пояс к дате"""

        return timezone.make_aware(value, timezone.get_current_timezone())

    def test_uses_today_when_time_has_not_arrived(self):
        """Проверяет напоминание сегодня до нужного времени"""

        now = self.aware(datetime(2026, 7, 19, 8, 0))

        result = calculate_next_notification(time(9, 30), 3, from_dt=now)

        self.assertEqual(result, self.aware(datetime(2026, 7, 19, 9, 30)))

    def test_uses_periodicity_when_time_has_passed(self):
        """Проверяет перенос по периодичности после времени"""

        now = self.aware(datetime(2026, 7, 19, 10, 0))

        result = calculate_next_notification(time(9, 30), 3, from_dt=now)

        self.assertEqual(result, self.aware(datetime(2026, 7, 22, 9, 30)))

    def test_exact_time_is_scheduled_for_next_period(self):
        """Проверяет перенос при точном совпадении времени"""

        now = self.aware(datetime(2026, 7, 19, 9, 30))

        result = calculate_next_notification(time(9, 30), 1, from_dt=now)

        self.assertEqual(result, now + timedelta(days=1))
