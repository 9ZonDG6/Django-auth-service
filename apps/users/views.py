from typing import TYPE_CHECKING

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.users import services
from apps.users.serializers import ChangePasswordSerializer, RegisterSerializer, UserSerializer

if TYPE_CHECKING:
    from rest_framework.request import Request

    from apps.users.types import AuthenticatedRequest


@extend_schema(tags=["Users"])
class RegisterView(GenericAPIView):
    """Регистрация пользователя."""

    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:
        """Регистрация пользователя."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = services.register_user(**serializer.validated_data)

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Users"])
class MeView(GenericAPIView):
    """Получение информации о текущем пользователе."""

    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request: AuthenticatedRequest) -> Response:
        """Получение информации о текущем пользователе."""
        return Response(self.serializer_class(request.user).data)


@extend_schema(tags=["Users"])
class ChangePasswordView(GenericAPIView):
    """Изменение пароля."""

    serializer_class = ChangePasswordSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request: AuthenticatedRequest) -> Response:
        """Смена пароля."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        services.change_password(request.user, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)
