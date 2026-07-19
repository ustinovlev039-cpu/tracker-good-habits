import re
from datetime import time

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from habits.models import Habit
from notifications.models import (
    NotificationLog,
    TelegramProfile,
    generate_connection_code,
)

User = get_user_model()


class TelegramApiTests(APITestCase):
    """Проверяет API привязки Telegram"""

    def setUp(self):
        """Создаёт пользователя для тестов Telegram"""

        self.user = User.objects.create_user(
            email="telegram@example.com",
            password="password123",
        )

    def test_connect_requires_authentication(self):
        """Проверяет защиту привязки авторизацией"""

        response = self.client.post(reverse("telegram-connect"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(TELEGRAM_BOT_USERNAME="habit_test_bot")
    def test_connect_creates_profile_code_and_bot_link(self):
        """Проверяет создание кода и ссылки на бота"""

        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("telegram-connect"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profile = TelegramProfile.objects.get(user=self.user)
        self.assertEqual(
            response.data["connection_code"],
            profile.connection_code,
        )
        self.assertRegex(profile.connection_code, r"^[A-Z0-9]{8}$")
        self.assertEqual(
            response.data["bot_link"],
            f"https://t.me/habit_test_bot?start={profile.connection_code}",
        )

    def test_repeated_connect_rotates_unverified_code(self):
        """Проверяет замену неподтверждённого кода"""

        self.client.force_authenticate(self.user)
        self.client.post(reverse("telegram-connect"))
        profile = TelegramProfile.objects.get(user=self.user)
        old_code = profile.connection_code

        response = self.client.post(reverse("telegram-connect"))

        profile.refresh_from_db()
        self.assertNotEqual(profile.connection_code, old_code)
        self.assertEqual(
            response.data["connection_code"],
            profile.connection_code,
        )

    def test_verified_connect_keeps_code_and_status_returns_profile(self):
        """Проверяет сохранение подтверждённой привязки"""

        profile = TelegramProfile.objects.create(
            user=self.user,
            chat_id=123,
            is_verified=True,
        )
        original_code = profile.connection_code
        self.client.force_authenticate(self.user)

        connect = self.client.post(reverse("telegram-connect"))
        status_response = self.client.get(reverse("telegram-status"))

        profile.refresh_from_db()
        self.assertEqual(connect.status_code, status.HTTP_200_OK)
        self.assertEqual(profile.connection_code, original_code)
        self.assertTrue(status_response.data["is_verified"])

    @override_settings(TELEGRAM_BOT_USERNAME="")
    def test_status_creates_profile_and_returns_no_link_without_username(self):
        """Проверяет статус без имени Telegram-бота"""

        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("telegram-status"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["bot_link"])
        self.assertTrue(
            TelegramProfile.objects.filter(user=self.user).exists()
        )


class NotificationModelTests(TestCase):
    """Проверяет модели Telegram и уведомлений"""

    def setUp(self):
        """Создаёт пользователя и привычку для тестов моделей"""

        self.user = User.objects.create_user(
            email="models@example.com",
            password="password123",
        )
        self.habit = Habit.objects.create(
            owner=self.user,
            place="Дом",
            time=time(8),
            action="Зарядка",
            duration=60,
        )

    def test_connection_code_format_and_rotation(self):
        """Проверяет формат и замену кода привязки"""

        code = generate_connection_code()
        profile = TelegramProfile.objects.create(user=self.user)
        old_code = profile.connection_code

        profile.rotate_code()

        self.assertTrue(re.fullmatch(r"[A-Z0-9]{8}", code))
        self.assertNotEqual(profile.connection_code, old_code)
        self.assertEqual(str(profile), "Telegram: models@example.com")

    def test_habit_and_notification_log_string_representations(self):
        """Проверяет строковые представления моделей"""

        log = NotificationLog.objects.create(
            habit=self.habit,
            scheduled_at=timezone.now(),
        )

        self.assertEqual(str(self.habit), "Зарядка — models@example.com")
        self.assertIn("Зарядка", str(log))
        self.assertIn(NotificationLog.Status.PENDING, str(log))

    def test_notification_log_is_unique_per_schedule(self):
        """Проверяет уникальность уведомления по расписанию"""

        scheduled_at = timezone.now()
        NotificationLog.objects.create(
            habit=self.habit,
            scheduled_at=scheduled_at,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            NotificationLog.objects.create(
                habit=self.habit,
                scheduled_at=scheduled_at,
            )
