from rest_framework.pagination import LimitOffsetPagination


class HabitPagination(LimitOffsetPagination):
    """Пагинация привычек в формате limit/offset/count/results"""

    default_limit = 5
    max_limit = 100
