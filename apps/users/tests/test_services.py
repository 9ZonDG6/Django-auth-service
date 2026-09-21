import pytest
from rest_framework.exceptions import ValidationError

from apps.users.models import User
from apps.users.services import register_user

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("password", "confirmation", "error_field"),
    [
        ("Str0ng-Pass-92!", "Different-Pass-92!", "password_verify"),
        ("12345678", "12345678", "password"),
        ("short", "short", "password"),
    ],
)
def test_registration_service_enforces_password_policy(password: str, confirmation: str, error_field: str) -> None:
    """Прямой вызов сервиса не обходит подтверждение и политику пароля."""
    with pytest.raises(ValidationError) as error:
        register_user(username="serviceuser", password=password, password_verify=confirmation)

    assert error_field in error.value.detail
    assert not User.objects.filter(username="serviceuser").exists()
