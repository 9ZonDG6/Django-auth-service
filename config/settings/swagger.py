import tomllib
from pathlib import Path

from config.settings.env import BASE_DIR

with Path.open(BASE_DIR / "pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)

PROJECT_VERSION = pyproject["project"]["version"]

SPECTACULAR_SETTINGS = {
    "TITLE": "Auth service",
    "VERSION": PROJECT_VERSION,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
}

SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"] = {
    "ValidationErrorEnum": "drf_standardized_errors.openapi_serializers.ValidationErrorEnum.choices",
    "ClientErrorEnum": "drf_standardized_errors.openapi_serializers.ClientErrorEnum.choices",
    "ServerErrorEnum": "drf_standardized_errors.openapi_serializers.ServerErrorEnum.choices",
    "ErrorCode401Enum": "drf_standardized_errors.openapi_serializers.ErrorCode401Enum.choices",
    "ErrorCode403Enum": "drf_standardized_errors.openapi_serializers.ErrorCode403Enum.choices",
    "ErrorCode404Enum": "drf_standardized_errors.openapi_serializers.ErrorCode404Enum.choices",
    "ErrorCode405Enum": "drf_standardized_errors.openapi_serializers.ErrorCode405Enum.choices",
    "ErrorCode406Enum": "drf_standardized_errors.openapi_serializers.ErrorCode406Enum.choices",
    "ErrorCode415Enum": "drf_standardized_errors.openapi_serializers.ErrorCode415Enum.choices",
    "ErrorCode429Enum": "drf_standardized_errors.openapi_serializers.ErrorCode429Enum.choices",
    "ErrorCode500Enum": "drf_standardized_errors.openapi_serializers.ErrorCode500Enum.choices",
}
SPECTACULAR_SETTINGS["POSTPROCESSING_HOOKS"] = ["drf_standardized_errors.openapi_hooks.postprocess_schema_enums"]
