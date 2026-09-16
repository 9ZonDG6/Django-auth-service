from django.urls import path

from apps.authentication.views import JWKSView, LoginView, LogoutView, RefreshView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("jwks.json", JWKSView.as_view(), name="jwks"),
]
