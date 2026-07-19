from datetime import time

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from habits.models import Habit

User = get_user_model()


class HabitApiTests(APITestCase):
    """Проверяет API управления привычками"""

    def setUp(self):
        """Создаёт пользователей и адрес списка привычек"""

        self.user = User.objects.create_user(
            email="student@example.com",
            password="strong-pass-123",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="strong-pass-123",
        )
        self.list_url = reverse("habit-list")

    def habit(self, owner=None, **kwargs):
        """Создаёт привычку для API-тестов"""

        data = {
            "owner": owner or self.user,
            "place": "Дом",
            "time": time(8),
            "action": "Разминка",
            "duration": 120,
        }
        data.update(kwargs)
        return Habit.objects.create(**data)

    def valid_payload(self, **kwargs):
        """Формирует корректные данные привычки"""

        data = {
            "place": "Дом",
            "time": "08:00:00",
            "action": "Разминка",
            "duration": 120,
        }
        data.update(kwargs)
        return data

    def authenticate(self):
        """Авторизует основного пользователя"""

        self.client.force_authenticate(self.user)

    def test_personal_list_requires_authentication(self):
        """Проверяет защиту личного списка авторизацией"""

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_sees_only_own_habits(self):
        """Проверяет выдачу только собственных привычек"""

        self.habit()
        self.habit(owner=self.other_user, action="Чтение")
        self.authenticate()

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["owner"], self.user.pk)

    def test_create_assigns_owner_and_notification_time(self):
        """Проверяет владельца и время нового напоминания"""

        self.authenticate()

        response = self.client.post(
            self.list_url,
            self.valid_payload(reward="Кофе"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        habit = Habit.objects.get(pk=response.data["id"])
        self.assertEqual(habit.owner, self.user)
        self.assertIsNotNone(habit.next_notification_at)
        self.assertEqual(response.data["owner"], self.user.pk)

    def test_retrieve_update_patch_and_delete_own_habit(self):
        """Проверяет операции с собственной привычкой"""

        habit = self.habit()
        detail_url = reverse("habit-detail", args=[habit.pk])
        self.authenticate()

        retrieved = self.client.get(detail_url)
        updated = self.client.put(
            detail_url,
            self.valid_payload(action="Йога", periodicity=2),
            format="json",
        )
        patched = self.client.patch(
            detail_url,
            {"place": "Парк"},
            format="json",
        )
        deleted = self.client.delete(detail_url)

        self.assertEqual(retrieved.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["action"], "Йога")
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.assertEqual(patched.data["place"], "Парк")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Habit.objects.filter(pk=habit.pk).exists())

    def test_other_users_habit_is_hidden_for_detail_mutations(self):
        """Проверяет защиту чужой привычки от доступа"""

        habit = self.habit(owner=self.other_user)
        detail_url = reverse("habit-detail", args=[habit.pk])
        self.authenticate()

        responses = (
            self.client.get(detail_url),
            self.client.put(detail_url, self.valid_payload(), format="json"),
            self.client.patch(detail_url, {"place": "Парк"}, format="json"),
            self.client.delete(detail_url),
        )

        self.assertTrue(
            all(
                response.status_code == status.HTTP_404_NOT_FOUND
                for response in responses
            )
        )
        self.assertTrue(Habit.objects.filter(pk=habit.pk).exists())

    def test_public_list_contains_only_public_habits_and_is_read_only(self):
        """Проверяет состав и неизменяемость публичного списка"""

        public = self.habit(
            owner=self.other_user,
            is_public=True,
            action="Публичная",
        )
        self.habit(owner=self.other_user, is_public=False, action="Скрытая")
        url = reverse("public-habits")

        response = self.client.get(url)
        post_response = self.client.post(
            url,
            self.valid_payload(),
            format="json",
        )
        patch_response = self.client.patch(
            f"{url}{public.pk}/",
            {"action": "Изменена"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], public.pk)
        self.assertEqual(
            post_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertIn(
            patch_response.status_code,
            (status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED),
        )
        public.refresh_from_db()
        self.assertEqual(public.action, "Публичная")

    def test_limit_offset_and_default_limit(self):
        """Проверяет limit, offset и размер страницы"""

        for number in range(8):
            self.habit(action=f"Привычка {number}", time=time(8, number))
        self.authenticate()

        default_response = self.client.get(self.list_url)
        limited_response = self.client.get(self.list_url, {"limit": 2})
        offset_response = self.client.get(
            self.list_url,
            {"limit": 2, "offset": 5},
        )

        self.assertEqual(default_response.data["count"], 8)
        self.assertEqual(len(default_response.data["results"]), 5)
        self.assertIsNotNone(default_response.data["next"])
        self.assertEqual(len(limited_response.data["results"]), 2)
        self.assertEqual(len(offset_response.data["results"]), 2)
        self.assertIsNotNone(offset_response.data["previous"])
        self.assertNotEqual(
            limited_response.data["results"][0]["id"],
            offset_response.data["results"][0]["id"],
        )


class HabitValidationTests(APITestCase):
    """Проверяет правила валидации привычек"""

    def setUp(self):
        """Создаёт пользователей и авторизует владельца"""

        self.user = User.objects.create_user(
            email="owner@example.com",
            password="password123",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.user)
        self.url = reverse("habit-list")

    def habit(self, owner=None, **kwargs):
        """Создаёт приятную привычку для проверок"""

        data = {
            "owner": owner or self.user,
            "place": "Дом",
            "time": time(20),
            "action": "Музыка",
            "duration": 60,
            "is_pleasant": True,
        }
        data.update(kwargs)
        return Habit.objects.create(**data)

    def payload(self, **kwargs):
        """Формирует данные полезной привычки"""

        data = {
            "place": "Дом",
            "time": "08:00:00",
            "action": "Разминка",
            "duration": 60,
        }
        data.update(kwargs)
        return data

    def assert_invalid(self, field=None, **payload):
        """Проверяет отклонение некорректных данных"""

        response = self.client.post(
            self.url,
            self.payload(**payload),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        if field:
            self.assertIn(field, response.data)

    def test_reward_and_related_habit_are_mutually_exclusive(self):
        """Проверяет несовместимость награды и связи"""

        pleasant = self.habit()
        self.assert_invalid(
            "non_field_errors",
            related_habit=pleasant.pk,
            reward="Кофе",
        )

    def test_duration_must_be_between_one_and_120(self):
        """Проверяет допустимую длительность привычки"""

        for value in (-1, 0, 121):
            with self.subTest(value=value):
                self.assert_invalid("duration", duration=value)

    def test_periodicity_must_be_between_one_and_seven(self):
        """Проверяет допустимую периодичность привычки"""

        for value in (0, 8):
            with self.subTest(value=value):
                self.assert_invalid("periodicity", periodicity=value)

    def test_related_habit_must_be_pleasant_and_owned_by_user(self):
        """Проверяет приятность и владельца связанной привычки"""

        useful = self.habit(is_pleasant=False)
        foreign = self.habit(owner=self.other_user)

        self.assert_invalid("related_habit", related_habit=useful.pk)
        self.assert_invalid("related_habit", related_habit=foreign.pk)

    def test_pleasant_habit_cannot_have_reward_or_related_habit(self):
        """Проверяет ограничения приятной привычки"""

        pleasant = self.habit(action="Другая приятная")

        self.assert_invalid("is_pleasant", is_pleasant=True, reward="Кофе")
        self.assert_invalid(
            "is_pleasant",
            is_pleasant=True,
            related_habit=pleasant.pk,
        )

    def test_habit_cannot_be_related_to_itself(self):
        """Проверяет запрет связи привычки с собой"""

        habit = self.habit()

        response = self.client.patch(
            reverse("habit-detail", args=[habit.pk]),
            {"related_habit": habit.pk, "is_pleasant": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("related_habit", response.data)

    def test_valid_useful_habits_can_use_reward_or_related_habit(self):
        """Проверяет допустимые варианты полезной привычки"""

        pleasant = self.habit()

        with_reward = self.client.post(
            self.url,
            self.payload(reward="Кофе"),
            format="json",
        )
        with_related = self.client.post(
            self.url,
            self.payload(action="Чтение", related_habit=pleasant.pk),
            format="json",
        )

        self.assertEqual(with_reward.status_code, status.HTTP_201_CREATED)
        self.assertEqual(with_related.status_code, status.HTTP_201_CREATED)

    def test_patch_cannot_bypass_existing_reward_rules(self):
        """Проверяет валидацию правил при частичном обновлении"""

        useful = self.habit(is_pleasant=False, reward="Кофе")
        pleasant = self.habit(action="Прогулка")
        detail_url = reverse("habit-detail", args=[useful.pk])

        add_related = self.client.patch(
            detail_url,
            {"related_habit": pleasant.pk},
            format="json",
        )
        make_pleasant = self.client.patch(
            detail_url,
            {"is_pleasant": True},
            format="json",
        )

        self.assertEqual(add_related.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            make_pleasant.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
