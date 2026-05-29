from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class SignUpForm(UserCreationForm):
    full_name = forms.CharField(label="Имя и фамилия", max_length=150, required=False)
    phone = forms.CharField(label="Телефон", max_length=20, required=False)
    as_host = forms.BooleanField(label="Я хочу сдавать жильё (хост)", required=False)

    class Meta:
        model = User
        fields = ("username", "full_name", "phone")

    def save(self, commit=True):
        user = super().save(commit=False)
        full = self.cleaned_data.get("full_name", "").strip()
        if full:
            parts = full.split(" ", 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ""
        user.phone = self.cleaned_data.get("phone") or None
        user.is_host = self.cleaned_data.get("as_host", False)
        if commit:
            user.save()
        return user
