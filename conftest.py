from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True, scope="session")
def _fast_password_hasher() -> Iterator[None]:
    """Argon2 намеренно медленный (memory-hard) — в проде это защита, в тестах лишние секунды."""
    with override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]):
        yield


@pytest.fixture(autouse=True)
def isolated_cache() -> Iterator[None]:
    """Изолировать кэш теста, чтобы лимиты DRF не накапливались между тестами."""
    with override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": f"test-{uuid4()}",
            },
        },
    ):
        try:
            yield
        finally:
            cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    """DRF APIClient для тестов HTTP-эндпоинтов."""
    return APIClient()
