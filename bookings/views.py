from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from listings.models import Property
from .models import Booking, Review
from .services import BookingError, create_booking, quote


def _parse(s):
    return date.fromisoformat(s)


@login_required
def create(request, property_id):
    """Создание брони из формы на странице объекта."""
    prop = get_object_or_404(Property, pk=property_id, status=Property.Status.PUBLISHED)
    if request.method != "POST":
        return redirect(prop)

    try:
        check_in = _parse(request.POST["check_in"])
        check_out = _parse(request.POST["check_out"])
        guests = int(request.POST.get("guests", 1))
    except (KeyError, ValueError):
        messages.error(request, "Укажите корректные даты заезда и выезда.")
        return redirect(prop)

    if prop.host_id == request.user.id:
        messages.error(request, "Нельзя забронировать собственный объект.")
        return redirect(prop)

    try:
        booking = create_booking(prop, request.user, check_in, check_out, guests)
    except BookingError as e:
        messages.error(request, str(e))
        return redirect(prop)

    if booking.status == Booking.Status.CONFIRMED:
        messages.success(request, f"✅ Бронь подтверждена! Оплата наличными при заезде — {booking.total_amount:,} ₸.")
    else:
        messages.success(request, "📨 Заявка отправлена хосту. Ответ в течение 24 часов. Оплата наличными при заезде.")
    return redirect("my_bookings")


@login_required
def pay(request, pk):
    """Имитация оплаты (Kaspi/карта подключаются здесь в проде)."""
    booking = get_object_or_404(Booking, pk=pk, guest=request.user)
    if request.method == "POST":
        # TODO: интеграция Kaspi Pay / банковский эквайринг с холдированием средств.
        # После успешной оплаты: instant-объект -> сразу подтверждено,
        # иначе -> ждёт подтверждения хоста (request-to-book).
        if booking.status == Booking.Status.PENDING_PAYMENT:
            if booking.property.instant_booking:
                booking.status = Booking.Status.CONFIRMED
                msg = "Оплата прошла, бронь подтверждена! (демо)"
            else:
                booking.status = Booking.Status.PENDING_HOST
                msg = "Оплата прошла, ждём подтверждения хоста. (демо)"
            booking.save(update_fields=["status"])
            messages.success(request, msg)
        return redirect("my_bookings")
    return render(request, "bookings/pay.html", {"booking": booking})


@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(guest=request.user).select_related("property")
    return render(request, "bookings/my_bookings.html", {"bookings": bookings})


@login_required
def cancel(request, pk):
    booking = get_object_or_404(Booking, pk=pk, guest=request.user)
    if request.method == "POST" and booking.status in (
        Booking.Status.PENDING_PAYMENT,
        Booking.Status.PENDING_HOST,
        Booking.Status.CONFIRMED,
    ):
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=["status"])
        messages.info(request, "Бронь отменена.")
    return redirect("my_bookings")


@login_required
def host_decision(request, pk):
    """Хост подтверждает или отклоняет заявку (Request-to-Book)."""
    booking = get_object_or_404(Booking, pk=pk, property__host=request.user)
    action = request.POST.get("action")
    if request.method == "POST" and booking.status == Booking.Status.PENDING_HOST:
        if action == "confirm":
            booking.status = Booking.Status.CONFIRMED
            messages.success(request, "Бронь подтверждена.")
        elif action == "reject":
            booking.status = Booking.Status.REJECTED
            messages.info(request, "Бронь отклонена.")
        booking.save(update_fields=["status"])
    return redirect("host_bookings")


@login_required
def review_create(request, pk):
    """Оставить отзыв по завершённой брони (один отзыв на бронь)."""
    booking = get_object_or_404(Booking, pk=pk, guest=request.user)
    if not booking.is_reviewable():
        messages.error(request, "Оставить отзыв можно только после завершённой поездки.")
        return redirect("my_bookings")

    if request.method == "POST":
        try:
            rating = int(request.POST.get("rating", 5))
        except ValueError:
            rating = 5
        rating = min(5, max(1, rating))
        Review.objects.create(
            booking=booking,
            property=booking.property,
            author=request.user,
            rating=rating,
            comment=request.POST.get("comment", "").strip(),
        )
        messages.success(request, "Спасибо за отзыв!")
        return redirect(booking.property)

    return render(request, "bookings/review_form.html", {"booking": booking})
