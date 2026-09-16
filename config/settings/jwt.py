from datetime import timedelta

from config.settings.env import JWT_ISSUER, JWT_SIGNING_KEY, JWT_VERIFYING_KEY

SIMPLE_JWT = {
    "ALGORITHM": "RS256",
    "SIGNING_KEY": JWT_SIGNING_KEY,
    "VERIFYING_KEY": JWT_VERIFYING_KEY,
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "UPDATE_LAST_LOGIN": True,
    "ISSUER": JWT_ISSUER,
    "LEEWAY": timedelta(seconds=10),
    "CHECK_REVOKE_TOKEN": True,
}
