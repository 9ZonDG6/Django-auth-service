import re
from http import HTTPStatus

import pytest
from django.conf import settings
from django.test import Client, override_settings

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("path", ["/admin/login/", "/api/docs/", "/api/redoc/", "/health/live/"])
def test_csp_report_only_is_default(client: Client, path: str) -> None:
    """Политика наблюдения покрывает все интерфейсы, без исключений URL."""
    response = client.get(path)
    assert response.status_code == HTTPStatus.OK
    assert "Content-Security-Policy" not in response
    policy = response["Content-Security-Policy-Report-Only"]
    assert "default-src 'none'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "unsafe-inline" not in policy
    assert "unsafe-eval" not in policy


@pytest.mark.parametrize("path", ["/api/docs/", "/api/redoc/"])
def test_documentation_has_unique_matching_nonce(client: Client, path: str) -> None:
    """Nonce в шаблоне совпадает с заголовком и меняется между запросами."""
    first = client.get(path)
    second = client.get(path)
    first_nonce = re.search(r'nonce="([^"]+)"', first.content.decode())
    second_nonce = re.search(r'nonce="([^"]+)"', second.content.decode())
    assert first_nonce is not None
    assert second_nonce is not None
    assert first_nonce[1] != second_nonce[1]
    assert f"'nonce-{first_nonce[1]}'" in first["Content-Security-Policy-Report-Only"]
    assert "fonts.googleapis.com" not in first.content.decode()


def test_swagger_initialization_is_external(client: Client) -> None:
    """Инициализация Swagger загружается отдельным ответом того же endpoint."""
    page = client.get("/api/docs/")
    assert '<script src="/api/docs/?script="></script>' in page.content.decode()
    script = client.get("/api/docs/?script=")
    assert script.status_code == HTTPStatus.OK
    assert script["Content-Type"].startswith("application/javascript")
    assert "SwaggerUIBundle" in script.content.decode()


def test_enforcing_policy_uses_enforcing_header(client: Client) -> None:
    """При включении блокировки middleware отправляет соответствующий заголовок."""
    with override_settings(
        CONTENT_SECURITY_POLICY=settings.CONTENT_SECURITY_POLICY_REPORT_ONLY,
        CONTENT_SECURITY_POLICY_REPORT_ONLY=None,
    ):
        response = client.get("/api/docs/")
    assert "Content-Security-Policy" in response
    assert "Content-Security-Policy-Report-Only" not in response
