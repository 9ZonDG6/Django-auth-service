from datetime import timedelta

import pytest
from axes.models import AccessAttempt, AccessAttemptExpiration, AccessFailureLog, AccessLog
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone

pytestmark = pytest.mark.django_db


def test_cleanup_preserves_active_attempts_and_recent_logs() -> None:
    """Очистка удаляет просроченное, сохраняя активные блокировки и свежие журналы."""
    now = timezone.now()
    expired = AccessAttempt.objects.create(username="expired", failures_since_start=5)
    active = AccessAttempt.objects.create(username="active", failures_since_start=5)
    legacy = AccessAttempt.objects.create(username="without-expiration", failures_since_start=5)
    AccessAttemptExpiration.objects.create(access_attempt=expired, expires_at=now - timedelta(seconds=1))
    AccessAttemptExpiration.objects.create(access_attempt=active, expires_at=now + timedelta(minutes=15))
    for model in (AccessLog, AccessFailureLog):
        old = model.objects.create(username="old")
        model.objects.filter(pk=old.pk).update(attempt_time=now - timedelta(days=31))
        model.objects.create(username="recent")

    call_command("cleanup_axes")

    assert set(AccessAttempt.objects.values_list("pk", flat=True)) == {active.pk, legacy.pk}
    assert not AccessAttemptExpiration.objects.filter(pk=expired.pk).exists()
    for model in (AccessLog, AccessFailureLog):
        assert list(model.objects.values_list("username", flat=True)) == ["recent"]


@pytest.mark.parametrize("days", [0, -1])
def test_cleanup_rejects_invalid_retention(days: int) -> None:
    """Нулевой и отрицательный срок не допускают случайного удаления всех журналов."""
    with pytest.raises(CommandError, match="положительным"):
        call_command("cleanup_axes", days=days)


@override_settings(AXES_ENABLED=False)
def test_cleanup_skips_disabled_axes() -> None:
    """Отключённый AXES не требует очистки."""
    log = AccessLog.objects.create()
    AccessLog.objects.filter(pk=log.pk).update(attempt_time=timezone.now() - timedelta(days=31))
    call_command("cleanup_axes")
    assert AccessLog.objects.filter(pk=log.pk).exists()


def test_cleanup_custom_retention() -> None:
    """Срок хранения журналов можно изменить аргументом команды."""
    log = AccessLog.objects.create()
    AccessLog.objects.filter(pk=log.pk).update(attempt_time=timezone.now() - timedelta(days=8))
    call_command("cleanup_axes", days=7)
    assert not AccessLog.objects.exists()
