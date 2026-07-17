from rest_framework import serializers

from notifications.models import TelegramProfile


class TelegramProfileSerializer(serializers.ModelSerializer):
    bot_link = serializers.SerializerMethodField()

    class Meta:
        model = TelegramProfile
        fields = ("is_verified", "username", "connection_code", "bot_link", "updated_at")
        read_only_fields = fields

    def get_bot_link(self, obj) -> str | None:
        request = self.context.get("request")
        username = getattr(request, "telegram_bot_username", "")
        if not username:
            from django.conf import settings
            username = settings.TELEGRAM_BOT_USERNAME
        if not username:
            return None
        return f"https://t.me/{username}?start={obj.connection_code}"
