from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.fields import get_error_detail

from apps.authentication.services.token_lifecycle import revoke_all_tokens
from apps.users.models import User
from apps.users.selectors import user_exists

DEFAULT_GROUP_NAME = "user"


def register_user(*, username: str, password: str, password_verify: str, **extra_fields: str) -> User:
    """Зарегистрировать нового пользователя."""
    if password != password_verify:
        raise ValidationError({"password_verify": "Пароли не совпадают."})

    if user_exists(username=username):
        raise ValidationError("Пользователь с таким username уже существует.")

    _validate_new_password(password, user=User(username=username, **extra_fields), field="password")

    user = User.objects.create_user(username=username, password=password, **extra_fields)

    default_group, _ = Group.objects.get_or_create(name=DEFAULT_GROUP_NAME)
    user.groups.add(default_group)

    return user


def change_password(user: User, *, old_password: str, new_password: str) -> None:
    """Сменить пароль пользователя, предварительно проверив старый."""
    if not user.check_password(old_password):
        raise ValidationError("Неверный текущий пароль.")

    _validate_new_password(new_password, user=user, field="new_password")

    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])

    revoke_all_tokens(user)


def _validate_new_password(password: str, *, user: User, field: str) -> None:
    """Применить политику Django и привязать ошибки к полю операции."""
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise ValidationError({field: get_error_detail(exc)}) from exc
