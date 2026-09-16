from typing import TYPE_CHECKING

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.authentication import services
from apps.authentication.serializers import CustomTokenObtainPairSerializer, LogoutSerializer, RefreshSerializer
from apps.users.models import User

if TYPE_CHECKING:
    from rest_framework.request import Request

axes_reset = None
if settings.AXES_ENABLED:
    from axes.utils import reset as axes_reset


class LoginView(TokenObtainPairView):
    """Логин по username/password — отдаёт пару access/refresh токенов."""

    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = (AllowAny,)

    def post(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Логин с явной обработкой блокировки django-axes."""
        try:
            response = super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            if getattr(request, "axes_locked_out", None):
                return Response(
                    {"detail": "Слишком много неудачных попыток входа."},
                    status=settings.AXES_HTTP_RESPONSE_CODE,
                )
            raise

        if (
            axes_reset is not None
            and settings.AXES_ENABLED
            and settings.AXES_RESET_ON_SUCCESS
            and isinstance(request.data, dict)
        ):
            username = request.data.get("username")
            ip_address = getattr(request, "axes_ip_address", None)
            if isinstance(username, str) and username.strip() and ip_address:
                axes_reset(ip=ip_address, username=username.strip())

        return response


class RefreshView(TokenRefreshView):
    """Обновление access/refresh с перечитыванием ролей/staff/superuser из БД."""

    serializer_class = RefreshSerializer


class LogoutView(GenericAPIView):
    """Отзывает refresh-токен пользователя."""

    serializer_class = LogoutSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request: Request) -> Response:
        """Добавить refresh-токен из тела запроса в blacklist."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not isinstance(request.user, User):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            services.blacklist_refresh_token(serializer.validated_data["refresh"], owner=request.user)
        except TokenError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_205_RESET_CONTENT)


class JWKSView(APIView):
    """Отдаёт публичный ключ (JWKS) для проверки подписи токенов другими сервисами."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    @staticmethod
    def get(_request: Request) -> Response:
        """Вернуть JWKS с текущим публичным ключом."""
        return Response(services.get_jwks())
