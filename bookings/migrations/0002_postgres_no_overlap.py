"""
Производственная защита от овербукинга на уровне БД (только PostgreSQL).

Добавляет EXCLUSION-ограничение через расширение btree_gist: невозможно вставить
две активные брони одного объекта с пересекающимися диапазонами дат — даже если
в коде приложения окажется баг. На SQLite (MVP) миграция пропускается.

Чтобы включить: переключите DATABASES на PostgreSQL и выполните migrate.
"""
from django.db import migrations


SQL_FORWARD = """
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE bookings_booking
    ADD CONSTRAINT no_overlapping_bookings
    EXCLUDE USING gist (
        property_id WITH =,
        daterange(check_in, check_out, '[)') WITH &&
    )
    WHERE (status IN ('pending_host', 'confirmed', 'completed'));
"""

SQL_REVERSE = """
ALTER TABLE bookings_booking DROP CONSTRAINT IF EXISTS no_overlapping_bookings;
"""


def apply_if_postgres(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(SQL_FORWARD)


def reverse_if_postgres(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(SQL_REVERSE)


class Migration(migrations.Migration):
    dependencies = [("bookings", "0001_initial")]
    operations = [migrations.RunPython(apply_if_postgres, reverse_if_postgres)]
