from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework import status

if TYPE_CHECKING:
    from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("payload", "expected", "error_type", "code"),
    [
        ({}, status.HTTP_400_BAD_REQUEST, "validation_error", "required"),
        (
            {"username": "missing", "password": "wrong"},
            status.HTTP_401_UNAUTHORIZED,
            "client_error",
            "no_active_account",
        ),
    ],
)
def test_login_error_contract(
    api_client: APIClient, payload: dict[str, str], expected: int, error_type: str, code: str
) -> None:
    """Ошибки полей и аутентификации имеют общий формат и сохраняют статус."""
    response = api_client.post("/api/v1/auth/login/", payload)
    assert response.status_code == expected
    assert response.data["type"] == error_type
    assert response.data["errors"][0]["code"] == code
    assert set(response.data["errors"][0]) == {"code", "detail", "attr"}
    if expected == status.HTTP_401_UNAUTHORIZED:
        assert response["WWW-Authenticate"].startswith("Bearer")


@override_settings(DEBUG=False)
def test_unhandled_error_hides_internal_details(api_client: APIClient) -> None:
    """Production 500 не раскрывает текст внутреннего исключения."""
    api_client.raise_request_exception = False
    with patch("apps.authentication.views.get_jwks", side_effect=RuntimeError("private diagnostic")):
        response = api_client.get("/.well-known/jwks.json")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data["type"] == "server_error"
    assert response.data["errors"][0]["code"] == "error"
    assert "private diagnostic" not in response.content.decode()
