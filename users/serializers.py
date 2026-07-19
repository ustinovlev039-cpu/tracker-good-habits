from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    """Проверяет данные регистрации пользователя"""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        """Определяет поля регистрации пользователя"""

        model = User
        fields = ("id", "email", "password")
        read_only_fields = ("id",)

    def create(self, validated_data):
        """Создаёт пользователя с защищённым паролем"""

        return User.objects.create_user(**validated_data)
