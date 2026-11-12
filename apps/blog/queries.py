from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.utils import timezone

from apps.blog.models import Category, Post, Comment

User = get_user_model()

NEWEST_POSTS_LIMIT = 5
PAGE_SIZE = 10

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
}