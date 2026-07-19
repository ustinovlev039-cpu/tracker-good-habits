from datetime import time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from habits.models import Habit
from notifications.models import NotificationLog, TelegramProfile
from notifications.tasks import send_due_habit_reminders

User = get_user_model()


class ReminderTaskTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = User.objects.create_user(email="due@example.com", password="password123")
        TelegramProfile.objects.create(
            user=self.user,
            chat_id=987654,
            is_verified=True,
        )

    def habit(self, owner=None, **kwargs):
        data = {
            "owner": owner or self.user,
            "place": "Дом",
            "time": time(8),
            "action": "Зарядка",
            "duration": 60,
            "periodicity": 2,
            "next_notification_at": self.now - timedelta(minutes=1),
        }
        data.update(kwargs)
        return Habit.objects.create(**data)

    @patch("notifications.tasks.send_telegram_message", return_value={"message_id": 55})
    def test_sends_only_due_connected_habits_and_updates_state(self, send):
        due = self.habit()
        self.habit(action="Будущая", next_notification_at=self.now + timedelta(hours=1))
        disconnected = User.objects.create_user(
            email="disconnected@example.com",
            password="password123",
        )
        self.habit(owner=disconnected, action="Без Telegram")

        result = send_due_habit_reminders.run()

        self.assertEqual(result, {"sent": 1, "failed": 0})
        send.assert_called_once()
        self.assertEqual(send.call_args.args[0], 987654)
        due.refresh_from_db()
        log = NotificationLog.objects.get(habit=due)
        self.assertEqual(log.status, NotificationLog.Status.SENT)
        self.assertEqual(log.telegram_message_id, 55)
        self.assertIsNotNone(log.sent_at)
        self.assertGreater(due.next_notification_at, self.now)

    @patch("notifications.tasks.send_telegram_message", side_effect=RuntimeError("Telegram down"))
    def test_failure_is_logged_and_next_schedule_is_calculated(self, send):
        due = self.habit(next_notification_at=self.now - timedelta(days=5))

        result = send_due_habit_reminders.run()

        self.assertEqual(result, {"sent": 0, "failed": 1})
        log = NotificationLog.objects.get(habit=due)
        self.assertEqual(log.status, NotificationLog.Status.FAILED)
        self.assertIn("Telegram down", log.error_message)
        due.refresh_from_db()
        self.assertGreater(due.next_notification_at, timezone.now())

    @patch("notifications.tasks.send_telegram_message", return_value={"message_id": 1})
    def test_sent_schedule_is_not_sent_twice(self, send):
        due = self.habit()
        NotificationLog.objects.create(
            habit=due,
            scheduled_at=due.next_notification_at,
            status=NotificationLog.Status.SENT,
        )

        result = send_due_habit_reminders.run()

        self.assertEqual(result, {"sent": 0, "failed": 0})
        send.assert_not_called()

    @patch("notifications.tasks.send_telegram_message", return_value={"message_id": 77})
    def test_task_runs_in_eager_mode_without_worker(self, send):
        due = self.habit()

        result = send_due_habit_reminders.delay().get()

        self.assertEqual(result, {"sent": 1, "failed": 0})
        self.assertTrue(
            NotificationLog.objects.filter(
                habit=due,
                status=NotificationLog.Status.SENT,
            ).exists()
        )
