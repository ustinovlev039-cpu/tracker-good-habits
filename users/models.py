from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    """Представляет пользователя с email вместо username"""

    username = None
    email = models.EmailField("email", unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        """Возвращает email пользователя"""

        return self.email
