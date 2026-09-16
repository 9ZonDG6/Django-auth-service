from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import URLPattern, URLResolver, include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from config.settings.django import MEDIA_ROOT, MEDIA_URL
from config.settings.env import DEBUG, SILK_ENABLED

urlpatterns: list[URLPattern | URLResolver] = [
    path("", RedirectView.as_view(url="/backend/swagger/")),
    path("backend/", RedirectView.as_view(url="/backend/swagger/")),
    path("backend/admin/", admin.site.urls),
    path("backend/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("backend/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("backend/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("auth/", include("apps.authentication.urls")),
    path("users/", include("apps.users.urls")),
]

if SILK_ENABLED:
    urlpatterns.append(path("silk/", include("silk.urls", namespace="silk")))

if DEBUG:
    urlpatterns.extend(staticfiles_urlpatterns())
    urlpatterns.extend(static(MEDIA_URL, document_root=MEDIA_ROOT))
