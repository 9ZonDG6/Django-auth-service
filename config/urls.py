from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import URLPattern, URLResolver, include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.authentication.views import JWKSView
from config.settings.django import MEDIA_ROOT, MEDIA_URL
from config.settings.env import DEBUG, SILK_ENABLED

urlpatterns: list[URLPattern | URLResolver] = [
    path(".well-known/jwks.json", JWKSView.as_view(), name="jwks"),
    path("", RedirectView.as_view(url="/api/docs/")),
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/v1/auth/", include("apps.authentication.urls")),
    path("api/v1/users/", include("apps.users.urls")),
]

if SILK_ENABLED:
    urlpatterns.append(path("silk/", include("silk.urls", namespace="silk")))

if DEBUG:
    urlpatterns.extend(staticfiles_urlpatterns())
    urlpatterns.extend(static(MEDIA_URL, document_root=MEDIA_ROOT))
