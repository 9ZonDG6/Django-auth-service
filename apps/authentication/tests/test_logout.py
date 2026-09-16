from typing import TYPE_CHECKING

import pytest
from rest_framework import status

from apps.users.models import User

if TYPE_CHECKING:
    from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-Pass-92!"


def _login(api_client: APIClient) -> dict:
    User.objects.create_user(username="logoutuser", password=PASSWORD)
    response = api_client.post("/api/v1/auth/login/", {"username": "logoutuser", "password": PASSWORD})
    return response.data


def test_logout_requires_authentication(api_client: APIClient) -> None:
    """Без access-токена logout недоступен."""
    response = api_client.post("/api/v1/auth/logout/", {"refresh": "whatever"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_logout_blacklists_refresh_token(api_client: APIClient) -> None:
    """После logout тот же refresh больше нельзя использовать."""
    tokens = _login(api_client)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = api_client.post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]})
    assert response.status_code == status.HTTP_205_RESET_CONTENT

    reuse_response = api_client.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]})
    assert reuse_response.status_code == status.HTTP_401_UNAUTHORIZED


def test_logout_with_already_blacklisted_token_returns_400(api_client: APIClient) -> None:
    """Повторный logout тем же refresh-токеном — понятная ошибка, не 500."""
    tokens = _login(api_client)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    api_client.post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]})

    response = api_client.post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_logout_rejects_another_users_refresh_token(api_client: APIClient) -> None:
    """Нельзя отозвать чужой refresh-токен, даже если он каким-то образом известен."""
    victim_tokens = _login(api_client)
    User.objects.create_user(username="attacker", password=PASSWORD)
    attacker_login = api_client.post("/api/v1/auth/login/", {"username": "attacker", "password": PASSWORD})
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {attacker_login.data['access']}")

    response = api_client.post("/api/v1/auth/logout/", {"refresh": victim_tokens["refresh"]})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    api_client.credentials()
    still_valid = api_client.post("/api/v1/auth/refresh/", {"refresh": victim_tokens["refresh"]})
    assert still_valid.status_code == status.HTTP_200_OK
