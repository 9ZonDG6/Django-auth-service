from typing import TYPE_CHECKING

import jwt
import pytest
from rest_framework import status

from apps.users.models import User

if TYPE_CHECKING:
    from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-Pass-92!"


def test_jwks_is_public_and_well_formed(api_client: APIClient) -> None:
    """JWKS доступен без авторизации и содержит корректно оформленный RSA-ключ."""
    response = api_client.get("/auth/jwks.json")

    assert response.status_code == status.HTTP_200_OK
    keys = response.data["keys"]
    assert len(keys) == 1
    assert keys[0]["kty"] == "RSA"
    assert {"kid", "alg", "use", "n", "e"} <= keys[0].keys()


def test_jwks_key_verifies_a_real_login_token(api_client: APIClient) -> None:
    """Round-trip: подпись токена из /login реально проверяется по ключу из /jwks.json."""
    User.objects.create_user(username="jwksuser", password=PASSWORD)
    login_response = api_client.post("/auth/login/", {"username": "jwksuser", "password": PASSWORD})
    access = login_response.data["access"]

    jwks = api_client.get("/auth/jwks.json").data
    signing_key = jwt.PyJWK.from_dict(jwks["keys"][0])

    payload = jwt.decode(access, key=signing_key.key, algorithms=["RS256"])

    assert payload["username"] == "jwksuser"


def test_access_token_header_kid_matches_jwks(api_client: APIClient) -> None:
    """Заголовок токена должен содержать kid, совпадающий с JWKS.

    Без него PyJWKClient и аналоги в других языках не смогут выбрать нужный
    ключ из JWKS при ротации (несколько ключей в ответе).
    """
    User.objects.create_user(username="kiduser", password=PASSWORD)
    login_response = api_client.post("/auth/login/", {"username": "kiduser", "password": PASSWORD})
    access = login_response.data["access"]

    header = jwt.get_unverified_header(access)
    jwks = api_client.get("/auth/jwks.json").data

    assert header.get("kid") == jwks["keys"][0]["kid"]
