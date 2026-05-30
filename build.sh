#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# seed идемпотентен — повторно не дублирует данные
python manage.py seed
