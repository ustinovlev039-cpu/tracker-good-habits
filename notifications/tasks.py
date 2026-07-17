from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from habits.models import Habit
from notifications.models import NotificationLog
from notifications.telegram import send_telegram_message, build_habit_message


@shared_task
def send_due_habit_reminders():
    due_ids = list(
        Habit.objects.filter(
            next_notification_at__isnull=False,
            next_notification_at__lte=timezone.now(),
            owner__telegram_profile__is_verified=True,
            owner__telegram_profile__chat_id__isnull=False,
        ).values_list("id", flat=True)
    )

    sent = 0
    failed = 0
    for habit_id in due_ids:
        with transaction.atomic():
            habit = (
                Habit.objects.select_for_update()
                .select_related("owner__telegram_profile", "related_habit")
                .get(pk=habit_id)
            )
            scheduled_at = habit.next_notification_at
            if scheduled_at is None or scheduled_at > timezone.now():
                continue

            log, created = NotificationLog.objects.get_or_create(
                habit=habit,
                scheduled_at=scheduled_at,
            )
            if not created and log.status == NotificationLog.Status.SENT:
                continue

            try:
                result = send_telegram_message(
                    habit.owner.telegram_profile.chat_id,
                    build_habit_message(habit),
                )
                log.status = NotificationLog.Status.SENT
                log.sent_at = timezone.now()
                log.telegram_message_id = result.get("message_id")
                log.error_message = ""
                sent += 1
            except Exception as exc:  # Celery должен сохранить ошибку и продолжить остальные привычки
                log.status = NotificationLog.Status.FAILED
                log.error_message = str(exc)
                failed += 1
            log.save()

            next_at = scheduled_at + timedelta(days=habit.periodicity)
            now = timezone.now()
            while next_at <= now:
                next_at += timedelta(days=habit.periodicity)
            habit.next_notification_at = next_at
            habit.save(update_fields=["next_notification_at", "updated_at"])

    return {"sent": sent, "failed": failed}
