from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Создаёт обычных пользователей и суперпользователей"""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Создаёт пользователя с нормализованным email"""

        if not email:
            raise ValueError("Email обязателен.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Создаёт обычного пользователя"""

        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Создаёт суперпользователя и проверяет его права"""

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("У суперпользователя is_staff должен быть True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(
                "У суперпользователя is_superuser должен быть True."
            )
        return self._create_user(email, password, **extra_fields)
