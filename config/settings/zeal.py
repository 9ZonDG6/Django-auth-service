from config.settings.env import LOGGING_ENABLED, ZEAL_ENABLED

if ZEAL_ENABLED:
    globals()["INSTALLED_APPS"].append("zeal")

    middleware: list[str] = globals()["MIDDLEWARE"]
    anchor = (
        "silk.middleware.SilkyMiddleware"
        if "silk.middleware.SilkyMiddleware" in middleware
        else "django.middleware.security.SecurityMiddleware"
    )
    middleware.insert(middleware.index(anchor) + 1, "zeal.middleware.zeal_middleware")

    ZEAL_RAISE = False

    ZEAL_ALLOWLIST = [
        {"model": "silk.Request", "field": "response"},
        {"model": "sessions.Session", "field": "get()"},
    ]

    if LOGGING_ENABLED:
        globals()["LOGGING"]["loggers"]["py.warnings"]["handlers"].append("zeal_file")
