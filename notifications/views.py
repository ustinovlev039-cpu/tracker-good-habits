from drf_spectacular.utils import extend_schema
from rest_framework import permissions, response, status, views

from .models import TelegramProfile, generate_connection_code
from .serializers import TelegramProfileSerializer


@extend_schema(tags=["Telegram"], summary="Получить или обновить код привязки Telegram")
class TelegramConnectView(views.APIView):
    serializer_class = TelegramProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile, _ = TelegramProfile.objects.get_or_create(user=request.user)
        if profile.is_verified:
            return response.Response(
                TelegramProfileSerializer(profile, context={"request": request}).data,
                status=status.HTTP_200_OK,
            )
        profile.connection_code = generate_connection_code()
        profile.save(update_fields=["connection_code", "updated_at"])
        return response.Response(
            TelegramProfileSerializer(profile, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Telegram"], summary="Статус привязки Telegram")
class TelegramStatusView(views.APIView):
    serializer_class = TelegramProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile, _ = TelegramProfile.objects.get_or_create(user=request.user)
        return response.Response(TelegramProfileSerializer(profile, context={"request": request}).data)
