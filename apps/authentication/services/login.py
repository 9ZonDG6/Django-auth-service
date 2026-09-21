from typing import TYPE_CHECKING

import structlog
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework_simplejwt.settings import api_settings

from apps.authentication.services.login_audit import complete_login
from apps.authentication.services.token_lifecycle import issue_refresh_token
from apps.users.models import User

if TYPE_CHECKING:
    from rest_framework.request import Request


def login(*, request: Request, username: str, password: str) -> dict[str, str]:
    """Проверить учётные данные, выдать JWT и завершить аудит входа."""
    user = authenticate(request=request, username=username, password=password)
    if getattr(request, "axes_locked_out", False):
        raise Throttled(detail="Слишком много неудачных попыток входа.")
    if not api_settings.USER_AUTHENTICATION_RULE(user) or not isinstance(user, User):
        raise AuthenticationFailed(_("No active account found with the given credentials"), "no_active_account")
    refresh = issue_refresh_token(user)
    tokens = {"refresh": str(refresh), "access": str(refresh.access_token)}
    if api_settings.UPDATE_LAST_LOGIN:
        update_last_login(User, user)
    complete_login(request=request, user=user)
    structlog.contextvars.bind_contextvars(user_id=str(user.pk))
    structlog.get_logger(__name__).info("login_succeeded", channel="jwt", user_id=str(user.pk))
    return tokens
