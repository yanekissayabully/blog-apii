from typing import ClassVar

from django.contrib import admin, messages
from django.db import models
from django.db.models import Count, Prefetch, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import urlencode
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    MultipleRelatedDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import action, display
from unfold.sections import TableSection

from apps.blog.models import Category, Comment, Post, Tag

COMMENT_BODY_PREVIEW_LENGTH = 60
COMMENTS_PER_PAGE = 10


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


class PostCommentsSection(TableSection):
    """Table with the comments of a post, shown when a row of the list is expanded."""

    verbose_name = "Comments"
    related_name = "comments"
    fields: ClassVar[list[str]] = ["author", "body", "created_at"]
    height = 300


class CommentInline(TabularInline):
    """Comments of a post on its edit page: in their own tab, 10 per page."""

    model = Comment
    tab = True
    per_page = COMMENTS_PER_PAGE
    extra = 0
    ordering: ClassVar[tuple[str, ...]] = ("-created_at",)
    fields: ClassVar[tuple[str, ...]] = ("author", "body", "created_at")
    readonly_fields: ClassVar[tuple[str, ...]] = ("created_at",)
    autocomplete_fields: ClassVar[list[str]] = ["author"]


@admin.register(Post)
class PostAdmin(ModelAdmin):
    # --- list page ---
    list_display: ClassVar[list[str]] = [
        "post_header",
        "status_label",
        "category",
        "tags_dropdown",
        "comments_count",
        "created_at",
    ]
    list_filter: ClassVar[list[tuple]] = [
        ("status", ChoicesDropdownFilter),
        ("category", RelatedDropdownFilter),
        ("tags", MultipleRelatedDropdownFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    ]
    list_filter_submit = True
    search_fields: ClassVar[list[str]] = ["title", "body", "author__email"]
    list_sections: ClassVar[list[type[TableSection]]] = [PostCommentsSection]

    # --- actions ---
    actions: ClassVar[list[str]] = ["publish_selected", "move_to_drafts"]
    actions_row: ClassVar[list[str]] = ["toggle_status"]
    actions_list: ClassVar[list[str]] = ["publish_all_drafts"]
    actions_detail: ClassVar[list[str]] = ["open_comments"]
    actions_submit_line: ClassVar[list[str]] = ["save_and_publish"]

    # --- edit page ---
    fieldsets: ClassVar[tuple] = (
        ("Content", {"classes": ["tab"], "fields": ("title", "slug", "body")}),
        ("Classification", {"classes": ["tab"], "fields": ("category", "tags", "status")}),
        ("Meta", {"classes": ["tab"], "fields": ("author", "created_at", "updated_at")}),
    )
    prepopulated_fields: ClassVar[dict[str, tuple[str, ...]]] = {"slug": ("title",)}
    autocomplete_fields: ClassVar[list[str]] = ["author", "category", "tags"]
    readonly_fields: ClassVar[tuple[str, ...]] = ("created_at", "updated_at")
    formfield_overrides: ClassVar[dict] = {models.TextField: {"widget": WysiwygWidget}}
    warn_unsaved_form = True
    inlines: ClassVar[list[type]] = [CommentInline]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        comments = Comment.objects.select_related("author")
        return (
            super()
            .get_queryset(request)
            .select_related("author", "category")
            .prefetch_related("tags", Prefetch("comments", queryset=comments))
            .annotate(comments_count=Count("comments"))
        )

    # --- columns ---
    @display(header=True, description="Post", ordering="title")
    def post_header(self, obj: Post) -> list:
        return [obj.title, obj.author.email]

    @display(
        description="Status",
        ordering="status",
        label={Post.Status.PUBLISHED: "success", Post.Status.DRAFT: "warning"},
    )
    def status_label(self, obj: Post) -> tuple[str, str]:
        return obj.status, obj.get_status_display()  # (key for the color, text to show)

    @display(description="Tags", dropdown=True)
    def tags_dropdown(self, obj: Post) -> dict:
        tags = obj.tags.all()  # uses prefetch_related: no extra query (.count() would make one)
        return {"title": f"{len(tags)} tags", "items": [{"title": tag.name} for tag in tags]}

    @display(description="Comments", ordering="comments_count")
    def comments_count(self, obj: Post) -> int:
        return obj.comments_count

    # --- bulk actions (checkboxes) ---
    @action(description="Publish selected", permissions=["change"])
    def publish_selected(self, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.update(status=Post.Status.PUBLISHED)
        self.message_user(request, f"Published posts: {updated}", messages.SUCCESS)

    @action(description="Move to drafts", permissions=["change"])
    def move_to_drafts(self, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.update(status=Post.Status.DRAFT)
        self.message_user(request, f"Moved to drafts: {updated}", messages.SUCCESS)

    # --- row action ---
    @action(description="Publish / unpublish", permissions=["change"])
    def toggle_status(self, request: HttpRequest, object_id: int) -> HttpResponse:
        post = get_object_or_404(Post, pk=object_id)
        post.status = Post.Status.DRAFT if post.status == Post.Status.PUBLISHED else Post.Status.PUBLISHED
        post.save(update_fields=["status", "updated_at"])
        self.message_user(request, f"'{post.title}' is now {post.get_status_display().lower()}", messages.SUCCESS)
        return redirect(reverse("admin:blog_post_changelist"))

    # --- button above the list ---
    @action(description="Publish all drafts", permissions=["change"])
    def publish_all_drafts(self, request: HttpRequest) -> HttpResponse:
        updated = Post.objects.filter(status=Post.Status.DRAFT).update(status=Post.Status.PUBLISHED)
        self.message_user(request, f"Published drafts: {updated}", messages.SUCCESS)
        return redirect(reverse("admin:blog_post_changelist"))

    # --- button on the post page ---
    @action(description="Open comments", url_path="open-comments")
    def open_comments(self, request: HttpRequest, object_id: int) -> HttpResponse:
        url = reverse("admin:blog_comment_changelist")
        return redirect(f"{url}?{urlencode({'post__id__exact': object_id})}")

    # --- button next to "Save" (runs after the post is saved) ---
    @action(description="Save & publish")
    def save_and_publish(self, request: HttpRequest, obj: Post) -> None:
        obj.status = Post.Status.PUBLISHED
        obj.save(update_fields=["status", "updated_at"])
        self.message_user(request, f"'{obj.title}' published", messages.SUCCESS)


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display: ClassVar[list[str]] = ["post_title", "author_email", "body_preview", "created_at"]
    list_select_related: ClassVar[list[str]] = ["post", "author"]  # one JOIN instead of a query per row
    list_filter: ClassVar[list[tuple]] = [
        ("post", AutocompleteSelectFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    ]
    list_filter_submit = True
    search_fields: ClassVar[list[str]] = ["body", "author__email", "post__title"]
    autocomplete_fields: ClassVar[list[str]] = ["post", "author"]

    @display(description="Post", ordering="post__title")
    def post_title(self, obj: Comment) -> str:
        return obj.post.title

    @display(description="Author", ordering="author__email")
    def author_email(self, obj: Comment) -> str:
        return obj.author.email

    @display(description="Comment")
    def body_preview(self, obj: Comment) -> str:
        if len(obj.body) <= COMMENT_BODY_PREVIEW_LENGTH:
            return obj.body
        return obj.body[:COMMENT_BODY_PREVIEW_LENGTH].rstrip() + "..."