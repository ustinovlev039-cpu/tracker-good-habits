from django.urls import path
from rest_framework.routers import DefaultRouter

from habits.views import HabitViewSet, PublicHabitListView

router = DefaultRouter()
router.register("", HabitViewSet, basename="habit")

urlpatterns = [
    path("public/", PublicHabitListView.as_view(), name="public-habits"),
]
urlpatterns += router.urls
