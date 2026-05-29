from django.contrib import admin

from .models import Amenity, AvailabilityBlock, Favorite, Property, PropertyPhoto


class PhotoInline(admin.TabularInline):
    model = PropertyPhoto
    extra = 1


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "city", "base_price", "host", "status")
    list_filter = ("type", "status", "city")
    search_fields = ("title", "city", "address")
    filter_horizontal = ("amenities",)
    inlines = [PhotoInline]


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "icon")


admin.site.register(AvailabilityBlock)
admin.site.register(Favorite)
