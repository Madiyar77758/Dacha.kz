from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "phone", "is_host", "verification", "is_staff")
    list_filter = ("is_host", "verification", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Профиль площадки", {"fields": ("phone", "is_host", "verification", "avatar", "rating")}),
    )
