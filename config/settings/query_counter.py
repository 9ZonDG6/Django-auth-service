from config.settings.env import QUERY_COUNTER_ENABLED

if QUERY_COUNTER_ENABLED:
    globals()["INSTALLED_APPS"].append("query_counter")
    globals()["MIDDLEWARE"].insert(0, "common.query_counter.QueryCounterMiddleware")
