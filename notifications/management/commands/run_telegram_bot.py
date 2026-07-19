import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from notifications.models import TelegramProfile


class Command(BaseCommand):
    """Запускает Telegram-бота в режиме long polling"""

    help = "Запускает Telegram-бота в режиме long polling"

    def handle(self, *args, **options):
        """Получает обновления Telegram и передаёт их обработчику"""

        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            raise CommandError("Укажите TELEGRAM_BOT_TOKEN в .env")

        base_url = f"https://api.telegram.org/bot{token}"
        offset = None
        self.stdout.write(self.style.SUCCESS("Telegram_бот запущен."))

        while True:
            try:
                params = {"timeout": 30}
                if offset is not None:
                    params["offset"] = offset
                response = requests.get(
                    f"{base_url}/getUpdates",
                    params=params,
                    timeout=40,
                )
                response.raise_for_status()
                payload = response.json()
                for update in payload.get("result", []):
                    offset = update["update_id"] + 1
                    self.process_update(base_url, update)
            except requests.RequestException as exc:
                self.stderr.write(f"Ошибка Telegram: {exc}")
                time.sleep(5)

    def process_update(self, base_url, update):
        """Привязывает Telegram-чат по команде start"""

        message = update.get("message") or {}
        text = (message.get("text") or "").strip()
        chat = message.get("chat") or {}
        if not text.startswith("/start") or not chat.get("id"):
            return

        parts = text.split(maxsplit=1)
        if len(parts) != 2:
            self.send(
                base_url,
                chat["id"],
                "Откройте ссылку привязки из приложения "
                "или отправьте /start КОД",
            )
            return

        code = parts[1].strip().upper()
        try:
            profile = TelegramProfile.objects.get(connection_code=code)
        except TelegramProfile.DoesNotExist:
            self.send(
                base_url,
                chat["id"],
                "Код привязки не найден или устарел",
            )
            return

        existing = (
            TelegramProfile.objects.filter(chat_id=chat["id"])
            .exclude(pk=profile.pk)
            .first()
        )
        if existing:
            existing.chat_id = None
            existing.username = ""
            existing.is_verified = False
            existing.save(
                update_fields=[
                    "chat_id",
                    "username",
                    "is_verified",
                    "updated_at",
                ]
            )

        profile.chat_id = chat["id"]
        profile.username = chat.get("username", "")
        profile.is_verified = True
        profile.save(
            update_fields=[
                "chat_id",
                "username",
                "is_verified",
                "updated_at",
            ]
        )
        self.send(
            base_url,
            chat["id"],
            "Telegram успешно подключён. "
            "Напоминания будут приходить в этот чат",
        )

    def send(self, base_url, chat_id, text):
        """Отправляет сообщение в Telegram-чат"""

        response = requests.post(
            f"{base_url}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=15,
        )
        response.raise_for_status()
