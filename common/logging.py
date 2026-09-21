"""Контекст HTTP-запроса и безопасное форматирование журналов."""

import re
import sys
import traceback
from time import perf_counter
from typing import TYPE_CHECKING, Any, override
from uuid import uuid4

import structlog
from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from django_structlog import signals
from django_structlog.middlewares import RequestMiddleware

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse
    from structlog.typing import EventDict, WrappedLogger

_EXCEPTION_INFO_LENGTH = 3
_REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_SECRET_FIELDS = frozenset(
    {
        "password",
        "old_password",
        "new_password",
        "password_verify",
        "token",
        "access",
        "refresh",
        "authorization",
        "cookie",
        "cookies",
        "headers",
        "body",
        "credentials",
    }
)


def redact_fields(value: object) -> object:
    """Скрыть чувствительные поля структурированных событий."""
    if isinstance(value, dict):
        return {
            key: "[redacted]" if str(key).lower() in _SECRET_FIELDS else redact_fields(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_fields(item) for item in value]
    return value


def prepare_event(_logger: WrappedLogger, _method: str, event: EventDict) -> EventDict:
    """Добавить сервис и убрать заголовки, query string и тексты исключений."""
    event["service"] = settings.SERVICE_NAME
    event.pop("user_agent", None)
    event.pop("correlation_id", None)
    event.pop("request", None)
    if "code" in event:
        event["status_code"] = event.pop("code")
    exc_info = event.pop("exc_info", None)
    if exc_info:
        if exc_info is True:
            exc_info = sys.exc_info()
        if isinstance(exc_info, BaseException):
            exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
        if isinstance(exc_info, tuple) and len(exc_info) == _EXCEPTION_INFO_LENGTH and exc_info[0] is not None:
            event["exception_type"] = exc_info[0].__name__
            event["traceback"] = [
                {"file": frame.filename, "line": frame.lineno, "function": frame.name}
                for frame in traceback.extract_tb(exc_info[2])
            ]
    return {
        key: "[redacted]" if key.lower() in _SECRET_FIELDS else redact_fields(value) for key, value in event.items()
    }


class RequestLoggingMiddleware(RequestMiddleware):
    """Расширить django-structlog проверкой request_id и длительностью запроса."""

    @override
    def prepare(self, request: HttpRequest) -> None:
        """Начать изолированный контекст без доверия произвольным заголовкам."""
        structlog.contextvars.clear_contextvars()
        candidate = request.META.get("HTTP_X_REQUEST_ID", "")
        request_id = candidate if isinstance(candidate, str) and _REQUEST_ID.fullmatch(candidate) else str(uuid4())
        request.META["HTTP_X_REQUEST_ID"] = request_id
        request.__dict__.pop("headers", None)
        request.__dict__["log_request_id"] = request_id
        request.__dict__["log_started_at"] = perf_counter()
        structlog.contextvars.bind_contextvars(method=request.method, path=request.path)
        super().prepare(request)

    @staticmethod
    @override
    def format_request(request: HttpRequest) -> str:
        """Не включать параметры URL в HTTP-события."""
        return f"{request.method} {request.path}"

    @override
    def handle_response(self, request: HttpRequest, response: HttpResponse) -> None:
        """Вернуть идентификатор клиенту и завершить контекст средствами пакета."""
        response["X-Request-ID"] = request.__dict__["log_request_id"]
        structlog.contextvars.bind_contextvars(
            duration_ms=round((perf_counter() - request.__dict__["log_started_at"]) * 1000, 2),
        )
        try:
            super().handle_response(request, response)
        finally:
            structlog.contextvars.clear_contextvars()


@receiver(user_logged_in, dispatch_uid="logging.login_succeeded")
def log_session_login(user: object, **_kwargs: Any) -> None:  # ruff: ignore[any-type]
    """Записать успешный сессионный вход без содержимого запроса."""
    structlog.get_logger(__name__).info("login_succeeded", channel="session", user_id=str(getattr(user, "pk", "")))


@receiver(user_login_failed, dispatch_uid="logging.login_failed")
def log_failed_login(**_kwargs: Any) -> None:  # ruff: ignore[any-type]
    """Отказ Django authenticate фиксируется отдельно от HTTP-статуса формы."""
    structlog.get_logger(__name__).warning("login_failed")


@receiver(signals.bind_extra_request_failed_metadata, dispatch_uid="logging.failure_duration")
def bind_failure_duration(request: HttpRequest, **_kwargs: Any) -> None:  # ruff: ignore[any-type]
    """Сохранить длительность и для необработанного исключения во view."""
    started_at = request.__dict__.get("log_started_at")
    if isinstance(started_at, (int, float)):
        structlog.contextvars.bind_contextvars(duration_ms=round((perf_counter() - started_at) * 1000, 2))
