from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class RegistrationAndJwtTests(APITestCase):
    """Проверяет регистрацию и JWT-авторизацию"""

    def test_successful_registration_hashes_password_and_hides_it(self):
        """Проверяет безопасное сохранение пароля"""

        response = self.client.post(
            reverse("register"),
            {"email": "new@example.com", "password": "strong-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.data)
        user = User.objects.get(email="new@example.com")
        self.assertNotEqual(user.password, "strong-password")
        self.assertTrue(user.check_password("strong-password"))

    def test_registration_rejects_invalid_data(self):
        """Проверяет отклонение некорректной регистрации"""

        invalid_payloads = (
            {"email": "not-an-email", "password": "strong-password"},
            {"email": "short@example.com", "password": "short"},
            {"password": "strong-password"},
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    reverse("register"),
                    payload,
                    format="json",
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

    def test_duplicate_email_is_rejected(self):
        """Проверяет запрет повторного email"""

        User.objects.create_user(
            email="exists@example.com",
            password="strong-password",
        )

        response = self.client.post(
            reverse("register"),
            {"email": "exists@example.com", "password": "another-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_jwt_returns_access_and_refresh_tokens(self):
        """Проверяет выдачу access и refresh токенов"""

        User.objects.create_user(
            email="jwt@example.com",
            password="strong-password",
        )

        response = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "jwt@example.com", "password": "strong-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_jwt_rejects_wrong_password(self):
        """Проверяет отказ JWT при неверном пароле"""

        User.objects.create_user(
            email="jwt@example.com",
            password="strong-password",
        )

        response = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "jwt@example.com", "password": "wrong-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserManagerAndModelTests(TestCase):
    """Проверяет модель и менеджер пользователей"""

    def test_create_user_sets_expected_flags(self):
        """Проверяет права обычного пользователя"""

        user = User.objects.create_user(
            email="USER@EXAMPLE.COM",
            password="password123",
        )

        self.assertEqual(user.email, "USER@example.com")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(str(user), "USER@example.com")

    def test_create_user_requires_email(self):
        """Проверяет обязательность email"""

        with self.assertRaisesMessage(ValueError, "Email обязателен"):
            User.objects.create_user(email="", password="password123")

    def test_create_superuser_sets_expected_flags(self):
        """Проверяет права суперпользователя"""

        user = User.objects.create_superuser(
            email="admin@example.com",
            password="password123",
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_rejects_invalid_flags(self):
        """Проверяет обязательные права суперпользователя"""

        with self.assertRaisesMessage(ValueError, "is_staff"):
            User.objects.create_superuser(
                email="staff@example.com",
                password="password123",
                is_staff=False,
            )
        with self.assertRaisesMessage(ValueError, "is_superuser"):
            User.objects.create_superuser(
                email="admin@example.com",
                password="password123",
                is_superuser=False,
            )
