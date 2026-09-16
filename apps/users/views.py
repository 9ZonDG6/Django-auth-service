from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.users import services
from apps.users.models import User
from apps.users.serializers import ChangePasswordSerializer, RegisterSerializer, UserSerializer

if TYPE_CHECKING:
    from rest_framework.request import Request


class RegisterView(GenericAPIView):
    """Регистрация пользователя."""

    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:
        """Регистрация пользователя."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = services.register_user(**serializer.validated_data)
        except ValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(GenericAPIView):
    """Получение информации о текущем пользователе."""

    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        """Получение информации о текущем пользователе."""
        return Response(self.serializer_class(request.user).data)


class ChangePasswordView(GenericAPIView):
    """Изменение пароля."""

    serializer_class = ChangePasswordSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request: Request) -> Response:
        """Смена пароля."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not isinstance(request.user, User):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            services.change_password(
                request.user,
                old_password=serializer.validated_data["old_password"],
                new_password=serializer.validated_data["new_password"],
            )
        except ValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_200_OK)
