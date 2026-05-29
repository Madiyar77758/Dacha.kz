from django.contrib import admin

from .models import Booking, Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("property", "author", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("property__title", "author__username", "comment")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "guest", "check_in", "check_out", "status", "total_amount")
    list_filter = ("status",)
    date_hierarchy = "check_in"
    search_fields = ("property__title", "guest__username")
