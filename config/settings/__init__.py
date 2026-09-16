from split_settings.tools import include

include(
    "env.py",
    "django.py",
    "security.py",
    "apps.py",
    "database.py",
    "logging.py",
    "jwt.py",
    "rest_framework.py",
    "silk.py",
    "axes.py",
    "extra_checks.py",
    "zeal.py",
    scope=globals(),
)
