"""Проверить production-сборку статики, не изменяя рабочий STATIC_ROOT."""

import os
import secrets
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import django
from django.conf import settings
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage, staticfiles_storage
from django.core.management import call_command


def main() -> None:
    """Собрать статику во временный каталог и проверить ключевые ресурсы."""
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    os.environ["ENVIRONMENT"] = "production"
    os.environ["DEBUG"] = "false"
    os.environ["SECRET_KEY"] = secrets.token_urlsafe(50)
    with TemporaryDirectory(prefix="django-static-check-") as static_root:
        settings.STATIC_ROOT = Path(static_root)
        django.setup()
        if not isinstance(staticfiles_storage, ManifestStaticFilesStorage):
            raise TypeError("Production должен использовать ManifestStaticFilesStorage")
        call_command("collectstatic", interactive=False, verbosity=0)
        for resource in (
            "admin/css/base.css",
            "admin/js/core.js",
            "drf_spectacular_sidecar/swagger-ui-dist/swagger-ui.css",
            "drf_spectacular_sidecar/swagger-ui-dist/swagger-ui-bundle.js",
            "drf_spectacular_sidecar/redoc/bundles/redoc.standalone.js",
        ):
            hashed_name = staticfiles_storage.stored_name(resource)
            if hashed_name == resource or not staticfiles_storage.exists(hashed_name):
                message = f"Не найден ресурс с хешем: {resource}"
                raise RuntimeError(message)
            staticfiles_storage.url(resource)
        if not staticfiles_storage.exists("staticfiles.json"):
            raise RuntimeError("Не создан manifest staticfiles.json")
        sys.stdout.write("Production static files and manifest: OK\n")


if __name__ == "__main__":
    main()
