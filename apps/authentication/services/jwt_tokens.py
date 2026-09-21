from functools import cached_property
from typing import Any

import jwt
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.authentication.services.jwks import key_id


class KeyIdTokenBackend(TokenBackend):
    """`TokenBackend`, добавляющий `kid` в заголовок подписанного JWT."""

    def encode(self, payload: dict[str, Any]) -> str:
        """Подписать payload, добавив `kid` в заголовок токена."""
        jwt_payload = payload.copy()

        if self.audience is not None:
            jwt_payload["aud"] = self.audience

        if self.issuer is not None:
            jwt_payload["iss"] = self.issuer

        token = jwt.encode(
            jwt_payload,
            self.prepared_signing_key,
            algorithm=self.algorithm,
            headers={"kid": key_id(self.verifying_key)},
            json_encoder=self.json_encoder,
        )

        if isinstance(token, bytes):
            return token.decode("utf-8")
        return token


class KeyIdBackendMixin:
    """Backend принадлежит экземпляру токена, глобальное состояние SimpleJWT не меняется."""

    @cached_property
    def token_backend(self) -> KeyIdTokenBackend:
        """Создать backend из настроек SimpleJWT при первом использовании токена."""
        return KeyIdTokenBackend(
            algorithm=api_settings.ALGORITHM,
            signing_key=api_settings.SIGNING_KEY,
            verifying_key=api_settings.VERIFYING_KEY,
            audience=api_settings.AUDIENCE,
            issuer=api_settings.ISSUER,
            jwk_url=api_settings.JWK_URL,
            leeway=api_settings.LEEWAY,
            json_encoder=api_settings.JSON_ENCODER,
        )


class KeyIdAccessToken(KeyIdBackendMixin, AccessToken):
    """Access-токен с идентификатором публичного ключа в заголовке."""


class KeyIdRefreshToken(KeyIdBackendMixin, RefreshToken):
    """Refresh и производный access подписываются backend с kid."""

    access_token_class = KeyIdAccessToken
