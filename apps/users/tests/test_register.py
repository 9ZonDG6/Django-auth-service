from typing import TYPE_CHECKING

import pytest
from django.test import override_settings
from rest_framework import status

from apps.users.models import User
from config.settings.django import PASSWORD_HASHERS

if TYPE_CHECKING:
    from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/v1/users/register/"
PASSWORD = "Str0ng-Pass-92!"


def test_register_creates_user(api_client: APIClient) -> None:
    """Успешная регистрация создаёт User."""
    response = api_client.post(REGISTER_URL, {"username": "newbie", "password": PASSWORD, "password_verify": PASSWORD})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["username"] == "newbie"
    assert "password" not in response.data
    assert User.objects.filter(username="newbie").exists()


def test_register_rejects_password_mismatch(api_client: APIClient) -> None:
    """Несовпадающее подтверждение пароля — 400, пользователь не создаётся."""
    response = api_client.post(
        REGISTER_URL,
        {"username": "mismatch", "password": PASSWORD, "password_verify": "Different-Pass-92!"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "password_verify" in {error["attr"] for error in response.data["errors"]}
    assert not User.objects.filter(username="mismatch").exists()


def test_register_requires_password_verify(api_client: APIClient) -> None:
    """Подтверждение пароля обязательно."""
    response = api_client.post(REGISTER_URL, {"username": "noverify", "password": PASSWORD})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "password_verify" in {error["attr"] for error in response.data["errors"]}
    assert not User.objects.filter(username="noverify").exists()


def test_register_rejects_duplicate_username(api_client: APIClient) -> None:
    """Повторная регистрация с тем же username — 400, не падение на UNIQUE constraint."""
    User.objects.create_user(username="dup", password=PASSWORD)

    response = api_client.post(REGISTER_URL, {"username": "dup", "password": PASSWORD, "password_verify": PASSWORD})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_register_rejects_weak_password(api_client: APIClient) -> None:
    """AUTH_PASSWORD_VALIDATORS реально применяются при регистрации."""
    response = api_client.post(
        REGISTER_URL, {"username": "weakpw", "password": "12345678", "password_verify": "12345678"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not User.objects.filter(username="weakpw").exists()


def test_register_rejects_password_similar_to_username(api_client: APIClient) -> None:
    """UserAttributeSimilarityValidator должен работать и при регистрации, не только при смене пароля."""
    response = api_client.post(
        REGISTER_URL,
        {"username": "johnsmith", "password": "johnsmith123", "password_verify": "johnsmith123"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not User.objects.filter(username="johnsmith").exists()


def test_register_rejects_phone_longer_than_model_max_length(api_client: APIClient) -> None:
    """Модель ограничивает phone 11 символами — сериализатор должен отклонять раньше, чем БД."""
    response = api_client.post(
        REGISTER_URL,
        {"username": "phoneuser", "password": PASSWORD, "password_verify": PASSWORD, "phone": "1" * 50},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not User.objects.filter(username="phoneuser").exists()


@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
def test_register_hashes_password_with_argon2(api_client: APIClient) -> None:
    """Argon2 должен быть основным хешером (быстрее и надёжнее дефолтного PBKDF2).

    Глобальный autouse-фикстур `_fast_password_hasher` подменяет хешер на MD5 ради
    скорости тестов — здесь это нужно отменить, иначе проверяем не то, что в проде.
    """
    api_client.post(REGISTER_URL, {"username": "argonuser", "password": PASSWORD, "password_verify": PASSWORD})

    user = User.objects.get(username="argonuser")

    assert user.password.startswith("argon2$")


def test_register_accepts_blank_optional_fields(api_client: APIClient) -> None:
    """Модель разрешает blank=True для email и т.п. — сериализатор должен тоже."""
    response = api_client.post(
        REGISTER_URL,
        {"username": "blankfields", "password": PASSWORD, "password_verify": PASSWORD, "email": ""},
    )

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.parametrize(
    "password", [" Reg-Sp4ce!", "Reg-Sp4ce! ", "Reg Sp4ce!", "Reg\tSp4ce!", "Reg\nSp4ce!", "Reg\u00a0Sp4ce!"]
)
def test_register_trims_password_edges(api_client: APIClient, password: str) -> None:
    """Обрезаются края пароля, пробельные символы внутри сохраняются."""
    response = api_client.post(
        REGISTER_URL, {"username": "whitespace_account", "password": password, "password_verify": password}
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.get(username="whitespace_account").check_password(password.strip())
    login = api_client.post("/api/v1/auth/login/", {"username": "whitespace_account", "password": password})
    assert login.status_code == status.HTTP_200_OK


@pytest.mark.parametrize("phone", ["string", "123", "+79991234567", "7999abc4567", "７９９９１２３４５６７"])
def test_register_rejects_invalid_phone(api_client: APIClient, phone: str) -> None:
    """Телефон проверяется до создания пользователя."""
    response = api_client.post(
        REGISTER_URL,
        {"username": "invalidphone", "password": PASSWORD, "password_verify": PASSWORD, "phone": phone},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "phone" in {error["attr"] for error in response.data["errors"]}
    assert not User.objects.filter(username="invalidphone").exists()


@pytest.mark.parametrize("phone", ["79991234567", ""])
def test_register_accepts_phone(api_client: APIClient, phone: str) -> None:
    """Разрешены 11 цифр или пустое необязательное поле."""
    response = api_client.post(
        REGISTER_URL,
        {"username": "validphone", "password": PASSWORD, "password_verify": PASSWORD, "phone": phone},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["phone"] == phone
