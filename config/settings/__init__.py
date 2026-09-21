from split_settings.tools import include

include(
    "env.py",
    "django.py",
    "security.py",
    "csp.py",
    "apps.py",
    "database.py",
    "logging.py",
    "jwt.py",
    "rest_framework.py",
    "silk.py",
    "axes.py",
    "extra_checks.py",
    "query_counter.py",
    "zeal.py",
    "swagger.py",
    scope=globals(),
)
