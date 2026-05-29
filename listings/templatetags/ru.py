"""Шаблонные фильтры для русской локали."""
import re
from django import template

register = template.Library()


@register.filter
def plural(number, forms):
    """
    Правильная форма слова для числа по русским правилам.
    Использование: {{ n }} {{ n|plural:"ночь,ночи,ночей" }}
    forms — три формы через запятую: 1 ночь / 2 ночи / 5 ночей.
    """
    try:
        n = abs(int(number))
    except (TypeError, ValueError):
        return ""
    parts = [f.strip() for f in forms.split(",")]
    if len(parts) != 3:
        return parts[-1] if parts else ""
    one, few, many = parts
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return few
    return many


@register.filter
def wa_number(phone):
    """Убирает всё кроме цифр, заменяет 8 в начале на 7 (для КЗ/РФ номеров)."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    return digits
