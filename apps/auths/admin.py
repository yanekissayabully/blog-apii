from typing import Any, ClassVar

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import BooleanRadioFilter
from unfold.decorators import action, display
from unfold.forms import AdminPasswordChangeForm

from apps.auths.forms import UserChangeForm, UserCreationForm

User = get_user_model()

admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    # Our model has no `username`, so everything that mentions it is overridden.
    ordering: ClassVar[tuple[str, ...]] = ("email",)
    list_display: ClassVar[list[str]] = ["user_header", "is_active_label", "is_staff_label", "posts_count"]
    list_filter: ClassVar[list[tuple]] = [
        ("is_active", BooleanRadioFilter),
        ("is_staff", BooleanRadioFilter),
    ]
    list_filter_submit = True
    search_fields: ClassVar[list[str]] = ["email", "first_name", "last_name"]
    readonly_fields: ClassVar[tuple[str, ...]] = ("last_login",)

    fieldsets: ClassVar[tuple] = (
        ("Personal info", {"classes": ["tab"], "fields": ("email", "password", "first_name", "last_name")}),
        (
            "Permissions",
            {
                "classes": ["tab"],
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            },
        ),
        ("Important dates", {"classes": ["tab"], "fields": ("last_login",)}),
    )
    add_fieldsets: ClassVar[tuple] = (
        (None, {"classes": ("wide",), "fields": ("email", "first_name", "last_name", "password1", "password2")}),
    )
    actions: ClassVar[list[str]] = ["activate_users", "deactivate_users"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).annotate(posts_count=Count("posts"))

    @display(header=True, description="User")
    def user_header(self, obj: Any) -> list:
        full_name = f"{obj.first_name} {obj.last_name}".strip() or obj.email
        initials = f"{obj.first_name[:1]}{obj.last_name[:1]}".upper() or obj.email[:1].upper()
        return [full_name, obj.email, initials]

    @display(description="Active", label={True: "success", False: "danger"})
    def is_active_label(self, obj: Any) -> bool:
        return obj.is_active

    @display(description="Staff", label={True: "info", False: "warning"})
    def is_staff_label(self, obj: Any) -> bool:
        return obj.is_staff

    @display(description="Posts", ordering="posts_count")
    def posts_count(self, obj: Any) -> int:
        return obj.posts_count

    @action(description="Activate selected users")
    def activate_users(self, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated users: {updated}", messages.SUCCESS)

    @action(description="Deactivate selected users")
    def deactivate_users(self, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated users: {updated}", messages.SUCCESS)