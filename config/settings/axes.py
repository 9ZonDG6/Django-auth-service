from datetime import timedelta

from config.settings.env import AXES_COOLOFF_MINUTES, AXES_ENABLED, AXES_FAILURE_TRIES

if AXES_ENABLED:
    globals()["INSTALLED_APPS"].append("axes")
    globals()["MIDDLEWARE"].append("axes.middleware.AxesMiddleware")
    globals()["AUTHENTICATION_BACKENDS"].insert(0, "axes.backends.AxesStandaloneBackend")

    AXES_FAILURE_LIMIT = AXES_FAILURE_TRIES
    AXES_COOLOFF_TIME = timedelta(minutes=AXES_COOLOFF_MINUTES)

    AXES_LOCK_OUT_AT_FAILURE = True
    AXES_RESET_ON_SUCCESS = True
    AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = False

    AXES_USE_ATTEMPT_EXPIRATION = True
    AXES_HTTP_RESPONSE_CODE = 429

    AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
