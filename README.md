# Habit Tracker

## Описание проекта

Habit Tracker — backend SPA-трекера полезных привычек на Django REST
Framework. Приложение поддерживает регистрацию по email, JWT-аутентификацию,
CRUD личных привычек, публичные привычки, правила полезных и приятных привычек,
периодические напоминания Celery и привязку Telegram.

Документация API доступна после запуска:

- Swagger: `http://127.0.0.1/api/docs/`;
- ReDoc: `http://127.0.0.1/api/redoc/`;
- OpenAPI schema: `http://127.0.0.1/api/schema/`;
- health endpoint: `http://127.0.0.1/health/`.

## Стек технологий

- Python 3.12, Django 5.2, Django REST Framework;
- PostgreSQL 16;
- Redis 7;
- Celery Worker и Celery Beat;
- Gunicorn;
- Nginx;
- Docker Engine и Docker Compose Plugin;
- Ruff;
- Django TestCase/APITestCase и coverage;
- GitHub Actions.

## Структура сервисов

| Сервис | Назначение | Доступ |
|---|---|---|
| `web` | Django API через Gunicorn | только внутри сети, порт 8000 |
| `migrate` | одноразово применяет миграции и собирает static | не публикуется |
| `db` | PostgreSQL | только внутри сети, порт 5432 |
| `redis` | broker и result backend Celery | только внутри сети, порт 6379 |
| `celery` | выполняет фоновые задачи | не публикуется |
| `celery-beat` | создаёт периодические задачи | не публикуется |
| `telegram-bot` | Telegram long polling | исходящие подключения |
| `nginx` | reverse proxy, static и media | `HTTP_PORT`, по умолчанию 80 |

`web`, `migrate`, `celery`, `celery-beat` и `telegram-bot` используют один
образ `habit-tracker-app`. Миграции и `collectstatic` выполняет только
одноразовый сервис `migrate`; остальные процессы ждут его успешного завершения.
PostgreSQL, Redis, static, media и schedule Celery Beat хранятся в именованных
volumes.

Если `TELEGRAM_BOT_TOKEN` пуст, контейнер `telegram-bot` остаётся запущенным,
но polling отключается. После добавления токена перезапустите сервис.

## Переменные окружения

Создайте локальный файл, который не попадает в Git:

```bash
cp .env.example .env
```

Основные переменные:

| Переменная | Назначение |
|---|---|
| `SECRET_KEY` | уникальный длинный секрет Django |
| `DEBUG` | `False` для production |
| `ALLOWED_HOSTS` | домены/IP через запятую, без схемы |
| `CSRF_TRUSTED_ORIGINS` | доверенные origin со схемой `http://` или `https://` |
| `CORS_ALLOWED_ORIGINS` | origin frontend со схемой |
| `POSTGRES_DB` | имя базы PostgreSQL |
| `POSTGRES_USER` | пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | пароль PostgreSQL |
| `POSTGRES_HOST` | `db` внутри Compose |
| `POSTGRES_PORT` | `5432` внутри Compose |
| `REDIS_HOST` | `redis` внутри Compose |
| `REDIS_PORT` | `6379` внутри Compose |
| `CELERY_BROKER_URL` | обычно `redis://redis:6379/0` |
| `CELERY_RESULT_BACKEND` | обычно `redis://redis:6379/1` |
| `TELEGRAM_BOT_TOKEN` | токен реально используемого Telegram-бота |
| `TELEGRAM_BOT_USERNAME` | username бота без `@` |
| `HTTP_PORT` | опубликованный порт Nginx |
| `TIME_ZONE` | часовой пояс Django и Celery |

Не помещайте в репозиторий `.env`, production-пароли, токены, приватные ключи
или реальные секреты. Значения из `.env.example` демонстрационные и должны быть
заменены.

Для домена `tracker.example.com` нужны как минимум:

```env
DEBUG=False
ALLOWED_HOSTS=tracker.example.com
CSRF_TRUSTED_ORIGINS=https://tracker.example.com
CORS_ALLOWED_ORIGINS=https://app.example.com
```

Если HTTPS завершается на доверенном reverse proxy, после проверки TLS можно
включить:

```env
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

Не включайте HSTS до полной проверки HTTPS: браузеры запоминают эту политику.

## Локальный запуск через Docker Compose

Требуются Docker Engine и современный Docker Compose Plugin.

```bash
cp .env.example .env
docker compose config
docker compose up -d --build
docker compose ps
```

Ручной запуск миграций, Celery или Nginx не требуется. При первом старте
`migrate` ждёт healthy-состояния PostgreSQL, применяет миграции и собирает
статику. Затем запускаются Gunicorn, Celery, Telegram-бот и Nginx.

Проверка:

```bash
curl -I http://127.0.0.1/api/docs/
curl http://127.0.0.1/health/
```

Если в `.env` задан другой `HTTP_PORT`, добавьте его к URL.

## Запуск тестов

Полный набор тестов с реальным PostgreSQL в Docker:

```bash
docker compose run --rm web \
  python manage.py test --settings=config.settings_test
```

Внешние обращения к Telegram в тестах замоканы. CI также использует настоящий
PostgreSQL service container и Redis service container.

Для локального быстрого запуска без Docker допустим SQLite в памяти:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
USE_SQLITE_FOR_TESTS=True \
  python manage.py test --settings=config.settings_test
```

Проверка миграций и coverage:

```bash
USE_SQLITE_FOR_TESTS=True \
  python manage.py makemigrations --check --dry-run \
  --settings=config.settings_test
USE_SQLITE_FOR_TESTS=True \
  coverage run manage.py test --settings=config.settings_test
coverage report
```

## Запуск линтинга

Проект использует только Ruff; миграции, virtualenv, coverage и кеши исключены
из проверки.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
ruff check .
```

## Полезные Docker-команды

Состояние всех сервисов, включая завершившийся `migrate`:

```bash
docker compose ps --all
```

Логи всего проекта и отдельных сервисов:

```bash
docker compose logs -f
docker compose logs --tail=100 web celery celery-beat nginx
```

Проверка Nginx и неприменённых миграций:

```bash
docker compose exec nginx nginx -t
docker compose exec web python manage.py migrate --check
```

Повторная сборка и запуск:

```bash
docker compose up -d --build
```

Перезапуск Telegram-бота после добавления токена:

```bash
docker compose up -d --force-recreate telegram-bot
```

## CI/CD

Workflow находится в `.github/workflows/ci.yml`, называется `CI/CD` и
запускается при каждом `push` и `pull_request`.

Jobs выполняются независимо, а deploy ждёт все проверки:

1. `lint` устанавливает зависимости и запускает `ruff check .`;
2. `tests` запускает PostgreSQL и Redis, проверяет их готовность, применяет
   миграции, выполняет Django tests с coverage и валидирует OpenAPI schema;
3. `docker-build` валидирует оба Compose-файла, запускает
   `docker build --check`, собирает Compose image и выполняет `nginx -t`;
4. `deploy` зависит от `lint`, `tests` и `docker-build`.

Автоматический deploy запускается только при успешном `push` в ветку `main`.
Основная ветка определена по `origin/main`.

На сервере workflow:

```text
cd DEPLOY_PATH
git fetch --prune origin main
git reset --hard origin/main
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  up -d --build --remove-orphans
```

Перед деплоем workflow отдельно проверяет наличие всех Secrets, формат
приватного ключа и `known_hosts`, SSH-аутентификацию, доступ пользователя к
Docker, Git-репозиторию, production `.env` и `DEPLOY_PATH`.

После запуска workflow проверяет код завершения одноразового сервиса `migrate`,
конфигурацию Nginx, отсутствие неприменённых миграций, наличие admin static и
локальный `/health/` на сервере. Последним отдельным шагом GitHub runner
проверяет публичный `${APP_URL}/health/`. Только после успешных проверок
выполняется `docker image prune -f`. `.env` уже должен безопасно находиться на
сервере: workflow не создаёт, не изменяет и не передаёт его.

## GitHub Secrets

Добавьте repository Secrets в
`Settings → Secrets and variables → Actions → Repository secrets`:

| Secret | Содержимое |
|---|---|
| `SERVER_HOST` | реальный публичный домен или IP SSH-сервера |
| `SERVER_PORT` | фактический SSH-порт |
| `SERVER_USER` | отдельный пользователь деплоя |
| `SERVER_SSH_KEY` | приватная часть отдельного ключа GitHub Actions без passphrase |
| `SERVER_KNOWN_HOSTS` | проверенная строка known_hosts сервера |
| `DEPLOY_PATH` | абсолютный путь, например `/srv/habit-tracker` |
| `APP_URL` | реальный публичный base URL приложения со схемой |

Production `.env` не является GitHub Secret этого workflow: он создаётся один
раз непосредственно на сервере с правами `600`.

Проверить наличие Secrets без чтения их значений:

```bash
gh secret list
```

Безопасный интерактивный ввод каждого значения:

```bash
gh secret set SERVER_HOST
gh secret set SERVER_PORT
gh secret set SERVER_USER
gh secret set SERVER_SSH_KEY
gh secret set SERVER_KNOWN_HOSTS
gh secret set DEPLOY_PATH
gh secret set APP_URL
```

Для приватного ключа также можно передать содержимое через stdin, не помещая
его в аргументы командной строки:

```bash
gh secret set SERVER_SSH_KEY < /secure/path/to/deploy_key
```

Получите `known_hosts` на доверенной машине, подставив фактические host и port:

```bash
ssh-keyscan -H -p "$SERVER_PORT" "$SERVER_HOST" \
  > habit-tracker-known-hosts
ssh-keyscan -p "$SERVER_PORT" "$SERVER_HOST" 2>/dev/null \
  | ssh-keygen -lf -
```

На самом сервере получите fingerprint хост-ключа:

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Сверьте fingerprint с fingerprint ключа на сервере по отдельному доверенному
каналу, затем поместите всё содержимое файла в `SERVER_KNOWN_HOSTS`. Для
нестандартного порта запись будет содержать `[host]:port`. Workflow использует
`StrictHostKeyChecking=yes` и не добавляет неизвестные ключи автоматически.

## Подготовка удалённого сервера

Ниже приведён вариант для Ubuntu. Актуальная схема установки пакетов взята из
[официальной инструкции Docker Engine для Ubuntu](https://docs.docker.com/engine/install/ubuntu/);
Compose устанавливается как plugin, standalone `docker-compose` не нужен.

### 1. Создание пользователя деплоя

Выполните от существующего администратора:

```bash
sudo adduser deploy
sudo install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
sudo install -d -m 755 -o deploy -g deploy /srv/habit-tracker
```

### 2. Установка Docker Engine и Compose Plugin

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Добавьте официальный apt-репозиторий:

```bash
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

Установите и включите сервис:

```bash
sudo apt-get update
sudo apt-get install -y \
  docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker deploy
```

Группа `docker` даёт привилегированный доступ к Docker daemon. Добавляйте в неё
только доверенного пользователя деплоя. Завершите его SSH-сессию и войдите
заново, затем проверьте:

```bash
docker --version
docker compose version
docker run --rm hello-world
```

### 3. SSH-ключ GitHub Actions

Создайте отдельный ключ на доверенной локальной машине, не на GitHub runner:

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" \
  -f habit-tracker-github-actions
ssh-copy-id -i habit-tracker-github-actions.pub deploy@server.example.com
```

Либо вручную добавьте одну строку из `.pub` в:

```text
/home/deploy/.ssh/authorized_keys
```

На сервере проверьте права:

```bash
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

Приватный файл `habit-tracker-github-actions` сохраните только в
`SERVER_SSH_KEY`. Никогда не добавляйте его в Git. Ключ должен быть без
passphrase и сохранять строки `BEGIN/END OPENSSH PRIVATE KEY` и исходные
переносы.

До настройки GitHub Actions проверьте ключ вручную:

```bash
ssh-keygen -y -f /secure/path/to/deploy_key >/dev/null
ssh-keygen -yf /secure/path/to/deploy_key | ssh-keygen -lf -

ssh \
  -p "$SERVER_PORT" \
  -i /secure/path/to/deploy_key \
  -o BatchMode=yes \
  -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=/secure/path/to/known_hosts \
  "$SERVER_USER@$SERVER_HOST" \
  'echo SSH_OK'
```

Если команда возвращает `Permission denied (publickey)`, проверьте, что
соответствующая публичная часть добавлена отдельной строкой именно в
`/home/<SERVER_USER>/.ssh/authorized_keys`, владелец корректен, каталог имеет
права `700`, а файл — `600`.

### 4. Клонирование репозитория

Войдите как `deploy` и клонируйте репозиторий:

```bash
git clone <REPOSITORY_URL> /srv/habit-tracker
cd /srv/habit-tracker
git switch main
```

Для приватного репозитория отдельно настройте на сервере read-only deploy key
или другой безопасный доступ к `git fetch`. Этот ключ не должен совпадать с
ключом, которым GitHub Actions входит на сервер.

### 5. Production `.env`

Создайте файл непосредственно на сервере:

```bash
cd /srv/habit-tracker
cp .env.example .env
chmod 600 .env
nano .env
```

Замените все демонстрационные значения. Обязательно задайте production
`SECRET_KEY`, пароль PostgreSQL, реальные домены/IP, trusted origins и при
использовании Telegram — токен и username бота. Оставьте `POSTGRES_HOST=db`,
`REDIS_HOST=redis`, внутренние порты 5432/6379 и `DEBUG=False`.

### 6. Firewall

Сначала разрешите реальный SSH-порт, и только затем включайте UFW:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

Порты 5432, 6379 и 8000 открывать не требуется. Учтите
[особенности Docker и firewall](https://docs.docker.com/engine/install/ubuntu/#firewall-limitations):
публикуемые Docker-порты могут обходить некоторые правила UFW. В этом Compose
наружу публикуется только порт Nginx.

Для стабильной фоновой записи Redis на Linux рекомендуется включить memory
overcommit:

```bash
echo 'vm.overcommit_memory=1' | \
  sudo tee /etc/sysctl.d/99-habit-tracker-redis.conf
sudo sysctl --system
```

## Первый деплой

Первый запуск выполните вручную от пользователя `deploy`:

```bash
cd /srv/habit-tracker
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  config
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  up -d --build
```

Проверьте сервисы, миграции, static и HTTP:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  ps --all
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  logs --tail=100
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  exec web python manage.py migrate --check
curl http://127.0.0.1/health/
```

Только после успешного первого запуска добавьте перечисленные GitHub Secrets и
сделайте test push/merge в `main`.

## Автоматический деплой

При успешном push в `main` GitHub Actions подключается к серверу по SSH,
переходит строго в `DEPLOY_PATH`, обновляет рабочую копию до `origin/main` и
пересоздаёт только изменившиеся контейнеры. Одноразовый `migrate` не позволяет
нескольким процессам одновременно выполнять миграции или `collectstatic`.

Файл `.env` переживает `git reset --hard`, потому что он игнорируется Git и
хранится только на сервере. Не добавляйте его принудительно через `git add -f`.

Проверить последние runs и повторно запустить неуспешный run после изменения
только Secrets:

```bash
gh run list --limit 5
gh run rerun <RUN_ID> --failed
gh run watch <RUN_ID> --exit-status
gh run view <RUN_ID>
```

Если менялся workflow, создайте новый commit и push в `main`, а не перезапускайте
старый run: повтор старого run использует старую версию workflow.

Публичный адрес для `APP_URL` берётся из DNS-записи проекта или панели
провайдера сервера. Он должен совпадать с реально опубликованным Nginx и
значением `ALLOWED_HOSTS`. Для HTTPS origin также добавьте в
`CSRF_TRUSTED_ORIGINS`.

## Проверка состояния и логов

Локально:

```bash
docker compose ps
docker compose ps --all
docker compose logs -f
docker compose logs --tail=200
```

На production используйте оба Compose-файла:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  ps --all
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  logs -f --tail=200
```

Полезные отдельные проверки:

```bash
docker compose exec nginx nginx -t
docker compose exec celery celery -A config inspect ping
curl -I http://127.0.0.1/api/docs/
curl -i "${APP_URL%/}/health/"
```

## Остановка проекта

Остановка контейнеров с сохранением данных:

```bash
docker compose down
```

Удаление контейнеров вместе с volumes:

```bash
docker compose down -v
```

Внимание: `docker compose down -v` безвозвратно удалит данные PostgreSQL,
Redis, media, static и schedule Celery Beat. Не выполняйте эту команду на
production без проверенной резервной копии.

## Типовые проблемы

### Compose сообщает, что переменная обязательна

Убедитесь, что создан `.env` и заполнены `POSTGRES_DB`, `POSTGRES_USER`,
`POSTGRES_PASSWORD` и `SECRET_KEY`:

```bash
test -s .env
docker compose config
```

### PostgreSQL или Redis не становятся healthy

```bash
docker compose ps
docker compose logs --tail=200 db redis
```

Проверьте, что значения базы в `.env` не менялись после создания
`postgres_data`. При намеренной смене учётных данных обновите роль внутри
PostgreSQL либо пересоздайте volume только при допустимой потере данных.

### `migrate` завершился с ошибкой

```bash
docker compose ps --all
docker compose logs migrate
docker compose run --rm migrate
```

`web`, Celery и Nginx не стартуют, пока `migrate` не завершится с кодом 0.

### Django возвращает `DisallowedHost` или CSRF error

Добавьте фактический домен/IP в `ALLOWED_HOSTS`, а полный origin со схемой в
`CSRF_TRUSTED_ORIGINS`. После изменения:

```bash
docker compose up -d --force-recreate web celery celery-beat telegram-bot
```

### Celery Worker не подключается

```bash
docker compose logs --tail=200 celery redis
docker compose exec celery celery -A config inspect ping
```

Проверьте `REDIS_HOST=redis`, `REDIS_PORT=6379` и Celery URLs.

### Nginx возвращает 502

```bash
docker compose ps
docker compose logs --tail=200 web nginx
docker compose exec nginx nginx -t
curl http://127.0.0.1/health/
```

### Telegram polling отключён

Заполните `TELEGRAM_BOT_TOKEN` и `TELEGRAM_BOT_USERNAME`, затем:

```bash
docker compose up -d --force-recreate telegram-bot
docker compose logs -f telegram-bot
```

## Основные API endpoints

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
