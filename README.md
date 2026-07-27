# Habit Tracker Backend

Бэкенд SPA-трекера полезных привычек на Django REST Framework.

В состав проекта входят:

- Django REST Framework и Gunicorn;
- PostgreSQL;
- Redis;
- Celery Worker и Celery Beat;
- Telegram-бот;
- Nginx;
- Docker Compose;
- GitHub Actions с цепочкой tests → lint → build → deploy.

## Возможности

- регистрация пользователей по email;
- JWT access/refresh-токены;
- CRUD личных привычек;
- публичный список привычек;
- пагинация;
- проверка правил полезных и приятных привычек;
- Swagger и ReDoc;
- CORS;
- привязка Telegram;
- периодические уведомления Celery.

## Запуск через Docker Compose

Требуются Docker Engine и Docker Compose.

Создайте локальный файл окружения:

```bash
cp .env.template .env
```

Замените в `.env` как минимум:

- `SECRET_KEY`;
- `POSTGRES_PASSWORD`;
- `ALLOWED_HOSTS`;
- `CORS_ALLOWED_ORIGINS`;
- `CSRF_TRUSTED_ORIGINS`;
- `TELEGRAM_BOT_TOKEN`;
- `TELEGRAM_BOT_USERNAME`.

Запустите проект:

```bash
docker compose config
docker compose up --detach --build
docker compose ps
```

Проверка состояния:

```bash
curl http://127.0.0.1/health/
```

После запуска доступны:

- API: `http://127.0.0.1/api/`;
- Swagger: `http://127.0.0.1/api/docs/`;
- ReDoc: `http://127.0.0.1/api/redoc/`;
- Django Admin: `http://127.0.0.1/admin/`.

PostgreSQL, Redis и Gunicorn доступны только внутри Docker-сети. Наружу
публикуется только Nginx на порту `HTTP_PORT`, по умолчанию — `80`.

Все контейнеры используют `restart: unless-stopped`, поэтому автоматически
перезапускаются после сбоя процесса или перезапуска Docker daemon.

Остановка:

```bash
docker compose down
```

Данные PostgreSQL, Redis, static и media находятся в именованных Docker volumes.
Для удаления volumes используется отдельная явная команда:

```bash
docker compose down --volumes
```

## Локальная установка зависимостей

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
cp .env.template .env
```

При запуске компонентов без Docker замените в `.env` адреса `db` и `redis` на
`127.0.0.1`.

## Тесты и линтер

```bash
python manage.py check --settings=config.settings_test
python manage.py makemigrations --check --dry-run --settings=config.settings_test
coverage erase
coverage run manage.py test --settings=config.settings_test
coverage report
ruff check .
```

Тесты используют SQLite в памяти и не обращаются к production PostgreSQL.
Минимальное покрытие настроено на 80% в `.coveragerc`.

## Основные эндпоинты

```text
GET    /health/

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

## CI/CD

Workflow находится в `.github/workflows/ci.yml` и запускается при каждом push и
pull request.

Последовательность job:

1. `tests` — Django checks, проверка миграций, тесты и coverage, OpenAPI schema;
2. `lint` — Ruff, запускается только после успешных тестов;
3. `build` — проверка Compose и сборка Docker image;
4. `deploy` — запускается только после успешного build при push в `main`.

Ошибка любого этапа останавливает зависимые этапы. PR выполняет tests, lint и
build, но не выполняет production deploy.

## Подготовка production-сервера

На сервере должны быть установлены Docker Engine, Docker Compose plugin, UFW и
OpenSSH Server. Пользователь деплоя должен иметь доступ к Docker и каталогу
проекта.

Пример подготовки firewall для стандартного SSH-порта:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw enable
sudo ufw status verbose
```

Если SSH использует другой порт, разрешите именно его до включения UFW. Порты
5432, 6379 и 8000 открывать на сервере не нужно.

Создайте отдельную пару SSH-ключей для деплоя:

```bash
ssh-keygen -t ed25519 -C habit-tracker-deploy -f habit_tracker_deploy
ssh-copy-id -i habit_tracker_deploy.pub deploy@SERVER_HOST
```

Закрытый ключ не добавляется в репозиторий.

## GitHub Actions secrets

В настройках репозитория создайте:

- `SERVER_SSH_KEY` — содержимое закрытого deploy-ключа;
- `SERVER_KNOWN_HOSTS` — проверенная строка known_hosts сервера;
- `SERVER_HOST` — IP или домен сервера;
- `SERVER_USER` — пользователь деплоя;
- `SERVER_PORT` — SSH-порт;
- `DEPLOY_PATH` — абсолютный каталог проекта на сервере;
- `PRODUCTION_ENV` — полное содержимое production `.env`.

Получить строку known_hosts можно командой:

```bash
ssh-keyscan -H -p SERVER_PORT SERVER_HOST
```

Перед добавлением результата в secret обязательно сверьте fingerprint ключа с
сервером по доверенному каналу.

Для `PRODUCTION_ENV` используйте `.env.template` как список обязательных
переменных и замените все демонстрационные значения. Workflow передаёт файл на
сервер с правами текущего пользователя и `umask 077`; значение не попадает в
Docker build context благодаря `.dockerignore`.

## IP, домен и HTTPS

Для запуска по IP добавьте IP в `ALLOWED_HOSTS`. Для домена добавьте домен в
`ALLOWED_HOSTS`, а адрес frontend — в `CORS_ALLOWED_ORIGINS` и
`CSRF_TRUSTED_ORIGINS`.

Если TLS завершается на внешнем reverse proxy или балансировщике, установите:

```env
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

HSTS включайте только после проверки корректной работы HTTPS.

## Чек-лист pull request

Перед открытием PR из `dev` в `main`:

- все изменения добавлены в Git, включая `.github/workflows/ci.yml`;
- `.env`, ключи, `.venv`, `__pycache__`, coverage и IDE-файлы не добавлены;
- тесты и Ruff проходят локально;
- Docker Compose проходит проверку и image собирается;
- в описании PR указаны изменения, инструкция проверки и изменения secrets/env;
- workflow PR завершён успешно;
- production deploy выполняется только после merge/push в `main`.
