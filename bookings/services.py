"""
Ядро бизнес-логики бронирования: проверка доступности и защита от овербукинга.

Принцип пересечения интервалов (полуинтервалы [in, out)):
    два диапазона A и B пересекаются  <=>  A.start < B.end  И  A.end > B.start
Поскольку out — это день выезда (объект в этот день уже свободен), используем
строгие неравенства: заезд новой брони ровно в день выезда старой НЕ конфликтует.
"""
from datetime import date, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q

from listings.models import AvailabilityBlock, Property
from .models import Booking


class BookingError(Exception):
    """Бизнес-ошибка бронирования (показывается пользователю)."""


def overlapping_bookings(property, check_in, check_out, exclude_pk=None):
    """Активные брони объекта, пересекающиеся с [check_in, check_out)."""
    qs = Booking.objects.filter(
        property=property,
        status__in=Booking.BLOCKING_STATUSES,
        check_in__lt=check_out,
        check_out__gt=check_in,
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs


def overlapping_blocks(property, check_in, check_out):
    """Ручные блокировки хоста, пересекающиеся с [check_in, check_out)."""
    return AvailabilityBlock.objects.filter(
        property=property,
        start_date__lt=check_out,
        end_date__gt=check_in,
    )


def is_available(property, check_in, check_out, exclude_pk=None):
    """True, если интервал свободен (нет ни броней, ни блокировок)."""
    if overlapping_bookings(property, check_in, check_out, exclude_pk).exists():
        return False
    if overlapping_blocks(property, check_in, check_out).exists():
        return False
    return True


def booked_dates(property, horizon_days=365):
    """
    Множество занятых дат на горизонт (для подсветки в календаре).
    Возвращает set объектов date — каждая ночь, занятая бронью или блокировкой.
    День выезда НЕ включается (он свободен для следующего заезда).
    """
    today = date.today()
    limit = today + timedelta(days=horizon_days)
    busy = set()

    def _fill(start, end):
        d = max(start, today)
        while d < min(end, limit):
            busy.add(d)
            d += timedelta(days=1)

    for b in Booking.objects.filter(
        property=property, status__in=Booking.BLOCKING_STATUSES, check_out__gt=today
    ):
        _fill(b.check_in, b.check_out)
    for blk in AvailabilityBlock.objects.filter(property=property, end_date__gt=today):
        _fill(blk.start_date, blk.end_date)
    return busy


def quote(property, check_in, check_out):
    """Расчёт стоимости. Возвращает dict со всеми составляющими."""
    nights = (check_out - check_in).days
    if nights < 1:
        raise BookingError("Дата выезда должна быть позже даты заезда.")
    if nights < property.min_nights:
        raise BookingError(f"Минимальный срок аренды — {property.min_nights} ноч.")

    base_amount = 0
    d = check_in
    while d < check_out:
        base_amount += property.price_for(d)
        d += timedelta(days=1)

    cleaning = property.cleaning_fee
    service_fee = round(base_amount * settings.SERVICE_FEE_PERCENT / 100)
    total = base_amount + cleaning + service_fee
    host_payout = base_amount + cleaning  # хост получает без нашей комиссии гостя
    return {
        "nights": nights,
        "base_amount": base_amount,
        "cleaning_fee": cleaning,
        "service_fee": service_fee,
        "total_amount": total,
        "host_payout": host_payout,
    }


@transaction.atomic
def create_booking(property, guest, check_in, check_out, guests_count):
    """
    Атомарно и безопасно создаёт бронь.

    Защита от овербукинга в два рубежа:
    1) select_for_update() блокирует строку объекта на время транзакции —
       параллельные брони этого объекта выполняются строго по очереди,
       поэтому проверка is_available() не может «разойтись» с реальностью
       (классический race condition «двое проверили — оба записали»).
    2) В PostgreSQL поверх этого включается EXCLUDE-ограничение на уровне БД
       (см. миграцию 0002) — абсолютная гарантия, даже если код ошибётся.
    """
    # Лочим объект — сериализуем конкурентные брони одного и того же коттеджа.
    locked = Property.objects.select_for_update().get(pk=property.pk)

    if guests_count > locked.max_guests:
        raise BookingError(f"Максимум гостей: {locked.max_guests}.")

    if not is_available(locked, check_in, check_out):
        raise BookingError("Эти даты уже заняты. Выберите другие.")

    q = quote(locked, check_in, check_out)

    # Оплата наличными при заезде — онлайн-оплата не требуется.
    # Instant-объекты подтверждаются сразу, остальные ждут решения хоста.
    status = (
        Booking.Status.CONFIRMED
        if locked.instant_booking
        else Booking.Status.PENDING_HOST
    )
    booking = Booking.objects.create(
        property=locked,
        guest=guest,
        check_in=check_in,
        check_out=check_out,
        guests_count=guests_count,
        status=status,
        **q,
    )
    return booking
