from collections import defaultdict
from datetime import date

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from bookings.models import Booking
from bookings.services import booked_dates, is_available, quote, BookingError
from .forms import BlockForm, PropertyForm
from .models import Amenity, Favorite, Property


def _favorite_ids(user):
    """Множество id объектов в избранном пользователя (для подсветки сердечек)."""
    if not user.is_authenticated:
        return set()
    return set(Favorite.objects.filter(user=user).values_list("property_id", flat=True))


def home(request):
    """Главная + поиск/фильтрация."""
    qs = Property.objects.filter(status=Property.Status.PUBLISHED)

    city = request.GET.get("city", "").strip()
    ptype = request.GET.get("type", "").strip()
    guests = request.GET.get("guests", "").strip()
    amenity_codes = request.GET.getlist("amenity")
    check_in = request.GET.get("check_in", "").strip()
    check_out = request.GET.get("check_out", "").strip()
    price_min = request.GET.get("price_min", "").strip()
    price_max = request.GET.get("price_max", "").strip()

    if city:
        qs = qs.filter(city__icontains=city)
    if ptype:
        qs = qs.filter(type=ptype)
    if guests.isdigit():
        qs = qs.filter(max_guests__gte=int(guests))
    if price_min.isdigit():
        qs = qs.filter(base_price__gte=int(price_min))
    if price_max.isdigit():
        qs = qs.filter(base_price__lte=int(price_max))
    for code in amenity_codes:
        qs = qs.filter(amenities__code=code)
    qs = qs.distinct()

    # Сортировка (применяем к queryset до фильтра по датам — порядок сохранится в списке)
    sort = request.GET.get("sort", "").strip()
    sort_map = {
        "price": "base_price",
        "-price": "-base_price",
        "rating": "-rating",
        "new": "-created_at",
    }
    qs = qs.order_by(sort_map.get(sort, "-rating"), "-created_at")

    # Фильтр по датам — отсекаем занятые объекты (порядок сортировки сохраняется)
    if check_in and check_out:
        try:
            ci, co = date.fromisoformat(check_in), date.fromisoformat(check_out)
            qs = [p for p in qs if is_available(p, ci, co)]
        except ValueError:
            pass

    context = {
        "properties": qs,
        "amenities": Amenity.objects.all(),
        "types": Property.Type.choices,
        "filters": request.GET,
        "amenity_codes": amenity_codes,  # list — доступен в шаблоне без вызова методов
        "favorite_ids": _favorite_ids(request.user),
        "sort": sort or "rating",
        "sort_options": [
            ("rating", "Рекомендуем"),
            ("price", "Цена ↑"),
            ("-price", "Цена ↓"),
            ("new", "Новые"),
        ],
    }
    return render(request, "listings/home.html", context)


def property_detail(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    busy = sorted(d.isoformat() for d in booked_dates(prop))
    # Предрасчёт котировки, если переданы даты
    estimate = None
    ci = request.GET.get("check_in")
    co = request.GET.get("check_out")
    if ci and co:
        try:
            estimate = quote(prop, date.fromisoformat(ci), date.fromisoformat(co))
        except (ValueError, BookingError):
            estimate = None
    # bbox для встраиваемой карты OpenStreetMap (lon_min,lat_min,lon_max,lat_max)
    map_bbox = None
    if prop.latitude is not None and prop.longitude is not None:
        lat, lon = float(prop.latitude), float(prop.longitude)
        map_bbox = f"{lon - 0.02},{lat - 0.012},{lon + 0.02},{lat + 0.012}"

    guests = request.GET.get("guests", "1")
    if not guests.isdigit() or int(guests) < 1:
        guests = "1"

    context = {
        "property": prop,
        "busy_dates": busy,
        "today": date.today().isoformat(),
        "estimate": estimate,
        "check_in": ci or "",
        "check_out": co or "",
        "guests": guests,
        "map_bbox": map_bbox,
        "is_favorite": prop.pk in _favorite_ids(request.user),
        "reviews": prop.reviews.select_related("author")[:20],
        "service_fee_percent": settings.SERVICE_FEE_PERCENT,
    }
    return render(request, "listings/detail.html", context)


@require_POST
def favorite_toggle(request, pk):
    """AJAX-переключатель избранного. Возвращает {favorited: bool}."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "auth"}, status=401)
    prop = get_object_or_404(Property, pk=pk)
    fav = Favorite.objects.filter(user=request.user, property=prop)
    if fav.exists():
        fav.delete()
        favorited = False
    else:
        Favorite.objects.create(user=request.user, property=prop)
        favorited = True
    return JsonResponse({"favorited": favorited})


@login_required
def favorites_list(request):
    favs = Property.objects.filter(favorited_by__user=request.user).order_by("-favorited_by__created_at")
    return render(request, "listings/favorites.html", {
        "properties": favs, "favorite_ids": _favorite_ids(request.user),
    })


# ---------- Кабинет хоста ----------

@login_required
def host_dashboard(request):
    if not request.user.is_host:
        return redirect("become_host")
    properties = Property.objects.filter(host=request.user)
    return render(request, "listings/host_dashboard.html", {"properties": properties})


@login_required
def host_bookings(request):
    bookings = Booking.objects.filter(property__host=request.user).select_related("property", "guest")
    return render(request, "listings/host_bookings.html", {"bookings": bookings})


@login_required
def property_create(request):
    if not request.user.is_host:
        return redirect("become_host")
    if request.method == "POST":
        form = PropertyForm(request.POST)
        if form.is_valid():
            prop = form.save(commit=False)
            prop.host = request.user
            prop.save()
            form.save_m2m()
            # Загрузка фото (множественная)
            for f in request.FILES.getlist("photos"):
                prop.photos.create(image=f)
            messages.success(request, "Объект создан.")
            return redirect("host_dashboard")
    else:
        form = PropertyForm()
    return render(request, "listings/property_form.html", {"form": form, "is_new": True})


@login_required
def property_edit(request, pk):
    prop = get_object_or_404(Property, pk=pk, host=request.user)
    if request.method == "POST":
        form = PropertyForm(request.POST, instance=prop)
        if form.is_valid():
            form.save()
            for f in request.FILES.getlist("photos"):
                prop.photos.create(image=f)
            messages.success(request, "Объект обновлён.")
            return redirect("host_dashboard")
    else:
        form = PropertyForm(instance=prop)
    return render(request, "listings/property_form.html", {"form": form, "property": prop, "is_new": False})


@login_required
def property_calendar(request, pk):
    """Управление календарём: добавление и удаление блокировок."""
    prop = get_object_or_404(Property, pk=pk, host=request.user)
    if request.method == "POST":
        # Удаление блокировки
        del_pk = request.POST.get("delete_block")
        if del_pk:
            prop.blocks.filter(pk=del_pk).delete()
            return redirect("property_calendar", pk=pk)
        # Создание блокировки
        form = BlockForm(request.POST)
        if form.is_valid():
            block = form.save(commit=False)
            block.property = prop
            block.save()
            return redirect("property_calendar", pk=pk)
    else:
        form = BlockForm()
    busy = sorted(d.isoformat() for d in booked_dates(prop))
    bookings_data = [
        {"start": b.check_in.isoformat(), "end": b.check_out.isoformat(),
         "guest": str(b.guest), "nights": b.nights, "status": b.status}
        for b in Booking.objects.filter(
            property=prop, status__in=Booking.BLOCKING_STATUSES
        ).select_related("guest")
    ]
    return render(request, "listings/calendar.html", {
        "property": prop, "blocks": prop.blocks.all(),
        "busy_dates": busy, "bookings_data": bookings_data,
        "today": date.today().isoformat(),
    })


@login_required
def host_analytics(request):
    if not request.user.is_host:
        return redirect("become_host")

    ACTIVE = (Booking.Status.CONFIRMED, Booking.Status.COMPLETED, Booking.Status.PENDING_HOST)
    bookings = Booking.objects.filter(
        property__host=request.user, status__in=ACTIVE
    ).select_related("property")

    # --- Сводка ---
    total_bookings = bookings.count()
    total_earned = sum(b.host_payout for b in bookings)
    total_nights = sum(b.nights for b in bookings)
    avg_check = round(total_earned / total_bookings) if total_bookings else 0

    # --- По объектам ---
    by_prop = defaultdict(lambda: {"bookings": 0, "earned": 0, "name": ""})
    for b in bookings:
        key = b.property_id
        by_prop[key]["name"] = b.property.title
        by_prop[key]["bookings"] += 1
        by_prop[key]["earned"] += b.host_payout
    by_prop = sorted(by_prop.values(), key=lambda x: x["earned"], reverse=True)

    # --- По месяцам (последние 6 месяцев) ---
    monthly = defaultdict(lambda: {"earned": 0, "bookings": 0})
    for b in bookings:
        key = b.check_in.strftime("%Y-%m")
        monthly[key]["earned"] += b.host_payout
        monthly[key]["bookings"] += 1
    months_sorted = sorted(monthly.items())[-6:]

    # --- Предстоящие ---
    upcoming = Booking.objects.filter(
        property__host=request.user,
        status__in=ACTIVE,
        check_in__gte=date.today(),
    ).select_related("property", "guest").order_by("check_in")[:5]

    context = {
        "total_bookings": total_bookings,
        "total_earned": total_earned,
        "total_nights": total_nights,
        "avg_check": avg_check,
        "by_prop": by_prop,
        "monthly_labels": [m[0] for m in months_sorted],
        "monthly_earned": [m[1]["earned"] for m in months_sorted],
        "monthly_bookings": [m[1]["bookings"] for m in months_sorted],
        "upcoming": upcoming,
    }
    return render(request, "listings/analytics.html", context)


def properties_geojson(request):
    """GeoJSON для карты — все опубликованные объекты с координатами."""
    props = Property.objects.filter(
        status=Property.Status.PUBLISHED,
        latitude__isnull=False, longitude__isnull=False,
    ).prefetch_related("photos")
    features = []
    for p in props:
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(p.longitude), float(p.latitude)]},
            "properties": {
                "id": p.pk, "title": p.title, "city": p.city,
                "price": p.base_price, "rating": float(p.rating),
                "type": p.get_type_display(), "cover": p.cover,
                "url": p.get_absolute_url(),
            },
        })
    return JsonResponse({"type": "FeatureCollection", "features": features})
