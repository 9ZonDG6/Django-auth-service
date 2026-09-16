# Django-auth-service

[![CI](https://github.com/9ZonDG6/Django-auth-service/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/9ZonDG6/Django-auth-service/actions/workflows/ci.yml)

Сервис общей аутентификации на Django и Django REST Framework. Хранит пользователей,
проверяет пароли и выдаёт JWT с подписью RS256. Для проверки токенов другими
микросервисами используем **JWKS**: публичные ключи доступны по адресу
`/.well-known/jwks.json`, а заголовок `kid` в JWT указывает нужный ключ.
Сервис-потребитель получает и кэширует JWKS, затем проверяет токены локально.
Приватный ключ и доступ к базе пользователей ему не нужны. Такой способ
проверки уже используется в [Django-tasks-service](https://github.com/9ZonDG6/Django-tasks-service).

## Быстрый запуск

Нужны Python 3.14+ и `uv`. Для локального запуска достаточно SQLite — отдельную
базу поднимать не нужно.

Из корня проекта:

```bash
uv sync --locked
cp .env.example .env
uv run python manage.py migrate
uv run python manage.py createsuperuser
make server
```

Если `.env` уже существует, сохрани свои настройки вместо повторного копирования.
Ключи JWT в `.env.example` предназначены только для разработки и CI.

После запуска доступны:

- Swagger: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI: http://localhost:8000/api/schema/
- Админка: http://localhost:8000/admin/
- Публичный ключ в формате JWKS: http://localhost:8000/.well-known/jwks.json

Есть `make createsuperuser`: он создаёт **admin/admin** и работает только при
`ENVIRONMENT=local`.

## API

Тела запросов передаются в JSON. Для защищённых эндпоинтов нужен заголовок
`Authorization: Bearer <access>`.

| Метод | Адрес                     | Что делает                                        | Нужен access |
| ----- | ------------------------- | ------------------------------------------------- | ------------ |
| POST  | `/api/v1/users/register/`        | Создаёт пользователя                              | Нет          |
| POST  | `/api/v1/auth/login/`            | Возвращает access и refresh                       | Нет          |
| POST  | `/api/v1/auth/refresh/`          | Заменяет refresh и выдаёт новый access            | Нет          |
| POST  | `/api/v1/auth/logout/`           | Отзывает переданный refresh текущего пользователя | Да           |
| GET   | `/api/v1/users/me/`              | Возвращает профиль                                | Да           |
| POST  | `/api/v1/users/change-password/` | Меняет пароль и отзывает все refresh пользователя | Да           |
| GET   | `/.well-known/jwks.json`         | Возвращает публичный ключ                         | Нет          |

### Регистрация и вход

```bash
curl -X POST http://localhost:8000/api/v1/users/register/ \
  -H 'Content-Type: application/json' \
  -d '{"username": "alice", "password": "Example-Pass-92!", "email": "alice@example.com"}'

curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username": "alice", "password": "Example-Pass-92!"}'
```

Регистрация возвращает профиль с кодом `201` и добавляет пользователя в группу
`user`. Токены нужно получить отдельным запросом на вход:

```json
{
  "refresh": "<refresh-token>",
  "access": "<access-token>"
}
```

При регистрации обязательны `username` и `password`. Дополнительно можно передать
`email`, `first_name`, `last_name`, `patronymic` и `phone` (до 11 символов).
Пароли проверяются валидаторами Django и хешируются с помощью Argon2.

### Профиль, обновление и выход

```bash
curl http://localhost:8000/api/v1/users/me/ \
  -H 'Authorization: Bearer <access-token>'

curl -X POST http://localhost:8000/api/v1/auth/refresh/ \
  -H 'Content-Type: application/json' \
  -d '{"refresh": "<refresh-token>"}'

curl -X POST http://localhost:8000/api/v1/auth/logout/ \
  -H 'Authorization: Bearer <access-token>' \
  -H 'Content-Type: application/json' \
  -d '{"refresh": "<refresh-token>"}'
```

После обновления сохрани **оба новых токена**: использованный refresh отзывается.
Для выхода передавай актуальный refresh. Успешный выход возвращает `205` без тела.

Для смены пароля отправь на `/api/v1/users/change-password/` поля `old_password` и
`new_password` с access-токеном в заголовке. После успешной смены нужно войти заново.

## Как устроены токены

- Подпись — **RS256**. Приватный ключ хранится у сервиса авторизации.
- Access действует **15 минут**, refresh — **7 дней** с момента выдачи.
- При обновлении создаётся новая пара с актуальными ролями и признаками пользователя.
- В токены добавляются `username`, `roles`, `is_staff` и `is_superuser`.
- Заголовок `kid` связывает токен с ключом из `/.well-known/jwks.json`.
- Значение `iss` задаётся через `JWT_ISSUER`.

Другой сервис должен проверять подпись, допустимый алгоритм, издателя, срок действия
и тип токена: для запросов нужен `token_type=access`. Простого декодирования JWT
без проверки подписи недостаточно. `aud` по умолчанию не задан — назначение токенов
нужно определить при подключении сервисов.

Выход отзывает refresh, но уже выданный access продолжает действовать до истечения.
После смены пароля старый access отклоняется самим сервисом авторизации;
внешний сервис, проверяющий только подпись и срок, автоматически об этом не узнает.
Изменения ролей также не переписывают уже выданные токены.

JWKS сейчас содержит один публичный ключ. Автоматическая ротация ключей с периодом
совместного действия старого и нового ключей пока не реализована. OAuth2/OIDC
и единый браузерный вход между приложениями также не реализованы.

## Настройки

Основные параметры находятся в `.env`, образец — в [.env.example](.env.example).
Настройки Django разделены на файлы в [config/settings](config/settings).

| Параметр                                                                              | Назначение                                                                   |
| ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `ENVIRONMENT`                                                                         | `local` для разработки; вне local включаются HTTPS redirect и secure cookies |
| `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`                                                | Отладка, секрет Django и разрешённые хосты                                   |
| `DATABASE_ENGINE`                                                                     | `django.db.backends.sqlite3` или `django.db.backends.postgresql`             |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` | Подключение к PostgreSQL                                                     |
| `JWT_SIGNING_KEY`, `JWT_VERIFYING_KEY`                                                | Приватный и публичный PEM-ключи, закодированные в base64                     |
| `JWT_ISSUER`                                                                          | Издатель JWT; по умолчанию `django-template-auth`                            |
| `AXES_FAILURE_TRIES`, `AXES_COOLOFF_MINUTES`                                          | Лимит ошибок входа и срок блокировки                                         |
| `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_ALL_ORIGINS`                                      | Разрешённые источники браузерных запросов                                    |
| `CSRF_TRUSTED_ORIGINS`                                                                | Доверенные источники для CSRF-проверки                                       |

Silk, AXES, Zeal и логирование включаются отдельными переменными `*_ENABLED`.
Полный список есть в `.env.example`.

Для своей пары ключей:

```bash
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
```

Закодируй содержимое каждого PEM-файла в base64 одной строкой и запиши в
соответствующую переменную `JWT_*_KEY`. Приватный ключ и рабочий `.env` нельзя
добавлять в репозиторий или передавать другим сервисам.

Перед развёртыванием задай свои секреты, `DEBUG=false`, реальные хосты и origins,
отключи `CORS_ALLOW_ALL_ORIGINS` и Silk. Для нескольких экземпляров сервиса нужны
общая БД и общий кэш лимитов запросов DRF. Сейчас общий кэш отдельно не настроен.

Если HTTPS завершается на прокси, настрой доверие к нему для определения HTTPS
и клиентского IP. В текущей конфигурации AXES использует `REMOTE_ADDR`;
готовой схемы доверия к `X-Forwarded-For` нет.

## Защита входа

AXES защищает JWT-вход и админку. После **5 неудачных попыток** блокируется пара
**логин + IP** на **15 минут**. Новые запросы во время блокировки не продлевают её.
Успешный вход сбрасывает ошибки только своей пары.

Заблокированный API-вход возвращает `429`:

```json
{ "detail": "Слишком много неудачных попыток входа." }
```

Дополнительно действуют лимиты DRF: 100 запросов в час для анонимного клиента
и 1000 для авторизованного пользователя. Они тоже могут возвращать `429`.

Для ручного снятия блокировки одной пары:

```bash
uv run python manage.py axes_reset_ip_username 192.0.2.1 alice
```

## Обслуживание

Раз в сутки запускай:

```bash
make cleanup-axes
make flush-expired-tokens
```

Первая команда удаляет просроченные попытки AXES и журналы входов/ошибок старше
30 дней. Активные блокировки и попытки без записи срока истечения сохраняются.
Вторая очищает истёкшие записи токенов SimpleJWT.

Срок хранения журналов можно изменить:

```bash
make cleanup-axes AXES_LOG_RETENTION_DAYS=14
```

Он не влияет на длительность блокировки входа. Очистке попыток требуется
`AXES_USE_ATTEMPT_EXPIRATION=True`; при `AXES_ENABLED=false` команда пропускается.

Расписание нужно подключить в окружении развёртывания. Пример cron, где пути
необходимо заменить на свои:

```cron
15 3 * * * cd /srv/auth-service && /home/service/.local/bin/uv run python manage.py cleanup_axes --days 30 >> /var/log/auth-service/maintenance.log 2>&1
20 3 * * * cd /srv/auth-service && /home/service/.local/bin/uv run python manage.py flushexpiredtokens >> /var/log/auth-service/maintenance.log 2>&1
```

Запускай задачи от пользователя сервиса с доступом к той же БД и окружению.
Создай каталог журнала с правом записи и настрой logrotate для вывода cron.
Файловые логи самого приложения ротируются ежедневно, сохраняются 7 архивов.

## Проверки

```bash
uv run pytest            # Все тесты
make check               # Полный набор проверок, как в CI
make check-deploy        # Проверка Django с production-настройками
```

`make check` также запускает форматирование и Ruff с автоисправлениями, поэтому
может изменить файлы. `make check-deploy` проверяет настройки с временным секретом;
успешный результат не заменяет настройку реальных ключей и инфраструктуры.

## Структура проекта

- `apps/users` — модель пользователя, регистрация, профиль и смена пароля.
- `apps/authentication` — JWT, JWKS, вход, обновление, выход и команда очистки AXES.
- `config/settings` — настройки Django и подключённых библиотек.
- `common` — общие компоненты проекта.
- `conftest.py` — фикстуры тестов, включая изоляцию кэша между тестами.


## Связанный сервис задач

[Django-tasks-service](https://github.com/9ZonDG6/Django-tasks-service) — отдельный
пример потребителя JWT. Он хранит задачи в своей БД и проверяет access-токены
через `/.well-known/jwks.json`. Пароли, приватный ключ и доступ к БД пользователей ему не нужны.

Локально этот сервис работает на порту 8000, сервис задач — на 8001. Получи токены
через `/api/v1/auth/login/` и передавай access в `Authorization: Bearer ...` при запросах
к `http://localhost:8001/api/v1/tasks/`. Каждый пользователь видит только свои задачи.
Инструкция запуска находится в README сервиса задач.

Проверку назначения токена можно включить согласованно: здесь задать
`JWT_AUDIENCE=tasks-service`, там — `AUTH_JWT_AUDIENCE=tasks-service`, перезапустить
оба приложения и получить новую пару токенов. По умолчанию audience пуст для
совместимости с уже выданными токенами. Это общий audience для выдаваемых токенов,
а не механизм выбора отдельной аудитории при каждом входе.


## Общие соглашения сервисов

API обоих проектов использует префикс `/api/v1/` и завершающий `/`.
Публичные ключи auth доступны по `/.well-known/jwks.json` независимо от версии API.
Документация auth находится на `/api/docs/`, `/api/redoc/` и `/api/schema/`,
админка — на `/admin/`. Старые адреса `/auth/`, `/users/`, `/backend/` и
`/api/tasks/` заменены; клиенты должны перейти на новые пути.

Приложения находятся в `apps/`, настройки разделены по назначению в
`config/settings/`. Тесты приложения лежат рядом с ним, межсервисные тесты —
в `tests/` репозитория задач. Отдельная таблица пользователей в tasks не создаётся.

Полная проверка взаимодействия запускается из проекта задач:

```bash
AUTH_SERVICE_DIR=/path/to/Django-auth-service uv run pytest tests/test_e2e.py -q
```

Тест запускает оба приложения по HTTP на свободных локальных портах, с отдельными
временными SQLite-базами и новой парой RSA-ключей. Проверяет регистрацию, вход,
получение JWKS, доступ к своим задачам, запрет доступа к чужим, обновление и отзыв
refresh. Рабочие базы и ключи не используются. У обоих проектов должны быть
установлены зависимости в `.venv`.

В GitHub Actions обоих репозиториев это отдельное задание `HTTP integration`.
Для согласованных изменений используется одноимённая ветка второго проекта,
если она существует; иначе берётся его основная ветка. Это проверка совместимости
двух текущих версий, а не фиксация версии зависимости для production.
