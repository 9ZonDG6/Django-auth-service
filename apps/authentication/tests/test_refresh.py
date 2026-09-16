from typing import TYPE_CHECKING

import jwt
import pytest
from rest_framework import status

from apps.users.models import User

if TYPE_CHECKING:
    from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-Pass-92!"


def _login(api_client: APIClient) -> dict:
    User.objects.create_user(username="refreshuser", password=PASSWORD)
    response = api_client.post("/api/v1/auth/login/", {"username": "refreshuser", "password": PASSWORD})
    return response.data


def test_refresh_returns_new_token_pair(api_client: APIClient) -> None:
    """Refresh отдаёт новый access и новый refresh."""
    tokens = _login(api_client)

    response = api_client.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]})

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert response.data["refresh"] != tokens["refresh"]


def test_refresh_with_garbage_token_is_rejected(api_client: APIClient) -> None:
    """Мусор вместо токена — 401, а не 500."""
    response = api_client.post("/api/v1/auth/refresh/", {"refresh": "not-a-real-token"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_rotation_blacklists_old_token(api_client: APIClient) -> None:
    """Старый refresh нельзя использовать повторно после ротации."""
    tokens = _login(api_client)

    api_client.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]})
    reuse_response = api_client.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]})

    assert reuse_response.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_reflects_current_roles_not_stale_claims(api_client: APIClient) -> None:
    """Отозванная роль не должна жить в токене до истечения refresh — только до следующего refresh."""
    user = User.objects.create_user(username="roleuser", password=PASSWORD)
    group = user.groups.create(name="admin")
    login = api_client.post("/api/v1/auth/login/", {"username": "roleuser", "password": PASSWORD})
    claims_at_login = jwt.decode(login.data["access"], options={"verify_signature": False})
    assert claims_at_login["roles"] == ["admin"]

    user.groups.remove(group)
    response = api_client.post("/api/v1/auth/refresh/", {"refresh": login.data["refresh"]})

    claims_after_refresh = jwt.decode(response.data["access"], options={"verify_signature": False})
    assert claims_after_refresh["roles"] == []
