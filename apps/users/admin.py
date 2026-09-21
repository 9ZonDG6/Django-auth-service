from typing import TYPE_CHECKING

from django.contrib import admin
from django.contrib.admin.utils import quote
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from apps.users.models import User, UserGroup

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest, HttpResponse


admin.site.unregister(Group)


@admin.register(UserGroup)
class UserGroupAdmin(DjangoGroupAdmin):
    """Админка групп."""


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Админка пользователей."""

    fieldsets = (
        (
            "Учетные данные",
            {
                "fields": (
                    "username",
                    "password",
                ),
            },
        ),
        (
            "Профиль",
            {
                "fields": (
                    ("last_name", "first_name", "patronymic"),
                    ("email", "phone"),
                ),
            },
        ),
        (
            "Доступ и роли",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                ),
            },
        ),
        (
            "Доп. информация",
            {
                "classes": ("collapse",),
                "fields": (
                    ("date_joined", "last_login"),
                    ("created_at", "updated_at"),
                ),
            },
        ),
    )
    readonly_fields = (
        "id",
        "date_joined",
        "last_login",
        "created_at",
        "updated_at",
    )
    list_display = (
        "account",
        "fio",
        "is_active",
        "is_staff",
    )
    list_display_links = None
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "groups",
    )
    search_fields = (
        "^username",
        "email",
        "phone",
        "last_name",
        "first_name",
        "patronymic",
        "id",
    )
    ordering = ("username",)
    date_hierarchy = "date_joined"
    actions = (
        "activate_users",
        "deactivate_users",
    )

    def change_view(
        self,
        request: HttpRequest,
        object_id: str,
        form_url: str = "",
        extra_context: dict[str, object] | None = None,
    ) -> HttpResponse:
        """Показать username и UUID в подзаголовке штатной карточки."""
        response = super().change_view(request, object_id, form_url, extra_context)
        if isinstance(response, TemplateResponse) and response.context_data is not None:
            user = response.context_data.get("original")
            if isinstance(user, User):
                response.context_data["subtitle"] = f"{user.username} · {user.pk}"
        return response

    def get_fieldsets(  # ty: ignore[invalid-method-override]
        self,
        request: HttpRequest,
        obj: User | None = None,
    ) -> tuple[tuple[str | None, dict[str, object]], ...]:
        """Скрыть is_superuser/groups от staff без is_superuser."""
        fieldsets = super().get_fieldsets(request, obj)
        if isinstance(request.user, User) and request.user.is_superuser:
            return fieldsets  # ty: ignore[invalid-return-type]

        restricted_fields = {"is_superuser", "groups"}
        return tuple(
            (name, {**options, "fields": tuple(f for f in options["fields"] if f not in restricted_fields)})
            for name, options in fieldsets
        )  # ty: ignore[invalid-return-type]

    @staticmethod
    def _exclude_superusers_for_non_superuser(request: HttpRequest, queryset: QuerySet[User]) -> QuerySet[User]:
        """Не дать staff без is_superuser задеть суперпользователей bulk-экшеном."""
        if isinstance(request.user, User) and request.user.is_superuser:
            return queryset
        return queryset.exclude(is_superuser=True)

    @staticmethod
    @admin.display(description="Пользователь", ordering="username")
    def account(obj: User) -> str:
        """Вернуть ссылку на пользователя с ID и username."""
        url = reverse("admin:users_user_change", args=(quote(obj.pk),))
        return format_html(
            '<a href="{}" style="text-decoration: none;">{}<br>{}</a>',
            url,
            obj.id,
            obj.username,
        )

    @staticmethod
    @admin.display(description="ФИО", ordering="last_name")
    def fio(obj: User) -> str:
        """ФИО с переносом отчества на новую строку."""
        first_line = " ".join(filter(None, [obj.last_name, obj.first_name]))

        if first_line and obj.patronymic:
            return format_html("{}<br>{}", first_line, obj.patronymic)

        return first_line or obj.patronymic

    @admin.action(description="Активировать выбранных пользователей")
    def activate_users(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        """Активировать выбранных пользователей."""
        queryset = self._exclude_superusers_for_non_superuser(request, queryset)
        updated_count = queryset.update(is_active=True, updated_at=timezone.now())
        self.message_user(request, f"Активировано пользователей: {updated_count}")

    @admin.action(description="Заблокировать выбранных пользователей")
    def deactivate_users(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        """Заблокировать выбранных пользователей, кроме текущего."""
        queryset = self._exclude_superusers_for_non_superuser(request, queryset).exclude(pk=request.user.pk)
        updated_count = queryset.update(is_active=False, updated_at=timezone.now())
        self.message_user(request, f"Заблокировано пользователей: {updated_count}")
