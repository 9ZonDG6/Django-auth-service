from typing import TYPE_CHECKING

import pytest
from rest_framework import status

from apps.users.models import User

if TYPE_CHECKING:
    from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

OLD_PASSWORD = "Old-Str0ng-Pass-92!"
NEW_PASSWORD = "New-Str0nger-Pass-93!"
CHANGE_PASSWORD_URL = "/api/v1/users/change-password/"


def _login(api_client: APIClient, *, username: str = "cpuser") -> dict:
    User.objects.create_user(username=username, password=OLD_PASSWORD)
    response = api_client.post("/api/v1/auth/login/", {"username": username, "password": OLD_PASSWORD})
    return response.data


def test_change_password_requires_authentication(api_client: APIClient) -> None:
    """Без токена — 401."""
    response = api_client.post(CHANGE_PASSWORD_URL, {"old_password": OLD_PASSWORD, "new_password": NEW_PASSWORD})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_change_password_rejects_wrong_old_password(api_client: APIClient) -> None:
    """Неверный текущий пароль — 400, пароль не меняется."""
    tokens = _login(api_client)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = api_client.post(CHANGE_PASSWORD_URL, {"old_password": "wrong", "new_password": NEW_PASSWORD})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_change_password_success_allows_relogin_with_new_password(api_client: APIClient) -> None:
    """После успешной смены пароля старый больше не подходит, новый — работает."""
    tokens = _login(api_client)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = api_client.post(
        CHANGE_PASSWORD_URL,
        {"old_password": OLD_PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == status.HTTP_200_OK

    api_client.credentials()
    old_login = api_client.post("/api/v1/auth/login/", {"username": "cpuser", "password": OLD_PASSWORD})
    assert old_login.status_code == status.HTTP_401_UNAUTHORIZED

    new_login = api_client.post("/api/v1/auth/login/", {"username": "cpuser", "password": NEW_PASSWORD})
    assert new_login.status_code == status.HTTP_200_OK


def test_change_password_revokes_old_refresh_token(api_client: APIClient) -> None:
    """Смена пароля отзывает выданные refresh-токены — старый больше не работает."""
    tokens = _login(api_client)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    api_client.post(CHANGE_PASSWORD_URL, {"old_password": OLD_PASSWORD, "new_password": NEW_PASSWORD})

    api_client.credentials()
    response = api_client.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_change_password_invalidates_old_access_token_immediately(api_client: APIClient) -> None:
    """CHECK_REVOKE_TOKEN: старый access отваливается сразу, не ждёт истечения TTL."""
    tokens = _login(api_client)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    api_client.post(CHANGE_PASSWORD_URL, {"old_password": OLD_PASSWORD, "new_password": NEW_PASSWORD})

    response = api_client.get("/api/v1/users/me/")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_change_password_updates_updated_at(api_client: APIClient) -> None:
    """updated_at должен меняться при смене пароля, а не только password."""
    tokens = _login(api_client)
    user = User.objects.get(username="cpuser")
    updated_at_before = user.updated_at
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    api_client.post(CHANGE_PASSWORD_URL, {"old_password": OLD_PASSWORD, "new_password": NEW_PASSWORD})

    user.refresh_from_db()
    assert user.updated_at != updated_at_before


@pytest.mark.parametrize("password", [" New-Str0ng!", "New-Str0ng! ", "New Str0ng!", "New\tStr0ng!", "New\nStr0ng!"])
def test_change_password_trims_password_edges(api_client: APIClient, password: str) -> None:
    """Обрезаются края нового пароля, пробельные символы внутри сохраняются."""
    tokens = _login(api_client)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    response = api_client.post(CHANGE_PASSWORD_URL, {"old_password": f" {OLD_PASSWORD} ", "new_password": password})
    assert response.status_code == status.HTTP_200_OK
    assert User.objects.get(username="cpuser").check_password(password.strip())
