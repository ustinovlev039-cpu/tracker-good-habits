from datetime import time

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from habits.models import Habit

User = get_user_model()


class HabitApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="student@example.com", password="strong-pass-123")
        self.other_user = User.objects.create_user(email="other@example.com", password="strong-pass-123")
        self.client.force_authenticate(self.user)

    def test_user_sees_only_own_habits(self):
        Habit.objects.create(owner=self.user, place="Дом", time=time(8), action="Разминка", duration=120)
        Habit.objects.create(owner=self.other_user, place="Дом", time=time(9), action="Чтение", duration=60)
        response = self.client.get("/api/habits/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_cannot_set_reward_and_related_habit_together(self):
        pleasant = Habit.objects.create(
            owner=self.user,
            place="Дом",
            time=time(20),
            action="Послушать музыку",
            duration=120,
            is_pleasant=True,
        )
        response = self.client.post(
            "/api/habits/",
            {
                "place": "Дом",
                "time": "08:00:00",
                "action": "Разминка",
                "duration": 120,
                "related_habit": pleasant.pk,
                "reward": "Кофе",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duration_cannot_exceed_120_seconds(self):
        response = self.client.post(
            "/api/habits/",
            {
                "place": "Дом",
                "time": "08:00:00",
                "action": "Разминка",
                "duration": 121,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
