import requests
from django.conf import settings


class TelegramError(RuntimeError):
    """Описывает ошибку обращения к Telegram API"""


def send_telegram_message(chat_id, text):
    """Отправляет текстовое сообщение через Telegram API"""

    if not settings.TELEGRAM_BOT_TOKEN:
        raise TelegramError("TELEGRAM_BOT_TOKEN не задан.")

    url = (
        "https://api.telegram.org/"
        f"bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    )
    response = requests.post(
        url,
        json={"chat_id": chat_id, "text": text},
        timeout=15,
    )
    try:
        payload = response.json()
    except ValueError as exc:
        raise TelegramError("Telegram вернул некорректный ответ.") from exc
    if not response.ok or not payload.get("ok"):
        raise TelegramError(payload.get("description", "Ошибка Telegram API."))
    return payload["result"]


def build_habit_message(habit):
    """Формирует текст напоминания о привычке"""

    lines = [
        "Напоминание о привычке",
        "",
        f"Действие: {habit.action}",
        f"Место: {habit.place}",
        f"Время: {habit.time.strftime('%H:%M')}",
        f"Продолжительность: {habit.duration} сек.",
    ]
    if habit.related_habit:
        lines.extend(["", f"После выполнения: {habit.related_habit.action}"])
    elif habit.reward:
        lines.extend(["", f"Вознаграждение: {habit.reward}"])
    return "\n".join(lines)
