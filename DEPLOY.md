# Деплой Dacha.kz на PythonAnywhere (бесплатно, без карты)

Хостинг: **PythonAnywhere** · БД: **MySQL** · Стоимость: **0 ₸**

Везде замените `ВАШ_ЛОГИН` на ваш логин PythonAnywhere.

---

## 1. Залить код на GitHub

```bash
# создайте приватный репозиторий dacha-kz на github.com, затем:
git remote add origin https://github.com/ВАШ_GITHUB/dacha-kz.git
git branch -M main
git push -u origin main
```

## 2. Регистрация на PythonAnywhere

1. https://www.pythonanywhere.com/registration/register/beginner/ — бесплатный план **Beginner**.
2. Подтвердите e-mail, войдите.

## 3. Создать MySQL базу

Вкладка **Databases**:
1. Задайте пароль MySQL (запомните его) → **Initialize MySQL**.
2. В поле «Create a database» введите `dachakaz` → **Create**.
3. Полное имя БД будет: `ВАШ_ЛОГИН$dachakaz`.
4. Хост БД: `ВАШ_ЛОГИН.mysql.pythonanywhere-services.com`.

## 4. Скачать код на сервер

Вкладка **Consoles** → **Bash**:
```bash
git clone https://github.com/ВАШ_GITHUB/dacha-kz.git
cd dacha-kz
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 5. Создать .env на сервере

```bash
nano .env
```
Вставьте (подставив свои значения — пароль БД и SECRET_KEY):
```
SECRET_KEY=длинная-случайная-строка
DEBUG=False
ALLOWED_HOSTS=ВАШ_ЛОГИН.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://ВАШ_ЛОГИН.pythonanywhere.com
MYSQL_DB=ВАШ_ЛОГИН$dachakaz
MYSQL_USER=ВАШ_ЛОГИН
MYSQL_PASSWORD=ваш_пароль_БД
MYSQL_HOST=ВАШ_ЛОГИН.mysql.pythonanywhere-services.com
MYSQL_PORT=3306
```
Сохранить: `Ctrl+O`, `Enter`, выйти `Ctrl+X`.

Сгенерировать SECRET_KEY можно так:
```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

## 6. Миграции, статика, демо-данные

```bash
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py seed          # демо-объекты (по желанию)
# или свой админ:
python manage.py createsuperuser
```

## 7. Создать Web-приложение

Вкладка **Web** → **Add a new web app**:
1. **Manual configuration** (НЕ «Django»!) → **Python 3.10**.
2. В разделе **Code**:
   - Source code: `/home/ВАШ_ЛОГИН/dacha-kz`
   - Working directory: `/home/ВАШ_ЛОГИН/dacha-kz`
3. **Virtualenv**: `/home/ВАШ_ЛОГИН/dacha-kz/venv`

## 8. Настроить WSGI

В разделе **Code** нажмите на ссылку **WSGI configuration file**, удалите всё и вставьте:

```python
import os
import sys
from pathlib import Path

path = "/home/ВАШ_ЛОГИН/dacha-kz"
if path not in sys.path:
    sys.path.insert(0, path)

# Загрузка .env
from dotenv import load_dotenv  # если не установлен — см. ниже
load_dotenv(os.path.join(path, ".env"))

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

> Наш settings.py сам читает .env (своя функция load_dotenv), поэтому строки
> с `dotenv` можно убрать — оставьте только path + DJANGO_SETTINGS_MODULE + application.

Упрощённый вариант WSGI (рекомендуется):
```python
import sys
path = "/home/ВАШ_ЛОГИН/dacha-kz"
if path not in sys.path:
    sys.path.insert(0, path)
import os
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

## 9. Раздача статики

Вкладка **Web** → раздел **Static files** → Add:
| URL | Directory |
|-----|-----------|
| `/static/` | `/home/ВАШ_ЛОГИН/dacha-kz/staticfiles` |
| `/media/`  | `/home/ВАШ_ЛОГИН/dacha-kz/media` |

## 10. Запуск

Вкладка **Web** → большая зелёная кнопка **Reload**.
Сайт: **https://ВАШ_ЛОГИН.pythonanywhere.com**

---

## Обновление после изменений кода
```bash
cd ~/dacha-kz && git pull
source venv/bin/activate
pip install -r requirements.txt      # если менялись зависимости
python manage.py migrate
python manage.py collectstatic --no-input
# затем Web → Reload
```

## Частые проблемы
- **DisallowedHost** → проверьте ALLOWED_HOSTS в .env.
- **CSRF verification failed** → добавьте домен в CSRF_TRUSTED_ORIGINS (с https://).
- **Стили не грузятся** → проверьте Static files mapping и что collectstatic выполнен.
- **mysqlclient не ставится** → на PythonAnywhere он работает; если локально нужно — поставьте отдельно.