from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """Учётные данные для входа и выдаваемая пара токенов."""

    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class RefreshSerializer(serializers.Serializer):
    """Входные и выходные поля обновления токенов."""

    refresh = serializers.CharField()
    access = serializers.CharField(read_only=True)


class LogoutSerializer(serializers.Serializer):
    """Для logout нужен refresh-токен для отзыва."""

    refresh = serializers.CharField()


class JWKSerializer(serializers.Serializer):
    """Публичный RSA-ключ для проверки JWT."""

    kty = serializers.CharField()
    kid = serializers.CharField()
    use = serializers.CharField()
    alg = serializers.CharField()
    n = serializers.CharField()
    e = serializers.CharField()


class JWKSSerializer(serializers.Serializer):
    """Набор публичных ключей auth-сервиса."""

    keys = JWKSerializer(many=True)
