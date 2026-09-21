from config.settings.env import ENVIRONMENT

# Cookies одного хоста общие для всех портов: сервисам нужны разные имена.
CSRF_COOKIE_NAME = "auth_csrftoken"
SESSION_COOKIE_NAME = "auth_sessionid"

PERMISSIONS_POLICY: dict[str, list[str]] = {
    "accelerometer": [],
    "autoplay": [],
    "camera": [],
    "display-capture": [],
    "encrypted-media": [],
    "fullscreen": [],
    "geolocation": [],
    "gyroscope": [],
    "magnetometer": [],
    "microphone": [],
    "midi": [],
    "payment": [],
    "usb": [],
}

if ENVIRONMENT != "local":
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365  # 1 год
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Внутренние HTTP-пробы контейнера не требуют перенаправления на HTTPS.
SECURE_REDIRECT_EXEMPT = [r"^health/(live|ready)/$"]
