from rest_framework import serializers

from apps.users.models import User


class RegisterSerializer(serializers.ModelSerializer):
    """Сериализатор для создания User."""

    password = serializers.CharField(write_only=True)
    password_verify = serializers.CharField(write_only=True)
    phone = serializers.RegexField(
        regex=r"\A[0-9]{11}\Z",
        required=False,
        allow_blank=True,
        max_length=11,
        help_text="11 цифр без пробелов и знака +.",
        error_messages={"invalid": "Введите телефон из 11 цифр без пробелов и знака +."},
    )

    class Meta:
        model = User
        fields = (
            "username",
            "password",
            "password_verify",
            "email",
            "first_name",
            "last_name",
            "patronymic",
            "phone",
        )


class ChangePasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля User."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения User."""

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "patronymic",
            "phone",
            "is_staff",
            "is_superuser",
            "date_joined",
        )
