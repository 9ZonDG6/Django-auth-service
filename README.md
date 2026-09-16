[![CI](https://github.com/9ZonDG6/Django-template/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/9ZonDG6/Django-template/actions/workflows/ci.yml)

### Очистка записей AXES

Запускать раз в сутки:

```bash
make cleanup-axes
# Другой срок хранения журналов:
make cleanup-axes AXES_LOG_RETENTION_DAYS=14
```

Команда удаляет попытки с истёкшим `expiration.expires_at` и записи
`AccessLog` / `AccessFailureLog` старше 30 дней. Активные блокировки и попытки
без записи срока истечения сохраняются. Требуется
`AXES_USE_ATTEMPT_EXPIRATION=True`; при `AXES_ENABLED=false` команда ничего не делает.
Срок хранения журналов не влияет на 15-минутную блокировку входа.

Пример cron для запуска в 03:15 ежедневно (заменить пути на пути развёртывания):

```cron
15 3 * * * cd /srv/auth-service && /home/service/.local/bin/uv run python manage.py cleanup_axes --days 30 >> /var/log/auth-service/axes-cleanup.log 2>&1
```

Задание нужно установить в планировщик окружения развёртывания; репозиторий
сам его не устанавливает. Запускать от пользователя сервиса с доступом к той же
БД и окружению. Каталог журнала должен существовать и быть доступен для записи;
для файла вывода cron следует настроить logrotate.
