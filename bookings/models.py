from datetime import date

from django.conf import settings
from django.db import models
from django.db.models import Avg, Count

from listings.models import Property


class Booking(models.Model):
    """
    Бронирование. Полуинтервал [check_in, check_out):
    check_out — день выезда, поэтому новая бронь может начинаться в этот день
    (заезд после выезда предыдущего гостя).
    """

    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Ждёт оплаты"
        PENDING_HOST = "pending_host", "Ждёт подтверждения хоста"
        CONFIRMED = "confirmed", "Подтверждено"
        CANCELLED = "cancelled", "Отменено"
        COMPLETED = "completed", "Завершено"
        REJECTED = "rejected", "Отклонено"

    # Статусы, которые «занимают» календарь (учитываются при проверке овербукинга).
    BLOCKING_STATUSES = (
        Status.PENDING_HOST, Status.CONFIRMED, Status.COMPLETED,
    )

    property = models.ForeignKey(Property, on_delete=models.PROTECT, related_name="bookings")
    guest = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings")

    check_in = models.DateField("Заезд")
    check_out = models.DateField("Выезд")
    guests_count = models.PositiveSmallIntegerField("Гостей", default=1)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT)

    # Финансовый снимок на момент брони (цены потом могут измениться)
    nights = models.PositiveSmallIntegerField(default=1)
    base_amount = models.PositiveIntegerField("Проживание, ₸", default=0)
    cleaning_fee = models.PositiveIntegerField("Уборка, ₸", default=0)
    service_fee = models.PositiveIntegerField("Сервисный сбор, ₸", default=0)
    total_amount = models.PositiveIntegerField("Итого к оплате, ₸", default=0)
    host_payout = models.PositiveIntegerField("К выплате хосту, ₸", default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(check_out__gt=models.F("check_in")),
                name="checkout_after_checkin",
            ),
        ]

    def __str__(self):
        return f"Бронь #{self.pk} · {self.property.title} · {self.check_in}–{self.check_out}"

    def is_reviewable(self):
        """Поездка завершена (выезд в прошлом, бронь не отменена) и отзыва ещё нет.
        Не @property: имя поля `property` в этом классе перекрывает встроенный property."""
        if self.status not in (self.Status.CONFIRMED, self.Status.COMPLETED):
            return False
        if self.check_out > date.today():
            return False
        return not Review.objects.filter(booking=self).exists()


class Review(models.Model):
    """Отзыв гостя об объекте. Один отзыв на одну бронь."""
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="review")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField("Оценка", default=5)  # 1..5
    comment = models.TextField("Отзыв", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.rating}★ от {self.author_id} · {self.property_id}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        recalc_property_rating(self.property_id)


def recalc_property_rating(property_id):
    """Пересчитывает средний рейтинг и число отзывов объекта."""
    agg = Review.objects.filter(property_id=property_id).aggregate(
        avg=Avg("rating"), n=Count("id")
    )
    Property.objects.filter(pk=property_id).update(
        rating=round(agg["avg"] or 0, 2), reviews_count=agg["n"] or 0
    )
