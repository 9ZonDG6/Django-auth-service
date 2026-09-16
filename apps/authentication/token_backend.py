from typing import Any

import jwt
from rest_framework_simplejwt.backends import TokenBackend

from apps.authentication.services import key_id


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
