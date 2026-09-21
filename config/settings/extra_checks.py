from config.settings.env import EXTRA_CHECKS_ENABLED

if EXTRA_CHECKS_ENABLED:
    globals()["INSTALLED_APPS"].append("extra_checks")

EXTRA_CHECKS = {
    "checks": [
        {
            "id": "model-attribute",
            "attrs": [
                "created_at",
                "updated_at",
            ],
        },
        {
            "id": "model-meta-attribute",
            "attrs": [
                "verbose_name",
                "verbose_name_plural",
                "ordering",
            ],
        },
        "no-unique-together",
        "model-admin",
        "field-file-upload-to",
        "field-verbose-name",
        "field-text-null",
        "field-null",
        "field-foreign-key-db-index",
        "field-related-name",
        "field-default-null",
        "field-choices-constraint",
        "drf-model-serializer-extra-kwargs",
        {
            "id": "drf-model-serializer-meta-attribute",
            "attrs": [
                "model",
                "fields",
            ],
        },
    ],
}
