from __future__ import annotations

import json
from typing import TYPE_CHECKING

from settings.conf import ENV_ID

if TYPE_CHECKING:
    from django.http import HttpRequest

LOCAL_ENV_ID = "local"
PRODUCTION_ENV_ID = "prod"

STATUS_FILTER_PARAM = "status__exact"
STATUS_PUBLISHED = "published"
STATUS_DRAFT = "draft"

TOP_AUTHORS_LIMIT = 5
CHART_BAR_RADIUS = 4
PERCENT = 100


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

def dashboard_callback(request: HttpRequest, context: dict) -> dict:
    """Adds the data for the admin home page (templates/admin/index.html) to the context."""
    # Imported inside the function: models are not ready yet when settings are loaded.
    from django.contrib.auth import get_user_model
    from django.db.models import Count, Q
    from django.urls import reverse

    from apps.blog.models import Category, Comment, Post

    user_model = get_user_model()
    post_changelist = reverse("admin:blog_post_changelist")

    # One query for both post counters.
    counters = Post.objects.aggregate(
        published=Count("pk", filter=Q(status=Post.Status.PUBLISHED)),
        drafts=Count("pk", filter=Q(status=Post.Status.DRAFT)),
    )
    published, drafts = counters["published"], counters["drafts"]
    total_posts = published + drafts

    cards = [
        {
            "title": "Users",
            "value": user_model.objects.count(),
            "icon": "group",
            "href": reverse("admin:auths_user_changelist"),
        },
        {
            "title": "Published posts",
            "value": published,
            "icon": "check_circle",
            "href": f"{post_changelist}?{STATUS_FILTER_PARAM}={STATUS_PUBLISHED}",
        },
        {
            "title": "Drafts",
            "value": drafts,
            "icon": "edit_note",
            "href": f"{post_changelist}?{STATUS_FILTER_PARAM}={STATUS_DRAFT}",
        },
        {
            "title": "Comments",
            "value": Comment.objects.count(),
            "icon": "chat",
            "href": reverse("admin:blog_comment_changelist"),
        },
    ]

    categories = list(Category.objects.annotate(posts_count=Count("posts")).order_by("-posts_count", "name"))
    chart_data = {
        "labels": [category.name for category in categories],
        "datasets": [
            {
                "label": "Posts",
                "data": [category.posts_count for category in categories],
                "backgroundColor": "var(--color-primary-600)",
                "borderRadius": CHART_BAR_RADIUS,
            }
        ],
    }

    top_authors = user_model.objects.annotate(posts_count=Count("posts")).order_by("-posts_count", "email")[
        :TOP_AUTHORS_LIMIT
    ]
    authors_table = {
        "headers": ["Author", "Email", "Posts"],
        "rows": [
            [f"{author.first_name} {author.last_name}".strip() or "-", author.email, author.posts_count]
            for author in top_authors
        ],
    }

    published_percent = round(published / total_posts * PERCENT) if total_posts else 0
    draft_percent = PERCENT - published_percent if total_posts else 0

    context.update(
        {
            "cards": cards,
            "chart_data": json.dumps(chart_data),
            "authors_table": authors_table,
            "published_percent": published_percent,
            "draft_percent": draft_percent,
        }
    )
    return context