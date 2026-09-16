from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.users.models import User

if TYPE_CHECKING:
    from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
PASSWORD = "Str0ng-Pass-92!"


@pytest.mark.parametrize("endpoint", ["api", "admin"])
def test_lockout_expires_without_extension(api_client: APIClient, endpoint: str) -> None:
    """Попытки во время блокировки не сдвигают срок её окончания в API и admin."""
    User.objects.create_user(username="axesuser", password=PASSWORD, is_staff=True)
    url = "/api/v1/auth/login/" if endpoint == "api" else reverse("admin:login")
    started = timezone.now()
    credentials = {"username": "axesuser", "password": PASSWORD}

    with (
        patch("django.utils.timezone.now", return_value=started),
        patch("axes.attempts.now", return_value=started),
        patch("axes.handlers.proxy.now", return_value=started),
    ):
        for _ in range(settings.AXES_FAILURE_LIMIT):
            locked = api_client.post(url, {**credentials, "password": "wrong-password"}, format="multipart")
        assert locked.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    before_expiry = started + settings.AXES_COOLOFF_TIME - timedelta(seconds=1)
    with (
        patch("django.utils.timezone.now", return_value=before_expiry),
        patch("axes.attempts.now", return_value=before_expiry),
        patch("axes.handlers.proxy.now", return_value=before_expiry),
    ):
        for password in ("wrong-password", PASSWORD):
            blocked = api_client.post(url, {**credentials, "password": password}, format="multipart")
            assert blocked.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "_auth_user_id" not in api_client.session

    after_expiry = started + settings.AXES_COOLOFF_TIME + timedelta(seconds=1)
    with (
        patch("django.utils.timezone.now", return_value=after_expiry),
        patch("axes.attempts.now", return_value=after_expiry),
        patch("axes.handlers.proxy.now", return_value=after_expiry),
    ):
        allowed = api_client.post(url, credentials, format="multipart")
        expected = status.HTTP_200_OK if endpoint == "api" else status.HTTP_302_FOUND
        assert allowed.status_code == expected


@pytest.mark.parametrize("username", ["axesuser", "nonexistent"])
@pytest.mark.parametrize("request_format", ["json", "multipart"])
def test_api_lockout_response(api_client: APIClient, username: str, request_format: str) -> None:
    """API возвращает одинаковый JSON 429 для существующего и неизвестного логина."""
    User.objects.create_user(username="axesuser", password=PASSWORD)
    for _ in range(settings.AXES_FAILURE_LIMIT):
        response = api_client.post(
            "/api/v1/auth/login/", {"username": username, "password": "wrong-password"}, format=request_format
        )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response["Content-Type"].startswith("application/json")
    assert response.json() == {"detail": "Слишком много неудачных попыток входа."}


def test_admin_lockout_response(api_client: APIClient) -> None:
    """Admin возвращает сообщение о блокировке и не создаёт авторизованную сессию."""
    User.objects.create_user(username="axesuser", password=PASSWORD, is_staff=True)
    for _ in range(settings.AXES_FAILURE_LIMIT):
        response = api_client.post(
            reverse("admin:login"), {"username": "axesuser", "password": "wrong-password"}, format="multipart"
        )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert str(settings.AXES_COOLOFF_MESSAGE) in response.content.decode()
    assert "_auth_user_id" not in api_client.session
