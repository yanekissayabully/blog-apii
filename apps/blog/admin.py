from typing import ClassVar

from django.contrib import admin
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.sections import TableSection

from apps.blog.models import Category, Comment, Post, Tag


class CategoryPostsSection(TableSection):
    """Table with the posts of a category, shown when a row of the list is expanded."""

    verbose_name = "Posts"
    related_name = "posts"
    fields: ClassVar[list[str]] = ["title", "status", "created_at"]
    height = 300


class PostsCountMixin:
    """Adds a sortable 'Posts' column. The count is calculated by the database in one query."""

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        queryset = super().get_queryset(request)  # type: ignore[misc]
        return queryset.annotate(posts_count=Count("posts"))

    @display(description="Posts", ordering="posts_count")
    def posts_count(self, obj: Category | Tag) -> int:
        return obj.posts_count


@admin.register(Category)
class CategoryAdmin(PostsCountMixin, ModelAdmin):
    list_display: ClassVar[list[str]] = ["name", "slug", "posts_count"]
    search_fields: ClassVar[list[str]] = ["name"]
    prepopulated_fields: ClassVar[dict[str, tuple[str, ...]]] = {"slug": ("name",)}
    list_sections: ClassVar[list[type[TableSection]]] = [CategoryPostsSection]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        # prefetch_related: the expanded rows read category.posts without a query per row
        return super().get_queryset(request).prefetch_related("posts")


@admin.register(Tag)
class TagAdmin(PostsCountMixin, ModelAdmin):
    list_display: ClassVar[list[str]] = ["name", "slug", "posts_count"]
    search_fields: ClassVar[list[str]] = ["name"]
    prepopulated_fields: ClassVar[dict[str, tuple[str, ...]]] = {"slug": ("name",)}


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_filter: ClassVar[list[str]] = ["status"]


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    pass