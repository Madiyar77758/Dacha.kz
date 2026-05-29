from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Единая модель пользователя. Один человек может быть и гостем, и хостом
    одновременно (флаг is_host «надстраивается» поверх обычного аккаунта).
    """

    class Verification(models.TextChoices):
        NONE = "none", "Не верифицирован"
        PENDING = "pending", "На проверке"
        VERIFIED = "verified", "Верифицирован"
        REJECTED = "rejected", "Отклонён"

    phone = models.CharField("Телефон", max_length=20, unique=True, null=True, blank=True)
    is_host = models.BooleanField("Является хостом", default=False)
    verification = models.CharField(
        "Верификация",
        max_length=10,
        choices=Verification.choices,
        default=Verification.NONE,
    )
    avatar = models.ImageField("Аватар", upload_to="avatars/", null=True, blank=True)
    rating = models.DecimalField("Рейтинг", max_digits=3, decimal_places=2, default=0)

    def __str__(self):
        return self.get_full_name() or self.username
