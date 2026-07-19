from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.management import CommandError
from django.test import TestCase, override_settings

from notifications.management.commands.run_telegram_bot import Command
from notifications.models import TelegramProfile

User = get_user_model()


class TelegramBotCommandTests(TestCase):
    def setUp(self):
        self.command = Command()
        self.user = User.objects.create_user(email="bot@example.com", password="password123")
        self.profile = TelegramProfile.objects.create(user=self.user)

    @override_settings(TELEGRAM_BOT_TOKEN="")
    def test_handle_requires_token(self):
        with self.assertRaises(CommandError):
            self.command.handle()

    @patch.object(Command, "send")
    def test_message_without_start_is_ignored(self, send):
        self.command.process_update(
            "https://telegram.test",
            {"message": {"text": "hello", "chat": {"id": 123}}},
        )

        send.assert_not_called()
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.is_verified)

    @patch.object(Command, "send")
    def test_start_without_or_with_wrong_code_does_not_bind(self, send):
        self.command.process_update(
            "https://telegram.test",
            {"message": {"text": "/start", "chat": {"id": 123}}},
        )
        self.command.process_update(
            "https://telegram.test",
            {"message": {"text": "/start WRONG123", "chat": {"id": 123}}},
        )

        self.profile.refresh_from_db()
        self.assertFalse(self.profile.is_verified)
        self.assertEqual(send.call_count, 2)

    @patch.object(Command, "send")
    def test_start_code_binds_chat_and_unbinds_previous_profile(self, send):
        other = User.objects.create_user(email="old@example.com", password="password123")
        old_profile = TelegramProfile.objects.create(
            user=other,
            chat_id=123,
            username="old",
            is_verified=True,
        )

        self.command.process_update(
            "https://telegram.test",
            {
                "message": {
                    "text": f"/start {self.profile.connection_code.lower()}",
                    "chat": {"id": 123, "username": "student"},
                }
            },
        )

        self.profile.refresh_from_db()
        old_profile.refresh_from_db()
        self.assertTrue(self.profile.is_verified)
        self.assertEqual(self.profile.chat_id, 123)
        self.assertEqual(self.profile.username, "student")
        self.assertIsNone(old_profile.chat_id)
        self.assertFalse(old_profile.is_verified)
        send.assert_called_once()

    @patch("notifications.management.commands.run_telegram_bot.requests.post")
    def test_send_posts_to_telegram(self, post):
        post.return_value.raise_for_status = Mock()

        self.command.send("https://telegram.test", 123, "Готово")

        post.assert_called_once_with(
            "https://telegram.test/sendMessage",
            json={"chat_id": 123, "text": "Готово"},
            timeout=15,
        )
        post.return_value.raise_for_status.assert_called_once_with()
