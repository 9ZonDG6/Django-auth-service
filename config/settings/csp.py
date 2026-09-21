from csp.constants import NONCE, NONE, SELF

from config.settings.env import CSP_REPORT_ONLY

_POLICY = {
    "DIRECTIVES": {
        "default-src": [NONE],
        "script-src": [SELF, NONCE],
        "style-src": [SELF, NONCE],
        "img-src": [SELF, "data:"],
        "font-src": [SELF],
        "connect-src": [SELF],
        "form-action": [SELF],
        "frame-ancestors": [NONE],
        "base-uri": [NONE],
        # ReDoc создаёт локальный Web Worker для поиска по документации.
        "worker-src": [SELF, "blob:"],
    },
}

CONTENT_SECURITY_POLICY = None if CSP_REPORT_ONLY else _POLICY
CONTENT_SECURITY_POLICY_REPORT_ONLY = _POLICY if CSP_REPORT_ONLY else None
