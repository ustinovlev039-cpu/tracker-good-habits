from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, viewsets

from habits.models import Habit
from habits.serializers import HabitSerializer, PublicHabitSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Привычки"],
        summary="Список привычек текущего пользователя",
    ),
    retrieve=extend_schema(
        tags=["Привычки"],
        summary="Получить свою привычку",
    ),
    create=extend_schema(tags=["Привычки"], summary="Создать привычку"),
    update=extend_schema(
        tags=["Привычки"],
        summary="Полностью изменить привычку",
    ),
    partial_update=extend_schema(
        tags=["Привычки"],
        summary="Частично изменить привычку",
    ),
    destroy=extend_schema(tags=["Привычки"], summary="Удалить привычку"),
)
class HabitViewSet(viewsets.ModelViewSet):
    """Управляет привычками текущего пользователя"""

    queryset = Habit.objects.none()
    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Возвращает только привычки текущего пользователя"""

        return Habit.objects.filter(owner=self.request.user).select_related(
            "related_habit"
        )

    def perform_create(self, serializer):
        """Назначает текущего пользователя владельцем привычки"""

        serializer.save(owner=self.request.user)


@extend_schema(tags=["Привычки"], summary="Список публичных привычек")
class PublicHabitListView(generics.ListAPIView):
    """Возвращает доступные всем публичные привычки"""

    serializer_class = PublicHabitSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Habit.objects.filter(is_public=True).select_related("owner")
