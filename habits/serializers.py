from rest_framework import serializers

from .models import Habit
from .services import calculate_next_notification


class HabitSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Habit
        fields = (
            "id",
            "owner",
            "place",
            "time",
            "action",
            "is_pleasant",
            "related_habit",
            "periodicity",
            "reward",
            "duration",
            "is_public",
            "next_notification_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "owner", "next_notification_at", "created_at", "updated_at")

    def _effective(self, attrs, field, default=None):
        if field in attrs:
            return attrs[field]
        if self.instance is not None:
            return getattr(self.instance, field)
        return default

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        related_habit = self._effective(attrs, "related_habit")
        reward = self._effective(attrs, "reward", "") or ""
        is_pleasant = self._effective(attrs, "is_pleasant", False)
        duration = self._effective(attrs, "duration")
        periodicity = self._effective(attrs, "periodicity", 1)

        errors = {}
        if related_habit and reward:
            errors["non_field_errors"] = [
                "Нельзя одновременно указывать связанную привычку и вознаграждение."
            ]
        if duration is not None and not 1 <= duration <= 120:
            errors["duration"] = ["Время выполнения должно быть от 1 до 120 секунд."]
        if periodicity is not None and not 1 <= periodicity <= 7:
            errors["periodicity"] = ["Периодичность должна быть от 1 до 7 дней."]
        if related_habit:
            if not related_habit.is_pleasant:
                errors["related_habit"] = ["Связанная привычка должна быть приятной."]
            elif user and related_habit.owner_id != user.id:
                errors["related_habit"] = ["Нельзя использовать чужую привычку как связанную."]
            elif self.instance and related_habit.pk == self.instance.pk:
                errors["related_habit"] = ["Привычку нельзя связать саму с собой."]
        if is_pleasant and (related_habit or reward):
            errors["is_pleasant"] = [
                "У приятной привычки не может быть вознаграждения или связанной привычки."
            ]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        habit = Habit(**validated_data)
        habit.next_notification_at = calculate_next_notification(habit.time, habit.periodicity)
        habit.save()
        return habit

    def update(self, instance, validated_data):
        schedule_changed = "time" in validated_data or "periodicity" in validated_data
        instance = super().update(instance, validated_data)
        if schedule_changed:
            instance.next_notification_at = calculate_next_notification(instance.time, instance.periodicity)
            instance.save(update_fields=["next_notification_at", "updated_at"])
        return instance


class PublicHabitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Habit
        fields = (
            "id",
            "place",
            "time",
            "action",
            "is_pleasant",
            "periodicity",
            "reward",
            "duration",
            "created_at",
        )
