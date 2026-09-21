from typing import TYPE_CHECKING

from config.settings.env import SILK_ENABLED

if TYPE_CHECKING:
    from django.http import HttpRequest

if SILK_ENABLED:
    globals()["INSTALLED_APPS"].append("silk")

    middleware: list[str] = globals()["MIDDLEWARE"]
    middleware.insert(
        middleware.index("django.middleware.security.SecurityMiddleware") + 1,
        "silk.middleware.SilkyMiddleware",
    )

    SILKY_IGNORED_PREFIXES = (
        "/admin",
        "/silk",
        "/static",
        "/media",
        "/api/v1/auth",
    )
    SILKY_IGNORED_PREFIXES_WITH_SLASH = tuple(f"{prefix}/" for prefix in SILKY_IGNORED_PREFIXES)

    def silky_intercept(request: HttpRequest) -> bool:
        """Фильтрация запросов для Silk."""
        path = request.path
        return not (path in SILKY_IGNORED_PREFIXES or path.startswith(SILKY_IGNORED_PREFIXES_WITH_SLASH))

    SILKY_INTERCEPT_FUNC = silky_intercept

    SILKY_AUTHENTICATION = True
    SILKY_AUTHORISATION = True
