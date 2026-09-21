from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import URLPattern, URLResolver, include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerSplitView
from health_check.views import HealthCheckView

from apps.authentication.views import JWKSView
from config.settings.django import MEDIA_ROOT, MEDIA_URL
from config.settings.env import DEBUG, SILK_ENABLED

urlpatterns: list[URLPattern | URLResolver] = [
    path("health/live/", HealthCheckView.as_view(checks=[]), name="health-live"),
    path("health/ready/", HealthCheckView.as_view(checks=["health_check.Database"]), name="health-ready"),
    path(".well-known/jwks.json", JWKSView.as_view(), name="jwks"),
    path("", RedirectView.as_view(url="/api/docs/")),
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerSplitView.as_view(url_name="schema", template_name="docs/swagger.html"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema", template_name="docs/redoc.html"), name="redoc"),
    path("api/v1/auth/", include("apps.authentication.urls"), name="auth"),
    path("api/v1/users/", include("apps.users.urls"), name="users"),
]

if SILK_ENABLED:
    urlpatterns.append(path("silk/", include("silk.urls", namespace="silk")))

if DEBUG:
    urlpatterns.extend(staticfiles_urlpatterns())
    urlpatterns.extend(static(MEDIA_URL, document_root=MEDIA_ROOT))
