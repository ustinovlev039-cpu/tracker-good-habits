from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions

from .serializers import RegistrationSerializer


@extend_schema(tags=["Пользователи"], summary="Регистрация пользователя")
class RegistrationView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.AllowAny]
