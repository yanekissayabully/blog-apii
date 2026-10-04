from django.db import models
from typing import Any
# Create your models here.

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,   
    PermissionsMixin,
)

NAME_MAX_LENGTH = 50
EMAIL_REQUIRED_MESSAGE = "NE MOZHET BIT PUSTIM"

class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> 'User': 
        if not email:
            raise ValueError(EMAIL_REQUIRED_MESSAGE)
        user = self.model(email=email.lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self.db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields: Any) -> 'User': 
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=NAME_MAX_LENGTH, blank=True)
    last_name = models.CharField(max_length=NAME_MAX_LENGTH, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self) -> str:
        return self.email