from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from bookings.models import Booking, Review, recalc_property_rating
from listings.models import Amenity, AvailabilityBlock, Property

User = get_user_model()

AMENITIES = [
    ("pool", "Бассейн", "🏊"), ("banya", "Баня/сауна", "🧖"),
    ("bbq", "Мангал/барбекю", "🍖"), ("wifi", "Wi-Fi", "📶"),
    ("parking", "Парковка", "🅿️"), ("lake", "У водоёма", "🌊"),
    ("kitchen", "Кухня", "🍳"), ("playground", "Детская площадка", "🛝"),
]

PROPERTIES = [
    dict(title="Коттедж у Капшагая с бассейном", type="cottage", city="Капшагай",
         region="Алматинская обл.", rooms=4, beds=8, max_guests=10,
         base_price=45000, weekend_price=60000, cleaning_fee=5000, area_sqm=180,
         description="Просторный двухэтажный коттедж в 5 минутах от водохранилища. Большой бассейн, зона барбекю, мангал.",
         lat=43.8756, lon=77.0680, amen=["pool", "bbq", "wifi", "parking", "lake", "kitchen"]),
    dict(title="Уютная дача в Талгаре", type="dacha", city="Талгар",
         region="Алматинская обл.", rooms=2, beds=4, max_guests=5,
         base_price=20000, weekend_price=25000, cleaning_fee=2000, area_sqm=70,
         description="Тихая дача в горном предгорье. Сад, беседка, мангал. Идеально для семьи.",
         lat=43.3045, lon=77.2398, amen=["bbq", "wifi", "parking", "kitchen"]),
    dict(title="Баня на дровах + домик отдыха", type="banya", city="Алматы",
         region="Алматы", rooms=1, beds=2, max_guests=6,
         base_price=15000, cleaning_fee=1500, area_sqm=40,
         description="Настоящая русская баня на дровах с купелью. Комната отдыха, чай, веники.",
         lat=43.2389, lon=76.8897, amen=["banya", "bbq", "parking"]),
    dict(title="Глэмпинг-шатёр у гор", type="glamping", city="Иссык",
         region="Алматинская обл.", rooms=1, beds=2, max_guests=2,
         base_price=30000, weekend_price=38000, cleaning_fee=0, area_sqm=30,
         description="Купольный шатёр с панорамным видом на горы. Завтрак, костровая зона, звёздное небо.",
         lat=43.3520, lon=77.4500, amen=["bbq", "wifi", "lake"]),
    dict(title="Загородный дом для большой компании", type="cottage", city="Тургень",
         region="Алматинская обл.", rooms=5, beds=12, max_guests=15,
         base_price=70000, weekend_price=90000, cleaning_fee=8000, area_sqm=260,
         description="Огромный дом для корпоративов и торжеств. Бассейн, баня, караоке, большой банкетный зал.",
         lat=43.3000, lon=77.5800, amen=["pool", "banya", "bbq", "wifi", "parking", "kitchen", "playground"]),
    dict(title="Зона отдыха «Зелёный берег»", type="zone", city="Капшагай",
         region="Алматинская обл.", rooms=3, beds=6, max_guests=8,
         base_price=38000, weekend_price=50000, cleaning_fee=4000, area_sqm=150,
         description="База отдыха на берегу. Свой пляж, лодки, мангальные зоны, детская площадка.",
         lat=43.8800, lon=77.0500, amen=["bbq", "lake", "parking", "playground", "kitchen"]),
]


class Command(BaseCommand):
    help = "Наполняет БД демо-данными (хосты, гости, объекты, бронь)."

    def handle(self, *args, **opts):
        amen = {}
        for code, name, icon in AMENITIES:
            a, _ = Amenity.objects.get_or_create(code=code, defaults={"name": name, "icon": icon})
            amen[code] = a

        host, created = User.objects.get_or_create(
            username="host", defaults={"is_host": True, "first_name": "Айдос", "last_name": "Хозяин",
                                       "phone": "+77010000001", "verification": "verified"}
        )
        if created:
            host.set_password("host12345")
            host.save()

        guest, created = User.objects.get_or_create(
            username="guest", defaults={"first_name": "Гость", "phone": "+77010000002"}
        )
        if created:
            guest.set_password("guest12345")
            guest.save()

        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@dacha.kz", "admin12345")
            self.stdout.write("superuser admin/admin12345 создан")

        created_props = []
        for data in PROPERTIES:
            if Property.objects.filter(title=data["title"]).exists():
                continue
            p = Property.objects.create(
                host=host, title=data["title"], description=data["description"],
                type=data["type"], status=Property.Status.PUBLISHED,
                region=data["region"], city=data["city"],
                latitude=data["lat"], longitude=data["lon"],
                rooms=data["rooms"], beds=data["beds"], max_guests=data["max_guests"],
                area_sqm=data["area_sqm"], base_price=data["base_price"],
                weekend_price=data.get("weekend_price"), cleaning_fee=data["cleaning_fee"],
                min_nights=1, instant_booking=(data["type"] == "banya"),
            )
            p.amenities.set([amen[c] for c in data["amen"]])
            created_props.append(p)

        # демо-бронь и блокировка на первый объект
        if created_props:
            first = created_props[0]
            ci = date.today() + timedelta(days=7)
            co = ci + timedelta(days=3)
            Booking.objects.get_or_create(
                property=first, guest=guest, check_in=ci, check_out=co,
                defaults=dict(status=Booking.Status.CONFIRMED, guests_count=4, nights=3,
                              base_amount=135000, cleaning_fee=5000, service_fee=13500,
                              total_amount=153500, host_payout=140000),
            )
            AvailabilityBlock.objects.get_or_create(
                property=first, start_date=date.today() + timedelta(days=20),
                end_date=date.today() + timedelta(days=23), defaults={"reason": "Личное использование"},
            )

        # Прошедшие брони + отзывы, чтобы у объектов были реальные рейтинги.
        review_texts = [
            (5, "Отличное место, всё чисто и уютно. Обязательно вернёмся!"),
            (5, "Прекрасный вид, радушный хозяин, бассейн супер. Рекомендую."),
            (4, "Хорошо отдохнули, но Wi-Fi местами пропадал. В целом отлично."),
            (5, "Идеально для семьи с детьми. Мангал, баня — всё на высоте."),
        ]
        for idx, p in enumerate(Property.objects.all()):
            # каждая бронь в прошлом, без пересечений (свой диапазон дней назад)
            start = date.today() - timedelta(days=30 + idx * 5)
            past_ci, past_co = start, start + timedelta(days=2)
            b, created = Booking.objects.get_or_create(
                property=p, guest=guest, check_in=past_ci, check_out=past_co,
                defaults=dict(status=Booking.Status.COMPLETED, guests_count=2, nights=2,
                              base_amount=p.base_price * 2, cleaning_fee=p.cleaning_fee,
                              service_fee=round(p.base_price * 2 * 0.1),
                              total_amount=p.base_price * 2 + p.cleaning_fee + round(p.base_price * 2 * 0.1),
                              host_payout=p.base_price * 2 + p.cleaning_fee),
            )
            # отзыв на все, кроме последнего объекта — у него оставим бронь «к отзыву» для демо
            if created and idx < Property.objects.count() - 1:
                rating, text = review_texts[idx % len(review_texts)]
                Review.objects.get_or_create(
                    booking=b, defaults=dict(property=p, author=guest, rating=rating, comment=text),
                )

        # Пересчитываем рейтинги по фактическим отзывам (у объектов без отзывов → 0).
        for p in Property.objects.all():
            recalc_property_rating(p.id)

        self.stdout.write(self.style.SUCCESS(
            f"Готово. Объектов: {Property.objects.count()}. "
            f"Логины: host/host12345, guest/guest12345, admin/admin12345"
        ))
