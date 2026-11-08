"""Admin forms for the custom User model (it has no `username`, only `email`)."""

from django.contrib.auth import get_user_model
from unfold.forms import UserChangeForm as UnfoldUserChangeForm
from unfold.forms import UserCreationForm as UnfoldUserCreationForm

User = get_user_model()


class UserCreationForm(UnfoldUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")


class UserChangeForm(UnfoldUserChangeForm):
    class Meta:
        model = User
        fields = "__all__"