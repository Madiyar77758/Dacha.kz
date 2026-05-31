"""Выставляет домен сайта (для sitemap) из переменной SITE_DOMAIN."""
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Устанавливает Site.domain = settings.SITE_DOMAIN (для корректного sitemap.xml)"

    def handle(self, *args, **opts):
        domain = getattr(settings, "SITE_DOMAIN", "")
        if not domain:
            self.stdout.write("SITE_DOMAIN не задан — пропускаю.")
            return
        site, _ = Site.objects.get_or_create(pk=settings.SITE_ID)
        site.domain = domain
        site.name = "Dacha.kz"
        site.save()
        self.stdout.write(self.style.SUCCESS(f"Site domain → {domain}"))