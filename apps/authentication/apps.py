from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    name = "apps.authentication"

    def ready(self) -> None:  # ruff: ignore[no-self-use]
        """Подменить token_backend simplejwt на добавляющий `kid` в заголовок JWT."""
        from rest_framework_simplejwt import state  # ruff: ignore[import-outside-top-level]
        from rest_framework_simplejwt.settings import api_settings  # ruff: ignore[import-outside-top-level]

        from apps.authentication.token_backend import KeyIdTokenBackend  # ruff: ignore[import-outside-top-level]

        state.token_backend = KeyIdTokenBackend(
            api_settings.ALGORITHM,
            api_settings.SIGNING_KEY,
            api_settings.VERIFYING_KEY,
            api_settings.AUDIENCE,
            api_settings.ISSUER,
            api_settings.JWK_URL,
            api_settings.LEEWAY,
            api_settings.JSON_ENCODER,
        )
