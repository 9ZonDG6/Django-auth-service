LOCAL_APPS = [
    "apps.users.apps.UsersConfig",
    "apps.authentication.apps.AuthenticationConfig",
]

THIRD_PARTY_APPS = [
    "django_structlog",
    "health_check",
    "corsheaders",
    "django_safe_migrations",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "rest_framework_simplejwt.token_blacklist",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    *THIRD_PARTY_APPS,
    *LOCAL_APPS,
]
