from typing import TYPE_CHECKING

import pytest
from rest_framework import status

from apps.users.models import User

if TYPE_CHECKING:
    from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-Pass-92!"


def test_me_requires_authentication(api_client: APIClient) -> None:
    """Без токена — 401."""
    response = api_client.get("/api/v1/users/me/")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_me_returns_current_user_without_password(api_client: APIClient) -> None:
    """С валидным токеном отдаёт профиль текущего пользователя."""
    User.objects.create_user(username="meuser", password=PASSWORD, email="me@example.com")
    login = api_client.post("/api/v1/auth/login/", {"username": "meuser", "password": PASSWORD})
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    response = api_client.get("/api/v1/users/me/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["username"] == "meuser"
    assert response.data["email"] == "me@example.com"
    assert "password" not in response.data
