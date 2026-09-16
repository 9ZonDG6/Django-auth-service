from django.core.exceptions import ImproperlyConfigured

from config.settings.env import (
    BASE_DIR,
    DATABASE_ENGINE,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)

SUPPORTED_DATABASE_ENGINES = {
    "django.db.backends.sqlite3",
    "django.db.backends.postgresql",
}

if DATABASE_ENGINE not in SUPPORTED_DATABASE_ENGINES:
    msg = f"Неизвестный DATABASE_ENGINE: {DATABASE_ENGINE!r}. Поддерживаются: {sorted(SUPPORTED_DATABASE_ENGINES)}"
    raise ImproperlyConfigured(msg)

if DATABASE_ENGINE == "django.db.backends.postgresql":
    DATABASES = {
        "default": {
            "ENGINE": DATABASE_ENGINE,
            "NAME": POSTGRES_DB,
            "USER": POSTGRES_USER,
            "PASSWORD": POSTGRES_PASSWORD,
            "HOST": POSTGRES_HOST,
            "PORT": POSTGRES_PORT,
        },
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        },
    }
