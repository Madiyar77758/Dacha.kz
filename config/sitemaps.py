from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from listings.models import Property


class StaticSitemap(Sitemap):
    """Статичные страницы."""
    priority = 0.8
    changefreq = "weekly"
    protocol = "https"

    def items(self):
        return ["home"]

    def location(self, item):
        return reverse(item)


class PropertySitemap(Sitemap):
    """Все опубликованные объекты."""
    priority = 0.9
    changefreq = "daily"
    protocol = "https"

    def items(self):
        return Property.objects.filter(status=Property.Status.PUBLISHED)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()