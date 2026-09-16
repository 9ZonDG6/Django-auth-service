from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.authentication.services import revoke_all_tokens
from apps.users.models import User

DEFAULT_GROUP_NAME = "user"


def register_user(*, username: str, password: str, **extra_fields: str) -> User:
    """Зарегистрировать нового пользователя."""
    if User.objects.filter(username=username).exists():
        raise ValidationError("Пользователь с таким username уже существует.")

    validate_password(password, user=User(username=username, **extra_fields))

    user = User.objects.create_user(username=username, password=password, **extra_fields)

    default_group, _ = Group.objects.get_or_create(name=DEFAULT_GROUP_NAME)
    user.groups.add(default_group)

    return user


def change_password(user: User, *, old_password: str, new_password: str) -> None:
    """Сменить пароль пользователя, предварительно проверив старый."""
    if not user.check_password(old_password):
        raise ValidationError("Неверный текущий пароль.")

    validate_password(new_password, user=user)

    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])

    revoke_all_tokens(user)
