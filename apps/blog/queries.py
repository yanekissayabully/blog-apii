from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import (
    Avg,
    Case,
    Count,
    Exists,
    F,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat, TruncMonth
from django.utils import timezone
from django.utils.text import slugify

from apps.blog.models import Category, Comment, Post, Tag

User = get_user_model()

NEWEST_POSTS_LIMIT = 5
PAGE_SIZE = 10
EDITED_AFTER = timedelta(hours=1)
UNCATEGORIZED = "Uncategorized"
AVERAGE_DIGITS = 2
TOP_AUTHORS_LIMIT = 5
HOT_COMMENTS = 10
NORMAL_COMMENTS = 3
FEED_LIMIT = 50
NEWES_TAGGED_LIMIT = 20

def categories_by_name() -> QuerySet[Category]:
    return Category.objects.order_by("name")

def published_posts() -> QuerySet[Post]:
    return Post.objects.filter(status=Post.Status.PUBLISHED)

def newest_published_posts() -> QuerySet[Post]:
    return published_posts().order_by("-created_at")[:NEWEST_POSTS_LIMIT]

def post_by_slug(slug: str) -> Post | None:
    return Post.objects.filter(slug=slug).first()

def active_users_count() -> int:
    return User.objects.filter(is_active=True).count()

def has_drafts() -> bool:
    return Post.objects.filter(status=Post.Status.DRAFT).exists()

def published_posts_page(page: int) -> QuerySet[Post]:
    start = (page - 1) * PAGE_SIZE
    return published_posts().order_by("-created_at")[start: start + PAGE_SIZE]

def posts_with_word_in_title(word: str) -> QuerySet[Post]:
    return Post.objects.filter(title__icontains=word)

def users_with_email_domain(domain: str) -> QuerySet:
    return User.objects.filter(email__iendswith=f"@{domain}")

def posts_without_category() -> QuerySet[Post]:
    return Post.objects.filter(category__isnull=True)

def categories_by_slugs(slugs: list[str]) -> QuerySet[Category]:
    return Category.objects.filter(slug__in=slugs)

def posts_in_month(year: int, month: int) -> QuerySet[Post]:
    return Post.objects.filter(created_at__year=year, created_at__month=month)

def posts_last_days(days: int) -> QuerySet[Post]:
    return Post.objects.filter(created_at__gte=timezone.now() - timedelta(days=days))

def posts_between(start: date, end: date) -> QuerySet[Post]:
    return Post.objects.filter(created_at__date__range=(start, end))

def author_published_posts(email: str) -> QuerySet[Post]:
    return published_posts().filter(author__email__iexact=email)

def posts_with_tag(tag_slug: str) -> QuerySet[Post]:
    return Post.objects.filter(tags__slug=tag_slug)

def comments_in_category(category_slug: str) -> QuerySet[Comment]:
    return Comment.objects.filter(post__category__slug=category_slug)

def users_with_published_posts() -> QuerySet:
    return User.objects.filter(posts__status=Post.Status.PUBLISHED).distinct()

def posts_without_tags() -> QuerySet[Post]:
    return Post.objects.filter(tags__isnull=True)

def users_without_comments() -> QuerySet:
    return User.objects.filter(comments__isnull=True)

def posts_with_both_tags(first_slug: str, second_slug: str) -> QuerySet[Post]:
    return Post.objects.filter(tags__slug=first_slug).filter(tags__slug=second_slug)

def search_posts(text: str) -> QuerySet[Post]:
    return Post.objects.filter(Q(title__icontains=text) | Q(body__icontains=text))

def published_posts_missing_info() -> QuerySet[Post]:
    return published_posts().filter(Q(category__isnull=True) | Q(tags__isnull=True)).distinct()

def edited_posts() -> QuerySet[Post]:
    return Post.objects.filter(updated_at__gt=F("created_at") + EDITED_AFTER)

def comments_by_post_author() -> QuerySet[Comment]:
    return Comment.objects.filter(author=F("post__author"))

def comments_before_post() -> QuerySet[Comment]:
    return Comment.objects.filter(created_at__lt=F("post__created_at"))

def published_authors_emails() -> list[str]:
    emails = published_posts().values_list("author__email", flat=True).distinct().order_by("author__email")
    return list(emails)

def published_posts_overview() -> list[dict]:
    posts = (
        published_posts()
        .annotate(author_email=F("author__email"), category_name=Coalesce("category__name", Value(UNCATEGORIZED)))
        .order_by("-created_at")
        .values("title", "author_email", "category_name")
    )
    return list(posts)

def posts_stats() -> dict:
    return Post.objects.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(status=Post.Status.PUBLISHED)),
        drafts=Count("id", filter=Q(status=Post.Status.DRAFT)),
        first_post_at=Min("created_at"),
        last_post_at=Max("created_at"),
    )

def average_comments_per_post() -> float:
    average = published_posts().annotate(comments_number=Count("comments")).aggregate(average=Avg("comments_number"))
    return round(average["average"] or 0.0, AVERAGE_DIGITS)

def categories_with_post_count() -> QuerySet[Category]:
    return Category.objects.annotate(post_count=Count("posts")).order_by("-post_count", "name")

def categories_with_published_count() -> QuerySet[Category]:
    published = Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
    return Category.objects.annotate(published_count=published).order_by("-published_count", "name")

def top_authors() -> QuerySet:
    published = Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
    return User.objects.annotate(published_count=published).order_by("-published_count", "email")[:TOP_AUTHORS_LIMIT]

def popular_tags(min_posts: int) -> QuerySet[Tag]:
    return (
        Tag.objects.annotate(post_count=Count("posts"))
        .filter(post_count__gte=min_posts)
        .order_by("-post_count", "name")
    )

def  posts_per_status() -> list[dict]:
    return list(Post.objects.values("status").annotate(count=Count("id")).order_by("status"))

def users_activity() -> QuerySet:
    return User.objects.annotate(
        post_count=Count("posts", distinct=True),
        comment_count=Count("comments", distinct=True),
    ).order_by("email")

def search_users_by_full_name(text: str) -> QuerySet:
    return User.objects.annotate(full_name=Concat("first_name", Value(" "), "last_name")).filter(
        full_name__icontains=text
    )

def published_posts_per_month() -> list[dict]:
    months = published_posts().annotate(month=TruncMonth("created_at")).values("month")
    return list(months.annotate(count=Count("id")).order_by("month"))

def posts_with_popularity() -> QuerySet[Post]:
    popularity = Case(
        When(comment_count__gte=HOT_COMMENTS, then=Value("hot")),
        When(comment_count__gte=NORMAL_COMMENTS, then=Value("normal")),
        default=Value("quiet"),
    )
    return (
        Post.objects.annotate(comment_count=Count("comments"))
        .annotate(popularity=popularity)
        .order_by("-comment_count", "-created_at")
    )

def get_or_create_tag(name: str) -> tuple[Tag, bool]:
    return Tag.objects.get_or_create(slug=slugify(name), defaults={"name": name})

def publish_old_drafts(days: int) -> int:
    now = timezone.now()
    old_drafts = Post.objects.filter(status=Post.Status.DRAFT, created_at__lt=now - timedelta(days=days))
    return old_drafts.update(status=Post.Status.PUBLISHED, updated_at=now)

def tag_category_posts(category_slug: str, tag_slug: str) -> int:
    tag = Tag.objects.filter(slug=tag_slug).first()
    if tag is None:
        return 0
    post_ids = list(Post.objects.filter(category__slug=category_slug).values_list("pk", flat=True))
    tag.posts.add(*post_ids)
    return len(post_ids)

@transaction.atomic
def merge_categories(source_slug: str, target_slug: str) -> int:
    target = Category.objects.filter(slug=target_slug).first()
    if target is None:
        return 0
    moved = Post.objects.filter(category__slug=source_slug).update(category=target)
    Category.objects.filter(slug=source_slug).delete()
    return moved

def  delete_inactive_users_comments() -> int:
    _, deleted_per_model = Comment.objects.filter(author__is_active=False).delete()
    return deleted_per_model.get(Comment._meta.label, 0)

def published_feed() -> list[str]:
    posts = (
        published_posts()
            .select_related("author", "category")
            .order_by("-created_at")[:FEED_LIMIT]
    )
    return [
        f"{post.title} | {post.author.email} | {post.category.name if post.category else UNCATEGORIZED}"
        for post in posts
    ]

def newest_posts_with_tags() -> list[str]:
    tags = Prefetch("tags", queryset=Tag.objects.order_by("name"))
    posts = Post.objects.prefetch_related(tags).order_by("-created_at")[:NEWES_TAGGED_LIMIT]
    return [f"{post.title}: {', '.join(tag.name for tag in post.tags.all())}" for post in posts]

def categories_with_published_posts() -> dict[str, list[str]]:
    posts = Prefetch("posts", queryset=published_posts().order_by("-created_at"), to_attr="published")
    categories = (
        Category.objects.filter(posts__status=Post.Status.PUBLISHED).distinct().prefetch_related(posts).order_by("name")
    )
    return {category.name: [post.title for post in category.published] for category in categories}

def posts_with_last_comment() -> QuerySet[Post]:
    newest = Comment.objects.filter(post=OuterRef("pk")).order_by("-created_at").values("body")[:1]
    return published_posts().annotate(last_comment=Subquery(newest))

def posts_with_staff_comments() -> QuerySet[Post]:
    staff_comments = Comment.objects.filter(post=OuterRef("pk"), author__is_staff=True)
    return Post.objects.filter(Exists(staff_comments))

def users_with_draft_as_latest_post() -> QuerySet:
    latest = Post.objects.filter(author=OuterRef("pk")).order_by("-created_at").values("status")[:1]
    return User.objects.annotate(latest_post_status=Subquery(latest)).filter(latest_post_status=Post.Status.DRAFT)

QUERIES = {
    1: categories_by_name,
    2: published_posts,
    3: newest_published_posts,
    4: post_by_slug,
    5: active_users_count,
    6: has_drafts,
    7: published_posts_page,
    8: posts_with_word_in_title,
    9: users_with_email_domain,
    10: posts_without_category,
    11: categories_by_slugs,
    12: posts_in_month,
    13: posts_last_days,
    14: posts_between,
    15: author_published_posts,
    16: posts_with_tag,
    17: comments_in_category,
    18: users_with_published_posts,
    19: posts_without_tags,
    20: users_without_comments,
    21: posts_with_both_tags,
    22: search_posts,
    23: published_posts_missing_info,
    24: edited_posts,
    25: comments_by_post_author,
    26: comments_before_post,
    27: published_authors_emails,
    28: published_posts_overview,
    29: posts_stats,
    30: average_comments_per_post,
    31: categories_with_post_count,
    32: categories_with_published_count,
    33: top_authors,
    34: popular_tags,
    35: posts_per_status,
    36: users_activity,
    37: search_users_by_full_name,
    38: published_posts_per_month,
    39: posts_with_popularity,
    40: get_or_create_tag,
    41: publish_old_drafts,
    42: tag_category_posts,
    43: merge_categories,
    44: delete_inactive_users_comments,
    45: published_feed,
    46: newest_posts_with_tags,
    47: categories_with_published_posts,
    48: posts_with_last_comment,
    49: posts_with_staff_comments,
    50: users_with_draft_as_latest_post,
}