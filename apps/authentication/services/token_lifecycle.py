from typing import TYPE_CHECKING

from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.utils import get_md5_hash_password

from apps.authentication.selectors import outstanding_tokens_for_user
from apps.authentication.services.jwt_tokens import KeyIdRefreshToken
from apps.users.selectors import get_user_by_uuid, user_group_names

if TYPE_CHECKING:
    from apps.users.models import User


def blacklist_refresh_token(raw_token: str, *, owner: User) -> None:
    """Отозвать refresh-токен, предварительно убедившись, что он принадлежит owner."""
    error_message = "Недействительный refresh-токен."
    try:
        token = KeyIdRefreshToken(raw_token)  # ty: ignore[invalid-argument-type]
    except TokenError as exc:
        raise ValidationError(error_message, code="invalid_token") from exc
    token_user_id = token.payload.get(api_settings.USER_ID_CLAIM)
    owner_id = str(getattr(owner, api_settings.USER_ID_FIELD))
    if token_user_id != owner_id:
        raise ValidationError(error_message, code="invalid_token")

    token.blacklist()


def revoke_all_tokens(user: User) -> None:
    """Отозвать все выданные refresh-токены пользователя ("выйти везде")."""
    outstanding = outstanding_tokens_for_user(user)
    BlacklistedToken.objects.bulk_create(
        (BlacklistedToken(token=token) for token in outstanding),
        ignore_conflicts=True,
    )


def issue_refresh_token(user: User) -> KeyIdRefreshToken:
    """Выдать refresh с актуальными ролями и признаками пользователя."""
    token = KeyIdRefreshToken.for_user(user)
    if not isinstance(token, KeyIdRefreshToken):
        raise TypeError("Ожидался KeyIdRefreshToken")

    token["username"] = user.username
    token["roles"] = user_group_names(user)
    token["is_staff"] = user.is_staff
    token["is_superuser"] = user.is_superuser

    return token


def refresh_tokens(raw_token: str) -> dict[str, str]:
    """Проверить refresh и пароль, отозвать старый токен и выдать свежую пару."""
    try:
        old_refresh = KeyIdRefreshToken(raw_token)  # ty: ignore[invalid-argument-type]
    except TokenError as exc:
        raise InvalidToken(str(exc)) from exc

    user_id = old_refresh.payload.get(api_settings.USER_ID_CLAIM)
    user = get_user_by_uuid(user_id) if user_id is not None else None
    if user is None or not api_settings.USER_AUTHENTICATION_RULE(user):
        raise AuthenticationFailed("Пользователь не найден или деактивирован.", "no_active_account")

    if api_settings.CHECK_REVOKE_TOKEN and old_refresh.payload.get(
        api_settings.REVOKE_TOKEN_CLAIM
    ) != get_md5_hash_password(user.password):
        raise AuthenticationFailed("Пароль изменён. Войдите заново.", "password_changed")

    old_refresh.blacklist()
    new_refresh = issue_refresh_token(user)

    return {"access": str(new_refresh.access_token), "refresh": str(new_refresh)}
