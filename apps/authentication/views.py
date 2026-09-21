from typing import TYPE_CHECKING

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenViewBase

from apps.authentication.serializers import (
    JWKSSerializer,
    LoginSerializer,
    LogoutSerializer,
    RefreshSerializer,
)
from apps.authentication.services.jwks import get_jwks
from apps.authentication.services.login import login
from apps.authentication.services.token_lifecycle import blacklist_refresh_token, refresh_tokens

if TYPE_CHECKING:
    from rest_framework.request import Request

    from apps.users.types import AuthenticatedRequest


@extend_schema(tags=["Auth"])
class LoginView(TokenViewBase):
    """Логин по username/password — отдаёт пару access/refresh токенов."""

    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:
        """Проверить входные поля и передать вход сервису."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = login(request=request, **serializer.validated_data)
        return Response(tokens)


@extend_schema(tags=["Auth"])
class RefreshView(TokenViewBase):
    """Обновление access/refresh с перечитыванием ролей/staff/superuser из БД."""

    serializer_class = RefreshSerializer

    def post(self, request: Request) -> Response:
        """Передать refresh сервису обновления токенов."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = refresh_tokens(serializer.validated_data["refresh"])
        return Response(tokens)


@extend_schema(tags=["Auth"])
class LogoutView(GenericAPIView):
    """Отзывает refresh-токен пользователя."""

    serializer_class = LogoutSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request: AuthenticatedRequest) -> Response:
        """Добавить refresh-токен из тела запроса в blacklist."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        blacklist_refresh_token(serializer.validated_data["refresh"], owner=request.user)

        return Response(status=status.HTTP_205_RESET_CONTENT)


@extend_schema(tags=["Auth"])
class JWKSView(GenericAPIView):
    """Отдаёт публичный ключ (JWKS) для проверки подписи токенов другими сервисами."""

    serializer_class = JWKSSerializer
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request: Request) -> Response:  # ruff: ignore[unused-method-argument]
        """Вернуть JWKS с текущим публичным ключом."""
        serializer = self.get_serializer(instance=get_jwks())
        return Response(serializer.data)
