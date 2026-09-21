from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.test import Client, override_settings
from health_check.exceptions import ServiceUnavailable


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("endpoint", ["live", "ready"])
def test_health_is_public_and_not_cached(client: Client, endpoint: str) -> None:
    """Пробы работают с ошибочным JWT, по HTTP, и запрещают кеширование."""
    with override_settings(SECURE_SSL_REDIRECT=True):
        response = client.get(f"/health/{endpoint}/?format=json", HTTP_AUTHORIZATION="Bearer invalid")
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == (0 if endpoint == "live" else 1)
    assert all(value == "OK" for value in response.json().values())
    assert "no-store" in response["Cache-Control"]


@pytest.mark.django_db(transaction=True)
def test_database_failure_only_affects_readiness(client: Client) -> None:
    """Сбой БД отражается в readiness и не делает процесс неживым."""
    with patch("health_check.Database.run", side_effect=ServiceUnavailable("private connection details")):
        response = client.get("/health/ready/?format=json")
        live = client.get("/health/live/")
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert len(response.json()) == 1
    assert "private connection details" in next(iter(response.json().values()))
    assert live.status_code == HTTPStatus.OK
