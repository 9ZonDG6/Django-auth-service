from datetime import timedelta
from typing import TYPE_CHECKING, override

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    """Очистка истёкших попыток и старых журналов AXES."""

    help = "Удалить истёкшие попытки AXES и журналы старше --days (по умолчанию 30)."

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        """Добавить срок хранения журналов."""
        parser.add_argument("--days", type=int, default=30)

    def handle(self, *_args: object, **options: object) -> None:
        """Сохранить активные блокировки и удалить только устаревшие записи."""
        days = options["days"]
        if not isinstance(days, int) or days < 1:
            raise CommandError("--days должен быть положительным целым числом.")
        if not settings.AXES_ENABLED:
            self.stdout.write("AXES отключён, очистка пропущена.")
            return
        if not settings.AXES_USE_ATTEMPT_EXPIRATION:
            raise CommandError("Для очистки требуется AXES_USE_ATTEMPT_EXPIRATION=True.")

        now = timezone.now()
        attempts = apps.get_model("axes", "AccessAttempt")
        _, deleted = attempts.objects.filter(expiration__expires_at__lte=now).delete()
        self.stdout.write(f"Удалено истёкших попыток: {deleted.get('axes.AccessAttempt', 0)}")
        for model_name in ("AccessLog", "AccessFailureLog"):
            model = apps.get_model("axes", model_name)
            count, _ = model.objects.filter(attempt_time__lt=now - timedelta(days=days)).delete()
            self.stdout.write(f"Удалено {model_name}: {count}")
