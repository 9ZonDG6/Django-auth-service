from typing import TYPE_CHECKING

from apps.users.models import User

if TYPE_CHECKING:
    from uuid import UUID


def get_user_by_uuid(user_id: UUID | str) -> User | None:
    """Найти пользователя по UUID, включая неактивного."""
    return User.objects.filter(pk=user_id).first()


def user_exists(*, username: str) -> bool:
    """Проверить, занят ли username."""
    return User.objects.filter(username=username).exists()


def user_group_names(user: User) -> list[str]:
    """Получить имена групп пользователя для claims JWT."""
    return list(user.groups.values_list("name", flat=True))
