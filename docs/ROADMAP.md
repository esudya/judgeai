# Цифровой судья — архитектурный план (v2, 27.10.2026)

Продукт: «второе мнение» на **проект приговора** судьи (конкурс ВС «Алгоритм правосудия. Второе мнение»).
Фокус: рецидив — ст. 15, 18, 68 УК (+ 62, 63, 73, 86, 58). Система решений не принимает (п. 2.5.3 Положения).
Дедлайн I этапа — 01.11.2026 (рабочий сайт). Финал — март 2027.

## 1. Решения (зафиксированы с пользователем 27.10)

| Вопрос | Решение |
|---|---|
| Раскладка | Монорепо `judgeai`: `apps/web`, `services/api`, `services/parser`, `packages/legal_core` |
| Архитектура | Clean Architecture: domain → application (use cases) → adapters (интерфейсы, контроллеры, репозитории) → infrastructure (ORM, HTTP, LLM SDK, парсеры файлов). Бизнес-логика не знает про FastAPI/SQLAlchemy/LLM |
| Тесты | TDD (red → green → refactor). Порог покрытия **80%** (`pytest --cov-fail-under=80`) на каждый Python-пакет |
| Авторизация | Логин + пароль (argon2), сессионный токен. Без внешних провайдеров. Каждый use case принимает `UserContext`; доступ к чужому делу → `AccessDenied` (тест обязателен) |
| Тенантность | База практики (precedents) — общая, только чтение. Дела пользователя (проекты приговоров, отчёты) — строго по `owner_id` |
| LLM | Любой OpenAI-совместимый провайдер за `LlmGateway`. Промпты — только в infrastructure. Перед отправкой — обезличивание в application (`Anonymizer`) |
| Асинхронность | Статусы задач `pending/processing/completed/failed` в домене; очередь за интерфейсом `TaskQueue` (сейчас in-process BackgroundTasks, позже — брокер) |
| Деплой | Только локально. Публичный деплой — только после явного «да» пользователя |
| Приватные образцы | 9 неотбезличенных приговоров лежат в `ПРАВО/judgeai-private/samples/` — **вне репозитория**. Никогда не коммитить, не пушить, не цитировать ФИО в логах/тестах. Для тестов — синтетические фикстуры, сделанные по их структуре |

## 2. Монорепо

```
judgeai/
  packages/legal_core/          # Domain + доменные сервисы. 0 внешних зависимостей
    legal_core/
      entities/                 # Conviction, CriminalRecord, Sanction, Punishment, DraftVerdict, ...
      rules/                    # одна норма = один модуль: art15_category.py, art18_recidivism.py, art68.py, art62.py, art63.py, art73.py, art86.py, art58.py
      checks.py                 # CheckResult(status: ok|possible_violation|insufficient_data, norm, explanation, quote)
    tests/
  services/parser/              # Сбор и нормализация практики
    parser/
      domain/                   # RawDecision, PrecedentCard, SourceId
      application/              # CrawlSource, NormalizeDecision, Deduplicate
      adapters/                 # SourceCrawler (Protocol), DecisionRepository (Protocol)
      infrastructure/           # sudact.py, sudrf.py, http_client (rate limit, robots), storage (fs + Postgres)
    tests/
  services/api/                 # Текущий FastAPI-бэкенд, переносится сюда из корня
    src/
      domain/  application/  adapters/  infrastructure/
    tests/
  apps/web/                     # Текущий фронт (verdikt-web)
  docs/  ROADMAP.md  TASKS.md  AUTORUN.md  data-sources.md
```

`services/api` и `services/parser` импортируют `legal_core` как локальный пакет (`pip install -e packages/legal_core`).

## 3. База дел (precedents)

### 3.1 Источники — см. `docs/data-sources.md` (задача T1)
Кандидаты: sudact.ru, сайты районных судов `*.sudrf.ru` (модуль «Судебное делопроизводство», каждый суд отдельно), bsr.sudrf.ru (ГАС «Правосудие»), mos-gorsud.ru, Санкт-Петербургские суды, открытые датасеты судебных решений, статистика Судебного департамента (агрегаты). Цель — как можно больше уголовных приговоров. Перед парсингом каждого источника: robots.txt + условия использования, скорость ≤ 1 запрос / 2 с.

### 3.2 Схема хранения (новые таблицы, отдельная миграция; существующие таблицы не трогаем)

```
source_document
  id PK, source TEXT, source_url TEXT UNIQUE, uid TEXT NULL (УИД дела — ключ дедупликации между источниками),
  court TEXT, region_code TEXT, case_number TEXT, decision_date DATE NULL,
  fetched_at TIMESTAMPTZ, raw_path TEXT, sha256 TEXT UNIQUE, parse_status TEXT
precedent_case
  id PK, source_document_id FK UNIQUE,
  articles TEXT[]            -- нормализовано: '158.2.в', '228.2'
  main_article TEXT, category TEXT (small|medium|grave|especially_grave),
  recidivism TEXT (none|simple|dangerous|especially_dangerous|unknown),
  prior_convictions INT, minor_children BOOL NULL,
  mitigating TEXT[], aggravating TEXT[],       -- коды: '61.1.г', '63.1.а'
  applied_general TEXT[],                     -- '62.1', '64', '68.2', '68.3', '73'
  punishment_type TEXT, term_months INT NULL, conditional BOOL, regime TEXT NULL,
  fabula TEXT, embedding VECTOR(N), extracted_by TEXT, extraction_version INT
INDEX GIN(articles), BTREE(main_article, recidivism), BTREE(punishment_type)
```
Миграционный план: новая ревизия `0003_precedents` только CREATE TABLE/INDEX, downgrade = DROP этих таблиц. Данные пользователей не затрагиваются.

### 3.3 Критерии сортировки/отбора похожих
1. Жёсткие фильтры: та же статья + часть (+ пункт), тот же вид рецидива.
2. Мягкие: категория, наличие ч.1 ст.62 / ст.64 / ч.3 ст.68, наличие малолетних детей, число прежних судимостей, регион, год.
3. Ранжирование: косинус эмбеддинга фабулы + взвешенная дистанция признаков. Top-k = 10.
4. Статистика (медиана, квартили срока, доля условных) считается **в коде** по отобранному множеству, не LLM.

## 4. Приём проекта приговора
`DocumentParser` (Protocol) → infrastructure: `.docx` (python-docx), `.pdf` (pdfplumber), `.txt`.
Валидация (mime, размер, zip-bomb для docx) — в adapters до создания доменных сущностей.
`VerdictSegmenter` (domain service): вводная часть / «УСТАНОВИЛ» (описательно-мотивировочная) / «ПРИГОВОРИЛ» (резолютивная). Нормализация заголовков вразрядку («П Р И Г О В О Р», «У С Т А Н О В И Л»).
Извлечение фактов: regex-слой (статьи, сроки, даты, УИД) + LLM-слой (личность, смягчающие/отягчающие, судимости) с pydantic-валидацией и цитатой на каждый факт.

## 5. Сравнение с LLM
`CompareWithPractice` (use case): DraftFacts + top-k PrecedentCard + результаты rules → `LlmGateway.compare_cases(source, similar) -> ComparisonNarrative`.
В LLM уходят **структурированные карточки**, не полные тексты; ФИО/адреса/даты рождения вырезаны `Anonymizer`.
Промпт (infrastructure/llm/prompts/compare_v1.md): роль — помощник, не судья; вход — карточки; выход — JSON {annotation, deviations[], deeper_analysis[]}; каждая претензия — со ссылкой на норму или номер карточки; запрет придумывать нормы.

## 6. Что уже есть (main после MR !1)
FastAPI + Postgres/pgvector + Alembic 0001–0002, 202+polling, fake LLM, ч.1 ст.62 в коде, 29 тестов. Известный дефект: модель эмбеддингов `alekseevpavel04/multilingual-e5-small-ru-law` не поддерживается fastembed → тихий откат на keyword (исправить в T8).
