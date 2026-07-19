from datetime import time
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from habits.models import Habit
from notifications.telegram import (
    TelegramError,
    build_habit_message,
    send_telegram_message,
)

User = get_user_model()


class TelegramServiceTests(TestCase):
    @override_settings(TELEGRAM_BOT_TOKEN="")
    @patch("notifications.telegram.requests.post")
    def test_missing_token_raises_without_http_request(self, post):
        with self.assertRaisesMessage(TelegramError, "не задан"):
            send_telegram_message(123, "Текст")

        post.assert_not_called()

    @override_settings(TELEGRAM_BOT_TOKEN="test-token")
    @patch("notifications.telegram.requests.post")
    def test_success_uses_token_and_returns_result(self, post):
        post.return_value = Mock(
            ok=True,
            json=Mock(return_value={"ok": True, "result": {"message_id": 42}}),
        )

        result = send_telegram_message(123, "Текст")

        self.assertEqual(result, {"message_id": 42})
        post.assert_called_once_with(
            "https://api.telegram.org/bottest-token/sendMessage",
            json={"chat_id": 123, "text": "Текст"},
            timeout=15,
        )

    @override_settings(TELEGRAM_BOT_TOKEN="test-token")
    @patch("notifications.telegram.requests.post")
    def test_invalid_json_and_api_error_are_wrapped(self, post):
        post.return_value = Mock(ok=True, json=Mock(side_effect=ValueError))
        with self.assertRaisesMessage(TelegramError, "некорректный ответ"):
            send_telegram_message(123, "Текст")

        post.return_value = Mock(
            ok=False,
            json=Mock(return_value={"ok": False, "description": "Bad Request"}),
        )
        with self.assertRaisesMessage(TelegramError, "Bad Request"):
            send_telegram_message(123, "Текст")

    def test_message_contains_reward_or_related_habit(self):
        user = User.objects.create_user(email="message@example.com", password="password123")
        pleasant = Habit.objects.create(
            owner=user,
            place="Парк",
            time=time(9),
            action="Прогулка",
            duration=60,
            is_pleasant=True,
        )
        reward_habit = Habit.objects.create(
            owner=user,
            place="Дом",
            time=time(8),
            action="Зарядка",
            duration=120,
            reward="Кофе",
        )
        related_habit = Habit.objects.create(
            owner=user,
            place="Дом",
            time=time(10),
            action="Чтение",
            duration=90,
            related_habit=pleasant,
        )

        reward_message = build_habit_message(reward_habit)
        related_message = build_habit_message(related_habit)

        self.assertIn("Вознаграждение: Кофе", reward_message)
        self.assertIn("Продолжительность: 120 сек.", reward_message)
        self.assertIn("После выполнения: Прогулка", related_message)
