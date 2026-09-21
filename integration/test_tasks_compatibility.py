"""Два независимых процесса Django, свои базы данных и реальные HTTP-запросы."""

import base64
import json
import os
import socket
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import time
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from rest_framework import status

if TYPE_CHECKING:
    from collections.abc import Iterator

_HTTP_TIMEOUT_SECONDS = 5
_START_POLL_ATTEMPTS = 200
_START_POLL_INTERVAL_SECONDS = 0.1


def request(
    url: str,
    data: dict[str, Any] | None = None,
    token: str | None = None,
    method: str | None = None,
) -> tuple[int, Any]:
    """Выполнить реальный HTTP-запрос и вернуть (статус, тело-как-JSON-или-None)."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(  # ruff: ignore[suspicious-url-open-usage] — URL всегда собран самим тестом (http://127.0.0.1:<port>/...)
        url, data=json.dumps(data).encode() if data is not None else None, headers=headers, method=method
    )
    try:
        response = urlopen(req, timeout=_HTTP_TIMEOUT_SECONDS)  # ruff: ignore[suspicious-url-open-usage] — см. выше
    except HTTPError as exc:
        response = exc
    with response:
        code = response.status
        if not isinstance(code, int):
            msg = "Ответ не содержит статус-код"
            raise TypeError(msg)
        body = response.read()
        return code, json.loads(body) if body else None


def unused_port() -> int:
    """Найти свободный TCP-порт на localhost для временного dev-сервера."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def server(root: Path, port: int, database: Path, env: dict[str, str], log: Path) -> Iterator[str]:
    """Поднять `manage.py runserver` в отдельном процессе на своей sqlite-базе.

    Yields:
        Базовый URL запущенного сервера (`http://127.0.0.1:<port>`).
    """
    script = """
import sys
from django.conf import settings
settings.DATABASES["default"] = {"ENGINE": "django.db.backends.sqlite3", "NAME": sys.argv[1]}
import django
django.setup()
from django.core.management import call_command
call_command("migrate", verbosity=0)
call_command("runserver", sys.argv[2], use_reloader=False, verbosity=0)
"""
    with log.open("w+", encoding="utf-8") as output:
        process = subprocess.Popen(  # ruff: ignore[subprocess-without-shell-equals-true] — фиксированные аргументы, без shell, без внешнего ввода
            [str(root / ".venv/bin/python"), "-c", script, str(database), f"127.0.0.1:{port}"],
            cwd=root,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        try:
            for _ in range(_START_POLL_ATTEMPTS):
                if process.poll() is not None:
                    output.seek(0)
                    pytest.fail(output.read())
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                        break
                except OSError:
                    time.sleep(_START_POLL_INTERVAL_SECONDS)
            else:
                pytest.fail("Service did not start within 20 seconds")
            yield f"http://127.0.0.1:{port}"
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def _build_env(auth_port: int) -> dict[str, str]:
    """Собрать окружение для обоих процессов: общий RSA-ключ, issuer и audience."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings",
        "ENVIRONMENT": "local",
        "DEBUG": "true",
        "SECRET_KEY": "isolated-e2e-test-only",
        "ALLOWED_HOSTS": "127.0.0.1,localhost",
        "SILK_ENABLED": "false",
        "ZEAL_ENABLED": "false",
        "LOGGING_ENABLED": "false",
        "QUERY_COUNTER_ENABLED": "false",
        "EXTRA_CHECKS_ENABLED": "false",
        "LOG_FORMAT": "json",
        "LOG_LEVEL": "INFO",
        "AUTH_SERVICE_BASE_URL": f"http://127.0.0.1:{auth_port}",
        "JWT_SIGNING_KEY": base64.b64encode(private).decode(),
        "JWT_VERIFYING_KEY": base64.b64encode(public).decode(),
        "JWT_ISSUER": "e2e-auth",
        "JWT_AUDIENCE": "tasks-service",
        "AUTH_JWT_ISSUER": "e2e-auth",
        "AUTH_JWT_AUDIENCE": "tasks-service",
        "AUTH_JWKS_URL": f"http://127.0.0.1:{auth_port}/.well-known/jwks.json",
    }


def _register_and_login(auth_url: str, username: str) -> dict[str, Any]:
    """Зарегистрировать пользователя на реальном auth-сервисе и войти, вернув пару токенов."""
    password = "E2E-Strong-Password-92!"
    credentials = {"username": username, "password": password}
    registration = {**credentials, "password_verify": password}
    assert request(auth_url + "/api/v1/users/register/", registration)[0] == status.HTTP_201_CREATED
    code, pair = request(auth_url + "/api/v1/auth/login/", credentials)
    assert code == status.HTTP_200_OK
    return pair


def test_auth_and_tasks_over_http(tmp_path: Path) -> None:
    """Полный цикл через реальный HTTP: регистрация, логин, чужие задачи, refresh, logout."""
    checkout = os.environ.get("TASKS_SERVICE_DIR")
    if not checkout:
        pytest.skip("Set TASKS_SERVICE_DIR to run two-service HTTP E2E")
    auth_root = Path(__file__).resolve().parents[1]
    tasks_root = Path(checkout).resolve()
    auth_port, tasks_port = unused_port(), unused_port()
    env = _build_env(auth_port)

    with (
        server(auth_root, auth_port, tmp_path / "auth.sqlite3", env, tmp_path / "auth.log") as auth,
        server(tasks_root, tasks_port, tmp_path / "tasks.sqlite3", env, tmp_path / "tasks.log") as tasks,
    ):
        alice = _register_and_login(auth, "alice")
        bob = _register_and_login(auth, "bob")

        assert request(auth + "/.well-known/jwks.json")[0] == status.HTTP_200_OK
        assert request(tasks + "/api/v1/tasks/")[0] == status.HTTP_401_UNAUTHORIZED

        code, task = request(tasks + "/api/v1/tasks/", {"title": "HTTP integration"}, alice["access"])
        assert code == status.HTTP_201_CREATED
        detail = tasks + f"/api/v1/tasks/{task['id']}/"
        assert request(detail, token=alice["access"])[0] == status.HTTP_200_OK
        assert request(detail, token=bob["access"])[0] == status.HTTP_404_NOT_FOUND
        assert request(detail, {"title": "stolen"}, bob["access"], "PATCH")[0] == status.HTTP_404_NOT_FOUND
        assert request(detail, token=bob["access"], method="DELETE")[0] == status.HTTP_404_NOT_FOUND
        assert request(tasks + "/api/v1/tasks/", token=alice["refresh"])[0] == status.HTTP_401_UNAUTHORIZED

        code, refreshed = request(auth + "/api/v1/auth/refresh/", {"refresh": alice["refresh"]})
        assert code == status.HTTP_200_OK
        assert request(detail, token=refreshed["access"])[0] == status.HTTP_200_OK
        assert request(auth + "/api/v1/auth/refresh/", {"refresh": alice["refresh"]})[0] == status.HTTP_401_UNAUTHORIZED

        logout = request(auth + "/api/v1/auth/logout/", {"refresh": refreshed["refresh"]}, refreshed["access"])
        assert logout[0] == status.HTTP_205_RESET_CONTENT
        assert request(auth + "/api/v1/auth/refresh/", {"refresh": refreshed["refresh"]})[0] == (
            status.HTTP_401_UNAUTHORIZED
        )
        assert request(detail, token=refreshed["access"], method="DELETE")[0] == status.HTTP_204_NO_CONTENT
