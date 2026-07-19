from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class Habit(models.Model):
    """Хранит привычку пользователя и расписание напоминаний"""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habits",
    )
    place = models.CharField(max_length=255)
    time = models.TimeField()
    action = models.CharField(max_length=255)
    is_pleasant = models.BooleanField(default=False)
    related_habit = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="use_as_reward_for",
    )
    periodicity = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        help_text="Периодичность выполнения в днях: от 1 до 7.",
    )
    reward = models.CharField(max_length=255, blank=True)
    duration = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(120)],
        help_text="Предполагаемое время выполнения в секундах.",
    )
    is_public = models.BooleanField(default=False)
    next_notification_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Задаёт сортировку и ограничения привычек"""

        ordering = ("time", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(periodicity__gte=1) & Q(periodicity__lte=7),
                name="habit_periodicity_between_1_and_7",
            ),
            models.CheckConstraint(
                condition=Q(duration__gte=1) & Q(duration__lte=120),
                name="habit_duration_between_1_and_120",
            ),
            models.CheckConstraint(
                condition=Q(related_habit__isnull=True) | Q(reward=""),
                name="habit_not_both_related_and_reward",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_pleasant=False)
                    | (Q(related_habit__isnull=True) & Q(reward=""))
                ),
                name="pleasant_habit_without_reward_or_related",
            ),
        ]

    def __str__(self):
        """Возвращает название привычки и владельца"""

        return f"{self.action} — {self.owner}"
