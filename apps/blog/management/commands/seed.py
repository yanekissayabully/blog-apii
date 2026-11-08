"""Management command that fills the database with fake data."""

import random
import time
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils.text import slugify
from faker import Faker

from apps.blog.models import Category, Comment, Post, Tag

User = get_user_model()

# --- Defaults for the command arguments ---
DEFAULT_USERS = 20
DEFAULT_POSTS = 100
DEFAULT_COMMENTS = 500

# --- Users ---
SEED_PASSWORD = "seedpass123"
EMAIL_DOMAIN = "example.com"
INACTIVE_USER_CHANCE = 0.15
STAFF_USER_CHANCE = 0.10

# --- Posts ---
PUBLISHED_CHANCE = 0.70
NO_CATEGORY_CHANCE = 0.10
MAX_TAGS_PER_POST = 5
TITLE_WORDS = 6
MIN_PARAGRAPHS = 3
MAX_PARAGRAPHS = 6
SLUG_MAX_LENGTH = 50

# --- Comments ---
MIN_COMMENT_SENTENCES = 1
MAX_COMMENT_SENTENCES = 3

# --- Summary output ---
LABEL_WIDTH = 11
COUNT_WIDTH = 4

CATEGORY_NAMES = [
    "Python",
    "Django",
    "DevOps",
    "Databases",
    "Frontend",
    "Testing",
    "Security",
    "Career",
]

TAG_NAMES = [
    "api",
    "rest",
    "orm",
    "postgresql",
    "docker",
    "git",
    "linux",
    "celery",
    "redis",
    "asyncio",
    "typing",
    "pytest",
    "deployment",
    "performance",
    "refactoring",
    "tutorial",
    "best-practices",
    "authentication",
    "caching",
    "tips",
]


class Command(BaseCommand):
    help = "Fill the database with fake data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--users", type=int, default=DEFAULT_USERS, help="Number of users to create")
        parser.add_argument("--posts", type=int, default=DEFAULT_POSTS, help="Number of posts to create")
        parser.add_argument("--comments", type=int, default=DEFAULT_COMMENTS, help="Number of comments to create")
        parser.add_argument("--clear", action="store_true", help="Delete existing data before seeding")

    def handle(self, *args: Any, **options: Any) -> None:
        users_count: int = options["users"]
        posts_count: int = options["posts"]
        comments_count: int = options["comments"]
        clear: bool = options["clear"]

        self._validate_counts(users_count, posts_count, comments_count)

        started_at = time.perf_counter()
        fake = Faker()

        # One transaction: if something fails, the database stays as it was.
        with transaction.atomic():
            if clear:
                self._clear()

            users_created = self._create_users(fake, users_count)
            categories_created = self._create_named(Category, CATEGORY_NAMES)
            tags_created = self._create_named(Tag, TAG_NAMES)

            user_ids = list(User.objects.values_list("pk", flat=True))
            if (posts_count or comments_count) and not user_ids:
                raise CommandError("There are no users in the database. Use --users or create a user first.")

            posts_created = self._create_posts(fake, posts_count, user_ids)

            published_ids = list(Post.objects.filter(status=Post.Status.PUBLISHED).values_list("pk", flat=True))
            if comments_count and not published_ids:
                raise CommandError("There are no published posts to comment on. Use --posts or publish a post first.")

            comments_created = self._create_comments(fake, comments_count, user_ids, published_ids)

        elapsed = time.perf_counter() - started_at
        self._print_summary(
            [
                ("Users:", users_created),
                ("Categories:", categories_created),
                ("Tags:", tags_created),
                ("Posts:", posts_created),
                ("Comments:", comments_created),
            ],
            elapsed,
        )

    def _validate_counts(self, *counts: int) -> None:
        if any(count < 0 for count in counts):
            raise CommandError("Numbers of users, posts and comments must not be negative.")

    def _clear(self) -> None:
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Tag.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write("Old data deleted (superusers kept).")

    def _create_users(self, fake: Faker, count: int) -> int:
        used_emails: set[str] = set(User.objects.values_list("email", flat=True))
        password = make_password(SEED_PASSWORD)  # hash once: hashing is slow on purpose

        users: list[Any] = []
        for _ in range(count):
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = self._unique_email(first_name, last_name, used_emails)
            users.append(
                User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password,
                    is_active=random.random() >= INACTIVE_USER_CHANCE,
                    is_staff=random.random() < STAFF_USER_CHANCE,
                )
            )
        User.objects.bulk_create(users)
        return len(users)

    @staticmethod
    def _unique_email(first_name: str, last_name: str, used_emails: set[str]) -> str:
        base = f"{slugify(first_name)}.{slugify(last_name)}"
        email = f"{base}@{EMAIL_DOMAIN}"
        number = 1
        while email in used_emails:
            number += 1
            email = f"{base}{number}@{EMAIL_DOMAIN}"
        used_emails.add(email)
        return email

    @staticmethod
    def _create_named(model: type[Category] | type[Tag], names: list[str]) -> int:
        existing_slugs: set[str] = set(model.objects.values_list("slug", flat=True))
        new_objects = [model(name=name, slug=slugify(name)) for name in names if slugify(name) not in existing_slugs]
        model.objects.bulk_create(new_objects)
        return len(new_objects)

    @staticmethod
    def _unique_slug(title: str, used_slugs: set[str]) -> str:
        base = slugify(title)[:SLUG_MAX_LENGTH] or "post"
        slug = base
        number = 1
        while slug in used_slugs:
            number += 1
            suffix = f"-{number}"
            slug = base[: SLUG_MAX_LENGTH - len(suffix)] + suffix
        used_slugs.add(slug)
        return slug

    def _create_posts(self, fake: Faker, count: int, user_ids: list[int]) -> int:
        if count == 0:
            return 0

        category_ids = list(Category.objects.values_list("pk", flat=True))
        tag_ids = list(Tag.objects.values_list("pk", flat=True))
        used_slugs: set[str] = set(Post.objects.values_list("slug", flat=True))

        posts: list[Post] = []
        for _ in range(count):
            title = fake.sentence(nb_words=TITLE_WORDS).rstrip(".")
            has_category = category_ids and random.random() >= NO_CATEGORY_CHANCE
            is_published = random.random() < PUBLISHED_CHANCE
            posts.append(
                Post(
                    author_id=random.choice(user_ids),
                    title=title,
                    slug=self._unique_slug(title, used_slugs),
                    body="\n\n".join(fake.paragraphs(nb=random.randint(MIN_PARAGRAPHS, MAX_PARAGRAPHS))),
                    category_id=random.choice(category_ids) if has_category else None,
                    status=Post.Status.PUBLISHED if is_published else Post.Status.DRAFT,
                )
            )
        created_posts = Post.objects.bulk_create(posts)

        for post in created_posts:
            tags_number = random.randint(0, min(MAX_TAGS_PER_POST, len(tag_ids)))
            post.tags.set(random.sample(tag_ids, tags_number))
        return len(created_posts)

    @staticmethod
    def _create_comments(fake: Faker, count: int, user_ids: list[int], published_ids: list[int]) -> int:
        comments = [
            Comment(
                post_id=random.choice(published_ids),
                author_id=random.choice(user_ids),
                body=" ".join(fake.sentences(nb=random.randint(MIN_COMMENT_SENTENCES, MAX_COMMENT_SENTENCES))),
            )
            for _ in range(count)
        ]
        Comment.objects.bulk_create(comments)
        return len(comments)

    def _print_summary(self, rows: list[tuple[str, int]], elapsed: float) -> None:
        for label, count in rows:
            self.stdout.write(f"{label:<{LABEL_WIDTH}}{count:>{COUNT_WIDTH}} created")
        self.stdout.write(self.style.SUCCESS(f"Done in {elapsed:.2f} seconds"))