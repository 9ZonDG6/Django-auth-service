from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Кладёт в JWT дополнительные claims: Username, роли (группы) и staff/superuser."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Отключить обрезание пробелов у пароля."""
        super().__init__(*args, **kwargs)
        password_field = self.fields["password"]
        if isinstance(password_field, serializers.CharField):
            password_field.trim_whitespace = False

    @classmethod
    def get_token(cls, user: User) -> RefreshToken:
        """Сформировать refresh-токен с кастомными claims для пользователя."""
        token = super().get_token(user)
        if not isinstance(token, RefreshToken):
            msg = "Ожидался RefreshToken"
            raise TypeError(msg)

        token["username"] = user.username
        token["roles"] = list(user.groups.values_list("name", flat=True))
        token["is_staff"] = user.is_staff
        token["is_superuser"] = user.is_superuser

        return token


class RefreshSerializer(serializers.Serializer):
    """Обновление access/refresh с перечитыванием ролей/staff/superuser из БД."""

    refresh = serializers.CharField()
    access = serializers.CharField(read_only=True)

    def validate(self, attrs: dict[str, str]) -> dict[str, str]:  # ruff: ignore[no-self-use]
        """Проверить refresh, отозвать его и выдать новую пару со свежими claims."""
        try:
            old_refresh = RefreshToken(attrs["refresh"])  # ty: ignore[invalid-argument-type]
        except TokenError as exc:
            raise InvalidToken(exc.args[0] if exc.args else str(exc)) from exc

        user_id = old_refresh.payload.get(api_settings.USER_ID_CLAIM)
        user = User.objects.filter(**{api_settings.USER_ID_FIELD: user_id}).first()
        if user is None or not api_settings.USER_AUTHENTICATION_RULE(user):
            raise AuthenticationFailed("Пользователь не найден или деактивирован.", "no_active_account")

        old_refresh.blacklist()

        new_refresh = CustomTokenObtainPairSerializer.get_token(user)

        return {
            "access": str(new_refresh.access_token),
            "refresh": str(new_refresh),
        }


class LogoutSerializer(serializers.Serializer):
    """Для logout нужен refresh-токен для отзыва."""

    refresh = serializers.CharField()
