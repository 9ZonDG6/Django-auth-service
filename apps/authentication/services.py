import hashlib
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from django.conf import settings
from jwt.algorithms import RSAAlgorithm
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

if TYPE_CHECKING:
    from apps.users.models import User


def blacklist_refresh_token(raw_token: str, *, owner: User) -> None:
    """Отозвать refresh-токен, предварительно убедившись, что он принадлежит owner."""
    token = RefreshToken(raw_token)  # ty: ignore[invalid-argument-type]
    token_user_id = token.payload.get(api_settings.USER_ID_CLAIM)
    owner_id = str(getattr(owner, api_settings.USER_ID_FIELD))
    if token_user_id != owner_id:
        msg = "Токен принадлежит другому пользователю."
        raise TokenError(msg)

    token.blacklist()


def revoke_all_tokens(user: User) -> None:
    """Отозвать все выданные refresh-токены пользователя ("выйти везде")."""
    outstanding = OutstandingToken.objects.filter(user=user)
    BlacklistedToken.objects.bulk_create(
        (BlacklistedToken(token=token) for token in outstanding),
        ignore_conflicts=True,
    )


def get_jwks() -> dict[str, list[dict]]:
    """Собрать JWKS-ответ с публичным ключом для проверки подписи токенов."""
    public_key = serialization.load_pem_public_key(settings.SIMPLE_JWT["VERIFYING_KEY"].encode())
    if not isinstance(public_key, RSAPublicKey):
        msg = "JWT_VERIFYING_KEY должен быть RSA-ключом"
        raise TypeError(msg)

    jwk = RSAAlgorithm.to_jwk(public_key, as_dict=True)
    jwk["kid"] = key_id(settings.SIMPLE_JWT["VERIFYING_KEY"])
    jwk["alg"] = "RS256"
    jwk["use"] = "sig"

    return {"keys": [jwk]}


def key_id(public_key_pem: str) -> str:
    """Стабильный идентификатор ключа для поля `kid` — хэш содержимого ключа."""
    return hashlib.sha256(public_key_pem.encode()).hexdigest()[:16]
