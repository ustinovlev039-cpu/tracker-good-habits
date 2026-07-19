# Habit Tracker Backend

Учебный бэкенд SPA-трекера полезных привычек на Django REST Framework.

Для работы проекта используются:

- PostgreSQL — основная база данных;
- Redis — брокер сообщений Celery;
- Celery Worker — отправка напоминаний;
- Celery Beat — запуск проверки напоминаний каждую минуту;
- Telegram Bot API — доставка уведомлений.

Рабочее приложение использует PostgreSQL. SQLite применяется только в памяти
при автоматических тестах через `config.settings_test`. Docker в проекте не
используется: PostgreSQL, Redis, Django, Celery и Telegram-бот запускаются
локально.

## Что реализовано

- регистрация пользователей по email;
- JWT access/refresh-токены;
- CRUD личных привычек;
- запрет доступа к чужим привычкам;
- публичный список привычек без редактирования;
- пагинация по 5 привычек;
- валидаторы из задания;
- Swagger и ReDoc;
- CORS;
- привязка Telegram через одноразовый код;
- журнал отправленных и ошибочных уведомлений;
- периодические задачи Celery.

## Установка зависимостей

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```
## Применение миграций

```bash
python manage.py migrate
```

Создайте администратора:

```bash
python manage.py createsuperuser
```

## Запуск Django

```bash
python manage.py runserver
```

После запуска доступны:

- API: `http://127.0.0.1:8000/api/`
- Swagger: `http://127.0.0.1:8000/api/docs/`
- ReDoc: `http://127.0.0.1:8000/api/redoc/`
- Django Admin: `http://127.0.0.1:8000/admin/`

## Запуск Redis

Redis должен быть запущен до Celery.

### Linux

Пример запуска установленного Redis:

```bash
redis-server
```

Либо через системную службу:

```bash
sudo systemctl start redis-server
```

## Запуск Celery

Откройте отдельный терминал, активируйте `.venv` и запустите Worker.

### Linux/macOS

```bash
celery -A config worker -l INFO
```
## Запуск Telegram-бота

Создайте бота через BotFather и заполните `.env`:

```env
TELEGRAM_BOT_TOKEN=полученный_токен
TELEGRAM_BOT_USERNAME=имя_бота_без_символа_@
```

В отдельном терминале запустите:

```bash
python manage.py run_telegram_bot
```

## Какие процессы должны работать одновременно

Для полной работы проекта должны быть открыты четыре процесса:

1. Django:

```bash
python manage.py runserver
```

2. Celery Worker:

```bash
celery -A config worker -l INFO
```

3. Celery Beat:

```bash
celery -A config beat -l INFO
```

4. Telegram-бот:

```bash
python manage.py run_telegram_bot
```
## Основные эндпоинты

```text
POST   /api/users/register/
POST   /api/token/
POST   /api/token/refresh/

GET    /api/habits/
POST   /api/habits/
GET    /api/habits/{id}/
PUT    /api/habits/{id}/
PATCH  /api/habits/{id}/
DELETE /api/habits/{id}/

GET    /api/habits/public/

POST   /api/telegram/connect/
GET    /api/telegram/status/

GET    /api/schema/
GET    /api/docs/
GET    /api/redoc/
```

## Регистрация и JWT

Регистрация:

```http
POST /api/users/register/
Content-Type: application/json
```

```json
{
  "email": "student@example.com",
  "password": "strong-password-123"
}
```

Получение токена:

```http
POST /api/token/
Content-Type: application/json
```

```json
{
  "email": "student@example.com",
  "password": "strong-password-123"
}
```

Для защищённых запросов передавайте:

```http
Authorization: Bearer ACCESS_TOKEN
```

## Пример создания привычки

```json
{
  "place": "дома",
  "time": "08:00:00",
  "action": "сделать разминку",
  "is_pleasant": false,
  "related_habit": null,
  "periodicity": 1,
  "reward": "выпить кофе",
  "duration": 120,
  "is_public": true
}
```

## Запуск тестов

```bash
python manage.py test --settings=config.settings_test
```

Тестовый набор содержит 48 тестов. Django создаёт отдельную SQLite-базу в
памяти и удаляет её после тестов; основная PostgreSQL-конфигурация при этом не
изменяется.

## Запуск тестов с покрытием

```bash
coverage erase
coverage run manage.py test --settings=config.settings_test
coverage report -m
coverage html
```

Фактическое покрытие после полного прогона — 93%. Минимальный допустимый порог
в `.coveragerc` — 80%. HTML-отчёт открывается из `htmlcov/index.html`.
