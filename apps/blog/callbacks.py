from __future__ import annotations

from typing import TYPE_CHECKING

from settings.conf import ENV_ID

if TYPE_CHECKING:
    from django.http import HttpRequest

LOCAL_ENV_ID = "local"
PRODUCTION_ENV_ID = "prod"

STATUS_FILTER_PARAM = "status__exact"
STATUS_PUBLISHED = "published"
STATUS_DRAFT = "draft"


def environment_callback(request: HttpRequest) -> list[str] | None:
    """Badge in the header: orange for local, red for production."""
    if ENV_ID == LOCAL_ENV_ID:
        return ["Local", "warning"]
    if ENV_ID == PRODUCTION_ENV_ID:
        return ["Production", "danger"]
    return None


def drafts_badge(request: HttpRequest) -> int:
    # Imported inside the function: models are not ready yet when settings are loaded.
    from apps.blog.models import Post

    return Post.objects.filter(status=Post.Status.DRAFT).count()


def _posts_link(status: str | None = None) -> str:
    from django.urls import reverse

    url = reverse("admin:blog_post_changelist")
    return f"{url}?{STATUS_FILTER_PARAM}={status}" if status else url


def posts_all_link(request: HttpRequest) -> str:
    return _posts_link()


def posts_published_link(request: HttpRequest) -> str:
    return _posts_link(STATUS_PUBLISHED)


def posts_drafts_link(request: HttpRequest) -> str:
    return _posts_link(STATUS_DRAFT)


def posts_all_active(request: HttpRequest) -> bool:
    """'All' tab is active only when no status filter is applied."""
    return STATUS_FILTER_PARAM not in request.GET


def sidebar_navigation(request: HttpRequest) -> list[dict]:
    """Sidebar menu. The 'Users & Access' group is built only for superusers."""
    from django.urls import reverse_lazy

    navigation: list[dict] = [
        {
            "title": "Overview",
            "separator": True,
            "items": [
                {"title": "Dashboard", "icon": "dashboard", "link": reverse_lazy("admin:index")},
            ],
        },
        {
            "title": "Content",
            "separator": True,
            "items": [
                {
                    "title": "Posts",
                    "icon": "article",
                    "link": reverse_lazy("admin:blog_post_changelist"),
                    "badge": "apps.blog.callbacks.drafts_badge",
                },
                {"title": "Comments", "icon": "chat", "link": reverse_lazy("admin:blog_comment_changelist")},
                {"title": "Categories", "icon": "category", "link": reverse_lazy("admin:blog_category_changelist")},
                {"title": "Tags", "icon": "sell", "link": reverse_lazy("admin:blog_tag_changelist")},
            ],
        },
    ]
    if request.user.is_superuser:
        navigation.append(
            {
                "title": "Users & Access",
                "separator": True,
                "items": [
                    {"title": "Users", "icon": "person", "link": reverse_lazy("admin:auths_user_changelist")},
                    {"title": "Groups", "icon": "group", "link": reverse_lazy("admin:auth_group_changelist")},
                ],
            }
        )
    return navigation