from typing import TYPE_CHECKING

import jwt
import pytest
from django.conf import settings
from rest_framework import status

from apps.users.models import User

if TYPE_CHECKING:
    from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-Pass-92!"
LOGIN_URL = "/api/v1/auth/login/"


def _create_user(**extra_fields: str) -> User:
    return User.objects.create_user(username="loginuser", password=PASSWORD, **extra_fields)


def test_login_returns_token_pair_with_custom_claims(api_client: APIClient) -> None:
    """Успешный логин отдаёт access/refresh с кастомными claims (roles/username/staff/superuser)."""
    user = _create_user(email="loginuser@example.com")
    user.groups.create(name="admin")

    response = api_client.post(LOGIN_URL, {"username": "loginuser", "password": PASSWORD})

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data

    claims = jwt.decode(response.data["access"], options={"verify_signature": False})
    assert claims["username"] == "loginuser"
    assert claims["roles"] == ["admin"]
    assert claims["is_staff"] is False
    assert claims["is_superuser"] is False


def test_login_with_wrong_password_is_rejected(api_client: APIClient) -> None:
    """Неверный пароль — 401, токены не выдаются."""
    _create_user()

    response = api_client.post(LOGIN_URL, {"username": "loginuser", "password": "wrong-password"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_does_not_trim_password_whitespace(api_client: APIClient) -> None:
    """Пароль с пробелами по краям не должен обрезаться при валидации."""
    User.objects.create_user(username="spaceuser", password="  Sp4ce-Pass!  ")

    with_spaces = api_client.post(LOGIN_URL, {"username": "spaceuser", "password": "  Sp4ce-Pass!  "})
    trimmed = api_client.post(LOGIN_URL, {"username": "spaceuser", "password": "Sp4ce-Pass!"})

    assert with_spaces.status_code == status.HTTP_200_OK
    assert trimmed.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_updates_last_login(api_client: APIClient) -> None:
    """last_login должен обновляться при JWT-логине (UPDATE_LAST_LOGIN)."""
    user = _create_user()
    assert user.last_login is None

    api_client.post(LOGIN_URL, {"username": "loginuser", "password": PASSWORD})

    user.refresh_from_db()
    assert user.last_login is not None


def test_repeated_failed_logins_are_locked_out_by_axes(api_client: APIClient) -> None:
    """django-axes блокирует брутфорс и через API-логин, а не только через admin."""
    _create_user()

    for _ in range(settings.AXES_FAILURE_LIMIT):
        api_client.post(LOGIN_URL, {"username": "loginuser", "password": "wrong-password"})

    response = api_client.post(LOGIN_URL, {"username": "loginuser", "password": PASSWORD})

    assert response.status_code == settings.AXES_HTTP_RESPONSE_CODE


def test_lockout_is_not_bypassed_by_rotating_user_agent(api_client: APIClient) -> None:
    """Лок-аут привязан к username и IP — подмена User-Agent не помогает обойти лимит."""
    _create_user()

    for i in range(settings.AXES_FAILURE_LIMIT):
        api_client.post(LOGIN_URL, {"username": "loginuser", "password": "wrong-password"}, HTTP_USER_AGENT=f"ua-{i}")

    response = api_client.post(LOGIN_URL, {"username": "loginuser", "password": PASSWORD})

    assert response.status_code == settings.AXES_HTTP_RESPONSE_CODE


def test_lockout_does_not_affect_other_users_on_same_ip(api_client: APIClient) -> None:
    """Лок-аут по чужому аккаунту с того же IP не должен мешать другим юзерам."""
    _create_user()
    User.objects.create_user(username="otheruser", password=PASSWORD)

    for _ in range(settings.AXES_FAILURE_LIMIT):
        api_client.post(LOGIN_URL, {"username": "loginuser", "password": "wrong-password"})

    response = api_client.post(LOGIN_URL, {"username": "otheruser", "password": PASSWORD})

    assert response.status_code == status.HTTP_200_OK


def test_lockout_does_not_affect_same_user_on_other_ip(api_client: APIClient) -> None:
    """Заблокированная пара username/IP не мешает входу в аккаунт с другого IP."""
    _create_user()

    for _ in range(settings.AXES_FAILURE_LIMIT):
        api_client.post(
            LOGIN_URL,
            {"username": "loginuser", "password": "wrong-password"},
            REMOTE_ADDR="192.0.2.1",
        )

    blocked = api_client.post(
        LOGIN_URL,
        {"username": "loginuser", "password": PASSWORD},
        REMOTE_ADDR="192.0.2.1",
    )
    allowed = api_client.post(
        LOGIN_URL,
        {"username": "loginuser", "password": PASSWORD},
        REMOTE_ADDR="192.0.2.2",
    )

    assert blocked.status_code == settings.AXES_HTTP_RESPONSE_CODE
    assert allowed.status_code == status.HTTP_200_OK

    still_blocked = api_client.post(
        LOGIN_URL,
        {"username": "loginuser", "password": PASSWORD},
        REMOTE_ADDR="192.0.2.1",
    )
    assert still_blocked.status_code == settings.AXES_HTTP_RESPONSE_CODE


@pytest.mark.parametrize("request_format", ["json", "multipart"])
@pytest.mark.parametrize("username", ["loginuser", "  loginuser  "])
def test_successful_login_resets_current_pair(api_client: APIClient, request_format: str, username: str) -> None:
    """Успешный вход сбрасывает ошибки своей пары для JSON и формы."""
    _create_user()
    for _ in range(settings.AXES_FAILURE_LIMIT - 1):
        api_client.post(LOGIN_URL, {"username": "loginuser", "password": "wrong-password"})

    success = api_client.post(LOGIN_URL, {"username": username, "password": PASSWORD}, format=request_format)
    assert success.status_code == status.HTTP_200_OK

    failure = api_client.post(LOGIN_URL, {"username": "loginuser", "password": "wrong-password"})
    assert failure.status_code == status.HTTP_401_UNAUTHORIZED
