from django.conf import settings
from django.db import models
from django.urls import reverse

# Параметры подгонки изображений с CDN Unsplash (используются как красивые
# плейсхолдеры, пока хост не загрузил собственные фото).
STOCK_SUFFIX = "?auto=format&fit=crop&w=1000&q=70"
STOCK_PHOTOS = {
    "cottage": [
        "https://images.unsplash.com/photo-1518780664697-55e3ad937233",
        "https://images.unsplash.com/photo-1564013799919-ab600027ffc6",
        "https://images.unsplash.com/photo-1576941089067-2de3c901e126",
        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c",
    ],
    "dacha": [
        "https://images.unsplash.com/photo-1480796927426-f609979314bd",
        "https://images.unsplash.com/photo-1449158743715-0a90ebb6d2d8",
        "https://images.unsplash.com/photo-1505691938895-1758d7feb511",
        "https://images.unsplash.com/photo-1416331108676-a22ccb276e35",
    ],
    "banya": [
        "https://images.unsplash.com/photo-1542718610-a1d656d1884c",
        "https://images.unsplash.com/photo-1610641818989-c2051b5e2cfd",
        "https://images.unsplash.com/photo-1560185007-cde436f6a4d0",
    ],
    "glamping": [
        "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4",
        "https://images.unsplash.com/photo-1537905569824-f89f14cceb68",
        "https://images.unsplash.com/photo-1455496231601-e6195da1f841",
    ],
    "zone": [
        "https://images.unsplash.com/photo-1470770841072-f978cf4d019e",
        "https://images.unsplash.com/photo-1439066615861-d1af74d74000",
        "https://images.unsplash.com/photo-1500534623283-312aade485b7",
    ],
}


class Amenity(models.Model):
    """Справочник удобств (бассейн, баня, мангал...). M:N с Property."""
    code = models.SlugField("Код", max_length=50, unique=True)
    name = models.CharField("Название", max_length=100)
    icon = models.CharField("Эмодзи/иконка", max_length=10, blank=True)

    class Meta:
        verbose_name = "Удобство"
        verbose_name_plural = "Удобства"

    def __str__(self):
        return self.name


class Property(models.Model):
    """Объект аренды — дача, коттедж, баня, глэмпинг, зона отдыха."""

    class Type(models.TextChoices):
        COTTAGE = "cottage", "Коттедж"
        DACHA = "dacha", "Дача"
        BANYA = "banya", "Баня/сауна"
        GLAMPING = "glamping", "Глэмпинг"
        ZONE = "zone", "Зона отдыха"

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликовано"
        SUSPENDED = "suspended", "Снято"

    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="properties",
        verbose_name="Хост",
    )
    title = models.CharField("Заголовок", max_length=200)
    description = models.TextField("Описание", blank=True)
    type = models.CharField("Тип", max_length=20, choices=Type.choices, default=Type.COTTAGE)
    status = models.CharField("Статус", max_length=20, choices=Status.choices, default=Status.DRAFT)

    # Локация
    region = models.CharField("Область", max_length=100, blank=True)
    city = models.CharField("Город/посёлок", max_length=100, db_index=True)
    address = models.CharField("Адрес", max_length=255, blank=True)
    latitude = models.DecimalField("Широта", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("Долгота", max_digits=9, decimal_places=6, null=True, blank=True)

    # Характеристики
    rooms = models.PositiveSmallIntegerField("Комнат", default=1)
    beds = models.PositiveSmallIntegerField("Спальных мест", default=1)
    max_guests = models.PositiveSmallIntegerField("Макс. гостей", default=2)
    area_sqm = models.PositiveSmallIntegerField("Площадь, м²", null=True, blank=True)

    # Цены — храним в тенге (целое) для MVP. В проде лучше в тиынах (BIGINT).
    base_price = models.PositiveIntegerField("Цена за сутки, ₸", default=0)
    weekend_price = models.PositiveIntegerField("Цена за выходные, ₸", null=True, blank=True)
    cleaning_fee = models.PositiveIntegerField("Уборка, ₸", default=0)

    # Правила
    min_nights = models.PositiveSmallIntegerField("Мин. ночей", default=1)
    instant_booking = models.BooleanField("Мгновенное бронирование", default=False)
    cancellation_policy = models.CharField(
        "Политика отмены", max_length=10,
        choices=[("flexible","Гибкая"),("moderate","Умеренная"),("strict","Строгая")],
        default="flexible",
    )

    amenities = models.ManyToManyField(Amenity, blank=True, related_name="properties", verbose_name="Удобства")

    rating = models.DecimalField("Рейтинг", max_digits=3, decimal_places=2, default=0)
    reviews_count = models.PositiveIntegerField("Отзывов", default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Объект"
        verbose_name_plural = "Объекты"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("property_detail", args=[self.pk])

    def price_for(self, day):
        """Цена за конкретный день: выходные (пт=4, сб=5) дороже, если задано."""
        if self.weekend_price and day.weekday() in (4, 5):
            return self.weekend_price
        return self.base_price

    @property
    def gallery(self):
        """Список URL фотографий: загруженные хостом или красивые стоковые по типу."""
        photos = list(self.photos.all())
        if photos:
            return [p.image.url for p in photos]
        pool = STOCK_PHOTOS.get(self.type, STOCK_PHOTOS["cottage"])
        # стабильный сдвиг по id, чтобы у разных объектов одного типа были разные фото
        shift = (self.id or 0) % len(pool)
        ordered = pool[shift:] + pool[:shift]
        return [u + STOCK_SUFFIX for u in ordered]

    @property
    def cover(self):
        return self.gallery[0]


class PropertyPhoto(models.Model):
    """Фото объекта (One-to-Many)."""
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField("Фото", upload_to="properties/")
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"Фото #{self.pk} для {self.property_id}"


class AvailabilityBlock(models.Model):
    """
    Ручная блокировка дат хостом (ремонт, личное использование).
    Доступность объекта = производная: день свободен, если нет активной брони
    И нет блокировки на этот день. Поэтому храним только исключения, а не каждый день.
    Полупериод [start, end): end — день выезда, сам по себе свободен.
    """
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="blocks")
    start_date = models.DateField("С")
    end_date = models.DateField("По (выезд)")
    reason = models.CharField("Причина", max_length=100, blank=True, default="Закрыто хостом")

    class Meta:
        verbose_name = "Блокировка дат"
        verbose_name_plural = "Блокировки дат"

    def __str__(self):
        return f"{self.property_id}: {self.start_date}–{self.end_date}"


class Favorite(models.Model):
    """Избранное гостя (M:N user↔property через явную модель)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        constraints = [
            models.UniqueConstraint(fields=["user", "property"], name="unique_user_favorite"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} ♥ {self.property_id}"
