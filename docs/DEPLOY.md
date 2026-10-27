# Правила развёртывания на сервере

Статус: **черновик, не проверен на живом сервере.** Деплой — только после явного согласия владельца проекта. Автозапуски Claude не деплоят никогда.

## 1. Сервер

| Параметр | Требование | Почему |
|---|---|---|
| Расположение | Дата-центр в РФ | 152-ФЗ: проекты приговоров содержат персональные данные; отечественная инфраструктура — плюс по Положению |
| ОС | Ubuntu 24.04 LTS | Долгая поддержка, официальные пакеты Docker |
| Ресурсы (демо) | 4 vCPU, 8 ГБ RAM, 80 ГБ SSD | Эмбеддинги считаются на CPU; сырые HTML практики занимают место. Оценка, проверить нагрузкой |
| Домен | Отдельный поддомен, A-запись на сервер | Нужен для TLS |

## 2. Состав `compose.prod.yml`

| Сервис | Образ | Порты наружу | Данные |
|---|---|---|---|
| `proxy` | caddy (автоматический TLS) | 80, 443 | volume `caddy_data` (сертификаты) |
| `web` | статика `apps/web` (сборка без моков) | нет | — |
| `api` | `services/api` | нет (только через proxy) | volume `uploads` |
| `migrate` | тот же образ, что api, команда `alembic upgrade head` | нет | — |
| `parser` | `services/parser`, запуск по расписанию | нет | volume `raw_decisions` |
| `db` | `pgvector/pgvector:pg16` | **нет** | volume `pgdata` |
| `backup` | контейнер с `pg_dump` по расписанию | нет | volume/каталог `backups` |

Референс (не запускался; теги образов фиксировать при первой сборке):

```yaml
services:
  proxy:
    image: caddy:2
    ports: ["80:80", "443:443"]
    volumes: ["./deploy/Caddyfile:/etc/caddy/Caddyfile:ro", "caddy_data:/data"]
    depends_on: [api, web]
    restart: unless-stopped
  web:
    image: registry.gitlab.com/judgeai/judgeai/web:${RELEASE}
    restart: unless-stopped
  migrate:
    image: registry.gitlab.com/judgeai/judgeai/api:${RELEASE}
    command: ["alembic", "upgrade", "head"]
    env_file: .env
    depends_on: { db: { condition: service_healthy } }
    restart: "no"
  api:
    image: registry.gitlab.com/judgeai/judgeai/api:${RELEASE}
    env_file: .env
    volumes: ["uploads:/app/uploads"]
    depends_on:
      db: { condition: service_healthy }
      migrate: { condition: service_completed_successfully }
    healthcheck: { test: ["CMD", "curl", "-fsS", "http://localhost:8000/health"], interval: 30s, retries: 3 }
    restart: unless-stopped
  parser:
    image: registry.gitlab.com/judgeai/judgeai/parser:${RELEASE}
    env_file: .env
    volumes: ["raw_decisions:/data/raw"]
    depends_on: { db: { condition: service_healthy } }
    restart: unless-stopped
  db:
    image: pgvector/pgvector:pg16
    env_file: .env.db
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck: { test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER}"], interval: 10s, retries: 5 }
    restart: unless-stopped
volumes: { caddy_data: {}, uploads: {}, raw_decisions: {}, pgdata: {} }
```

## 3. Правила

### Секреты
- `.env` и `.env.db` живут только на сервере, `chmod 600`, владелец — пользователь деплоя. В git — только `.env.example` без значений.
- Ключ LLM, пароль БД, секрет сессий — разные для dev и prod. Никогда не печатать их в логи и чаты.
- Ключи реестра и SSH для CI — в GitLab CI/CD Variables (masked + protected).

### Сеть и доступ
- Наружу открыты только 22, 80, 443 (`ufw`). БД и api снаружи недоступны. Docker обходит ufw для опубликованных портов — поэтому у db/api нет `ports:` вообще.
- SSH только по ключам, root-вход запрещён, fail2ban включён.
- Контейнеры api/parser работают не от root (`USER app` в Dockerfile).
- Демо для жюри: доступ по логину/паролю (T10); открытая регистрация выключена.

### Данные
- На сервер **не загружаются** приватные образцы из `judgeai-private/`. Для демо — только опубликованные обезличенные тексты.
- База практики наполняется парсером на самом сервере или импортом дампа с Mac (`pg_dump -t source_document -t precedent_case -t criminal_article_sanction`).
- Бэкап: `pg_dump -Fc` ежедневно в 03:30 МСК, хранить 7 дневных + 4 недельных, копия вне сервера (S3-совместимое хранилище в РФ). Восстановление проверять раз в неделю на чистой БД.

### Релиз
1. Релиз = git-тег `vX.Y.Z` на main при зелёном CI (тесты, ruff, покрытие ≥ 80%, сборка фронта). CI собирает образы с тегом релиза; `latest` не используется.
2. Перед деплоем — свежий бэкап БД.
3. `RELEASE=vX.Y.Z docker compose -f compose.prod.yml pull && RELEASE=vX.Y.Z docker compose -f compose.prod.yml up -d` — migrate отрабатывает до старта api.
4. Проверка: `/health`, вход, загрузка тестового проекта, результат анализа.
5. Откат: предыдущий `RELEASE`. Миграции обратно совместимы (сначала добавить, потом удалять в следующем релизе) — тогда `alembic downgrade` не нужен. Downgrade — только по плану и после бэкапа.

### Эксплуатация
- Логи: драйвер `json-file` с `max-size: 10m`, `max-file: 5`. В логах нет текстов приговоров и ФИО — только id дел и статусы.
- Мониторинг: внешний пинг `/health` раз в минуту; алерт при 2 неудачах подряд.
- Обновления ОС: `unattended-upgrades` только security.

## 4. Чего ещё нет в коде (нужно до первого деплоя)
- [ ] Эндпоинт `GET /health` в api (с проверкой соединения с БД).
- [ ] Prod-Dockerfile для api/parser (без dev-зависимостей, `USER app`), для web — multi-stage сборка статики.
- [ ] `deploy/Caddyfile`: `/api/*` → api:8000, остальное → web, SPA-fallback на index.html.
- [ ] `.env.example` со списком переменных без значений.
- [ ] `.gitlab-ci.yml`: test → build images → push to registry (деплой — ручная кнопка `when: manual`).
- [ ] Скрипт бэкапа и проверки восстановления.

## 5. Открытые вопросы
- Какой провайдер VPS и кто платит?
- Домен для демо.
- LLM в prod: внешний API (GigaChat / YandexGPT) или локальная модель — локальная требует GPU и меняет требования к серверу.
