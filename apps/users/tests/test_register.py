from typing import TYPE_CHECKING

import pytest
from django.test import override_settings
from rest_framework import status

from apps.users.models import User
from config.settings.django import PASSWORD_HASHERS

if TYPE_CHECKING:
    from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

REGISTER_URL = "/users/register/"


def test_register_creates_user(api_client: APIClient) -> None:
    """Успешная регистрация создаёт User."""
    response = api_client.post(REGISTER_URL, {"username": "newbie", "password": "Str0ng-Pass-92!"})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["username"] == "newbie"
    assert "password" not in response.data
    assert User.objects.filter(username="newbie").exists()


def test_register_rejects_duplicate_username(api_client: APIClient) -> None:
    """Повторная регистрация с тем же username — 400, не падение на UNIQUE constraint."""
    User.objects.create_user(username="dup", password="Str0ng-Pass-92!")

    response = api_client.post(REGISTER_URL, {"username": "dup", "password": "Str0ng-Pass-92!"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_register_rejects_weak_password(api_client: APIClient) -> None:
    """AUTH_PASSWORD_VALIDATORS реально применяются при регистрации."""
    response = api_client.post(REGISTER_URL, {"username": "weakpw", "password": "12345678"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not User.objects.filter(username="weakpw").exists()


def test_register_rejects_password_similar_to_username(api_client: APIClient) -> None:
    """UserAttributeSimilarityValidator должен работать и при регистрации, не только при смене пароля."""
    response = api_client.post(REGISTER_URL, {"username": "johnsmith", "password": "johnsmith123"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not User.objects.filter(username="johnsmith").exists()


def test_register_rejects_phone_longer_than_model_max_length(api_client: APIClient) -> None:
    """Модель ограничивает phone 11 символами — сериализатор должен отклонять раньше, чем БД."""
    response = api_client.post(
        REGISTER_URL,
        {"username": "phoneuser", "password": "Str0ng-Pass-92!", "phone": "1" * 50},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not User.objects.filter(username="phoneuser").exists()


@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
def test_register_hashes_password_with_argon2(api_client: APIClient) -> None:
    """Argon2 должен быть основным хешером (быстрее и надёжнее дефолтного PBKDF2).

    Глобальный autouse-фикстур `_fast_password_hasher` подменяет хешер на MD5 ради
    скорости тестов — здесь это нужно отменить, иначе проверяем не то, что в проде.
    """
    api_client.post(REGISTER_URL, {"username": "argonuser", "password": "Str0ng-Pass-92!"})

    user = User.objects.get(username="argonuser")

    assert user.password.startswith("argon2$")


def test_register_accepts_blank_optional_fields(api_client: APIClient) -> None:
    """Модель разрешает blank=True для email и т.п. — сериализатор должен тоже."""
    response = api_client.post(REGISTER_URL, {"username": "blankfields", "password": "Str0ng-Pass-92!", "email": ""})

    assert response.status_code == status.HTTP_201_CREATED


def test_register_does_not_trim_password_whitespace(api_client: APIClient) -> None:
    """Пароль с пробелами по краям должен сохраниться как есть, не обрезаться."""
    response = api_client.post(REGISTER_URL, {"username": "regspace", "password": "  Reg-Sp4ce!  "})

    assert response.status_code == status.HTTP_201_CREATED
    user = User.objects.get(username="regspace")
    assert user.check_password("  Reg-Sp4ce!  ")
    assert not user.check_password("Reg-Sp4ce!")
