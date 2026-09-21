import hashlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from jwt.algorithms import RSAAlgorithm
from rest_framework_simplejwt.settings import api_settings


def get_jwks() -> dict[str, list[dict]]:
    """Собрать JWKS-ответ с публичным ключом для проверки подписи токенов."""
    public_key = serialization.load_pem_public_key(api_settings.VERIFYING_KEY.encode())
    if not isinstance(public_key, RSAPublicKey):
        msg = "JWT_VERIFYING_KEY должен быть RSA-ключом"
        raise TypeError(msg)

    jwk = RSAAlgorithm.to_jwk(public_key, as_dict=True)
    jwk["kid"] = key_id(api_settings.VERIFYING_KEY)
    jwk["alg"] = "RS256"
    jwk["use"] = "sig"

    return {"keys": [jwk]}


def key_id(public_key_pem: str) -> str:
    """Стабильный идентификатор ключа для поля `kid` — хэш содержимого ключа."""
    return hashlib.sha256(public_key_pem.encode()).hexdigest()[:16]
