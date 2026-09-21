from typing import TYPE_CHECKING

from django.conf import settings
from django.utils import timezone

if TYPE_CHECKING:
    from rest_framework.request import Request

    from apps.users.models import User


def complete_login(*, request: Request, user: User) -> None:
    """Записать успешный JWT-вход и сбросить ошибки только его пары username + IP."""
    if not settings.AXES_ENABLED:
        return
    from axes.conf import settings as axes_settings  # ruff: ignore[import-outside-top-level]
    from axes.utils import reset  # ruff: ignore[import-outside-top-level]

    record_jwt_login(request=request, user=user)
    ip_address = getattr(request, "axes_ip_address", None)
    if axes_settings.AXES_RESET_ON_SUCCESS and ip_address:
        reset(ip=ip_address, username=user.get_username())


def record_jwt_login(*, request: Request, user: User) -> None:
    """Записать успешную выдачу JWT без создания сессии и сигнала Django login."""
    if not settings.AXES_ENABLED:
        return

    from axes.conf import settings as axes_settings  # ruff: ignore[import-outside-top-level]
    from axes.models import AccessLog  # ruff: ignore[import-outside-top-level]

    if axes_settings.AXES_DISABLE_ACCESS_LOG:
        return

    AccessLog.objects.create(
        username=user.get_username(),
        ip_address=getattr(request, "axes_ip_address", None),
        user_agent=getattr(request, "axes_user_agent", "<unknown>"),
        http_accept=getattr(request, "axes_http_accept", "<unknown>"),
        path_info=getattr(request, "axes_path_info", request.path),
        attempt_time=getattr(request, "axes_attempt_time", timezone.now()),
    )
