import asyncio
import json
import logging
from http import HTTPStatus
from io import StringIO
from unittest.mock import patch
from uuid import UUID

import pytest
import structlog
from django.conf import settings
from django.test import AsyncClient, Client

from common.logging import prepare_event


@pytest.mark.django_db(transaction=True)
def test_request_metadata_and_cleanup(client: Client, caplog: pytest.LogCaptureFixture) -> None:
    """HTTP-событие содержит метаданные без заголовков и query string."""
    structlog.contextvars.bind_contextvars(stale="must-not-leak")
    with caplog.at_level(logging.INFO):
        response = client.get(
            "/health/live/?token=query-secret",
            HTTP_X_REQUEST_ID="trace-123",
            HTTP_AUTHORIZATION="Bearer header-secret",
            HTTP_COOKIE="sessionid=cookie-secret",
            HTTP_USER_AGENT="agent-secret",
        )
    assert response["X-Request-ID"] == "trace-123"
    events = [record.msg for record in caplog.records if isinstance(record.msg, dict)]
    finished = next(event for event in events if event["event"] == "request_finished")
    assert finished["service"] == settings.SERVICE_NAME
    assert finished["request_id"] == "trace-123"
    assert finished["path"] == "/health/live/"
    assert finished["status_code"] == HTTPStatus.OK
    assert finished["duration_ms"] >= 0
    assert not structlog.contextvars.get_contextvars()
    for secret in ("query-secret", "header-secret", "cookie-secret", "agent-secret", "must-not-leak"):
        assert secret not in str(events)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("request_id", ["", "x" * 65, "bad id", "bad\nheader"])
def test_invalid_request_id_is_replaced(client: Client, request_id: str) -> None:
    """Внешняя метка ограничена форматом и длиной."""
    response = client.get("/health/live/", HTTP_X_REQUEST_ID=request_id)
    assert UUID(response["X-Request-ID"])
    assert response["X-Request-ID"] != request_id


@pytest.mark.django_db(transaction=True)
def test_parallel_async_requests_keep_separate_ids() -> None:
    """Асинхронные запросы не делят request_id друг с другом."""

    async def run_requests() -> None:
        first, second = await asyncio.gather(
            AsyncClient().get("/health/live/", headers={"X-Request-ID": "first"}),
            AsyncClient().get("/health/live/", headers={"X-Request-ID": "second"}),
        )
        assert first["X-Request-ID"] == "first"
        assert second["X-Request-ID"] == "second"
        assert not structlog.contextvars.get_contextvars()

    asyncio.run(run_requests())


@pytest.mark.django_db(transaction=True)
def test_failure_response_has_request_id_without_exception_secret(
    client: Client, caplog: pytest.LogCaptureFixture
) -> None:
    """Даже необработанная ошибка сохраняет request_id, но не текст исключения."""
    client.raise_request_exception = False
    with patch("health_check.views.HealthCheckView.get", side_effect=RuntimeError("exception-secret")):
        response = client.get("/health/live/", HTTP_X_REQUEST_ID="failed-request")
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response["X-Request-ID"] == "failed-request"
    events = [record.msg for record in caplog.records if isinstance(record.msg, dict)]
    failed = next(event for event in events if event["event"] == "request_failed")
    assert failed["duration_ms"] >= 0
    assert "exception-secret" not in str(events)
    assert not structlog.contextvars.get_contextvars()


def test_json_formatter_redacts_structured_fields() -> None:
    """JSON содержит только безопасные данные, включая вложенные структуры."""
    output = StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=[prepare_event],
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        )
    )
    logger = logging.getLogger("logging-test")
    logger.addHandler(handler)
    structured_logger = structlog.wrap_logger(
        logger,
        processors=[prepare_event, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.stdlib.BoundLogger,
    )
    try:
        structured_logger.warning(
            "safe_event",
            password="password-secret",
            nested=[{"Authorization": "header-secret", "refresh": "token-secret"}],
        )
        logger.warning("plain_event")
    finally:
        logger.removeHandler(handler)
        handler.close()
    events = [json.loads(line) for line in output.getvalue().splitlines()]
    assert events[0]["password"] == "[redacted]"
    assert events[-1]["service"] == settings.SERVICE_NAME
    assert "secret" not in output.getvalue()
