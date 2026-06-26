# Мониторинг NZT Backend с Grafana Loki

Этот каталог содержит конфигурацию для стека мониторинга на основе Grafana Loki, Grafana и Grafana Alloy.

## Архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   NZT Backend   │───▶│  Grafana Alloy  │───▶│     Loki        │
│  (логи в файл)  │    │  (сбор логов)   │    │  (хранение)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │    Grafana      │
                                               │ (визуализация)  │
                                               └─────────────────┘
```

## Компоненты

1. **Loki** - агрегатор логов, хранит и индексирует логи
2. **Grafana** - веб-интерфейс для визуализации и поиска логов
3. **Grafana Alloy** - агент, который читает логи из файлов и отправляет в Loki

## Быстрый старт

### 1. Запуск стека мониторинга

```bash
# Запуск всех сервисов мониторинга
docker compose -f docker-compose.monitoring.yml up -d

# Проверка статуса
docker compose -f docker-compose.monitoring.yml ps
```

### 2. Запуск основного приложения

Убедитесь, что ваше приложение пишет логи в папку `logs/` (настроено в `.env`):

```bash
# Запуск основного приложения
docker compose -f docker-compose.dev.yml up -d
```

### 3. Доступ к Grafana

- URL: http://localhost:3000
- Логин: `admin`
- Пароль: `admin`

После входа в Grafana:
1. Перейдите в раздел "Dashboards" → "NZT Backend - Логи приложения"
2. Дашборд автоматически подключится к Loki и начнет отображать логи

## Конфигурация

### Loki (`monitoring/loki/loki-config.yml`)

- Порт: 3100
- Хранение: файловая система (для продакшена используйте S3/GCS)
- Ретеншен: 30 дней

### Alloy (`monitoring/alloy/config.alloy`)

- Читает логи из `/app/logs/*.log`
- Парсит JSON формат
- Извлекает метки: `level`, `method`, `path`, `request_id`, `user_id`, `error_type`
- Отправляет в Loki с метками: `service=nzt-backend`, `environment=development`

### Grafana

- Порт: 3000
- Автоматически настроенный datasource Loki
- Предустановленный дашборд для мониторинга логов

## Логи приложения

Приложение настроено на запись JSON логов в файл (см. `src/core/logging_config.py`):

```json
{
  "level": "info",
  "event": "request_completed",
  "timestamp": "2026-06-25T20:30:00Z",
  "service": "nzt-backend",
  "environment": "development",
  "method": "POST",
  "path": "/api/v1/chat/send",
  "status_code": 200,
  "duration_ms": 125.5,
  "request_id": "abc-123-def",
  "user_id": "user-456"
}
```

## Поиск логов в Grafana

Примеры запросов LogQL:

```logql
# Все логи приложения
{service="nzt-backend"}

# Только ошибки
{service="nzt-backend"} | json | level="error"

# Логи конкретного запроса
{service="nzt-backend"} | json | request_id="abc-123-def"

# Логи конкретного пользователя
{service="nzt-backend"} | json | user_id="user-456"

# Медленные запросы (> 1 секунды)
{service="nzt-backend"} | json | duration_ms > 1000
```

## Остановка

```bash
# Остановка стека мониторинга
docker compose -f docker-compose.monitoring.yml down

# Остановка с удалением данных
docker compose -f docker-compose.monitoring.yml down -v
```

## Для продакшена

1. **Хранение Loki**: настройте использование S3/GCS вместо файловой системы
2. **Безопасность**: включите аутентификацию в Loki и Grafana
3. **Alloy**: настройте сбор логов с нескольких инстансов
4. **Ретеншен**: настройте политику хранения логов
5. **Алертинг**: настройте оповещения о критических ошибках

## Полезные ссылки

- [Документация Loki](https://grafana.com/docs/loki/latest/)
- [Документация Alloy](https://grafana.com/docs/alloy/latest/)
- [LogQL справка](https://grafana.com/docs/loki/latest/logql/)