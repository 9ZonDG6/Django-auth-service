from typing import TYPE_CHECKING

from rest_framework.request import Request

if TYPE_CHECKING:
    from apps.users.models import User


class AuthenticatedRequest(Request):
    """Тип запроса auth-сервиса после успешной проверки IsAuthenticated."""

    user: User
