from typing import TYPE_CHECKING

from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from apps.users.models import User


def outstanding_tokens_for_user(user: User) -> QuerySet[OutstandingToken]:
    """Получить выданные пользователю refresh-токены."""
    return OutstandingToken.objects.filter(user=user)
