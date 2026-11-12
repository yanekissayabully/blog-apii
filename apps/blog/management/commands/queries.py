"""Management command that runs the ORM queries from apps/blog/queries.py."""

from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection
from django.db.models import Model, QuerySet
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django.utils.text import slugify

from apps.blog.management.commands.seed import CATEGORY_NAMES, EMAIL_DOMAIN, TAG_NAMES
from apps.blog.models import Comment, Post
from apps.blog.queries import QUERIES

User = get_user_model()

# Queries 40-44 change data, so a plain `queries` run skips them.
MODIFYING_QUERIES = range(40, 45)
ROWS_TO_SHOW = 5
COMMENT_PREVIEW = 50

# --- Sample values for the arguments ---
LAST_DAYS = 180
BETWEEN_DAYS = 90
POPULAR_TAG_MIN_POSTS = 5
OLD_DRAFTS_DAYS = 30


def build_sample_arguments() -> dict[int, dict[str, Any]]:
    """Arguments for the queries: {number: {argument: value}}. They give non-empty results.

    Slugs come from the seed lists; the email, word and dates come from the database.
    """
    today = timezone.localdate()
    category_slug = slugify(CATEGORY_NAMES[0])
    tag_slug = slugify(TAG_NAMES[0])
    second_tag_slug = slugify(TAG_NAMES[1])

    author_email = User.objects.filter(posts__status=Post.Status.PUBLISHED).values_list("email", flat=True).first()
    first_name = User.objects.exclude(first_name="").values_list("first_name", flat=True).first()
    post = Post.objects.order_by("-created_at").values_list("slug", "title", "created_at").first()
    slug, title, created_at = post or ("", "", timezone.now())
    word = title.split()[0] if title else ""

    return {
        4: {"slug": slug},
        7: {"page": 1},
        8: {"word": word},
        9: {"domain": EMAIL_DOMAIN},
        11: {"slugs": [category_slug, slugify(CATEGORY_NAMES[1])]},
        12: {"year": created_at.year, "month": created_at.month},
        13: {"days": LAST_DAYS},
        14: {"start": today - timedelta(days=BETWEEN_DAYS), "end": today},
        15: {"email": author_email or ""},
        16: {"tag_slug": tag_slug},
        17: {"category_slug": category_slug},
        21: {"first_slug": tag_slug, "second_slug": second_tag_slug},
        22: {"text": word},
        34: {"min_posts": POPULAR_TAG_MIN_POSTS},
        37: {"text": first_name or ""},
        40: {"name": TAG_NAMES[0].title()},
        41: {"days": OLD_DRAFTS_DAYS},
        42: {"category_slug": category_slug, "tag_slug": tag_slug},
        43: {"source_slug": slugify(CATEGORY_NAMES[-1]), "target_slug": category_slug},
    }


class Command(BaseCommand):
    help = "Run the ORM queries and show their results."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--number", type=int, help="Run only the query with this number")
        parser.add_argument("--sql", action="store_true", help="Also print the SQL of each query")

    def handle(self, *args: Any, **options: Any) -> None:
        number: int | None = options["number"]
        show_sql: bool = options["sql"]

        if number is None:
            numbers = [n for n in sorted(QUERIES) if n not in MODIFYING_QUERIES]
        elif number in QUERIES:
            numbers = [number]
        else:
            raise CommandError(f"There is no query number {number}.")

        arguments = build_sample_arguments()
        for n in numbers:
            self._run(n, QUERIES[n], arguments.get(n, {}), show_sql)

    def _run(self, number: int, function: Callable[..., Any], kwargs: dict[str, Any], show_sql: bool) -> None:
        with CaptureQueriesContext(connection) as context:
            result = function(**kwargs)
            # A QuerySet is lazy: it hits the database only when we read it.
            rows = list(result) if isinstance(result, QuerySet) else result

        count = len(context)
        word = "SQL query" if count == 1 else "SQL queries"
        self.stdout.write(self.style.MIGRATE_HEADING(f"#{number} {function.__name__} — {count} {word}"))

        if isinstance(result, QuerySet):
            self._print_rows(rows, list(result.query.annotations))
        elif isinstance(result, list):
            self._print_rows(rows, [])
        elif isinstance(result, dict):
            self._print_rows([f"{key}: {value}" for key, value in result.items()], [], noun="items")
        elif isinstance(result, Model):
            self.stdout.write(f"    {result}")
        else:
            self.stdout.write(f"    {result!r}")

        if show_sql:
            for captured in context.captured_queries:
                self.stdout.write(f"    SQL: {captured['sql']}")
        self.stdout.write("")

    def _print_rows(self, rows: list[Any], annotations: list[str], noun: str = "rows") -> None:
        for row in rows[:ROWS_TO_SHOW]:
            self.stdout.write(f"    {self._describe(row, annotations)}")
        self.stdout.write(f"    ({len(rows)} {noun})")

    @staticmethod
    def _describe(row: Any, annotations: list[str]) -> str:
        """Text for one row. For model objects, annotated values are added in brackets."""
        if isinstance(row, Comment):
            # str(comment) would load the author and the post: extra queries just for printing.
            return f"Comment #{row.pk}: {row.body[:COMMENT_PREVIEW]}"
        if isinstance(row, Model):
            extras = ", ".join(f"{name}={getattr(row, name)}" for name in annotations if hasattr(row, name))
            return f"{row} [{extras}]" if extras else str(row)
        return str(row)