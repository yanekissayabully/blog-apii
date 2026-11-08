from typing import ClassVar

from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.blog.models import Category, Comment, Post, Tag

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    pass

@admin.register(Tag)
class TagAdmin(ModelAdmin):
    pass

@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_filter: ClassVar[list[str]] = ["status"]

@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    pass