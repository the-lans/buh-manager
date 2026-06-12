# 📒 buh-manager — Персональный бухгалтер

Полноценное full-stack приложение для учёта личных финансов: импорт банковских выписок, хранение чеков, автоматическая сверка расходов и аналитика.

---

## 🗂 Содержание

- [Обзор](#обзор)
- [Стек технологий](#стек-технологий)
- [Структура проекта](#структура-проекта)
- [Запуск на локальном компьютере](#запуск-на-локальном-компьютере)
- [Запуск на production-сервере](#запуск-на-production-сервере)
- [Конфигурация](#конфигурация)
- [API](#api)
- [Тестирование](#тестирование)
- [Линтеры и типизация](#линтеры-и-типизация)
- [CI](#ci)
- [Основные концепции](#основные-концепции)
- [Алгоритм сопоставления чеков](#алгоритм-сопоставления-чеков)
- [Расчёт и проверка балансов](#расчёт-и-проверка-балансов)

---

## Обзор

**buh-manager** решает задачу «у меня куча выписок из банков и куча чеков — как понять, куда ушли деньги».

Что умеет система:

- 📥 **Импорт выписок** из Сбербанка, Т-Банка и Яндекс Банка (PDF через AI-агента)
- 🧾 **Хранение чеков** с позициями, фискальными данными (ФН/ФД/ФПД) и дедупликацией
- 🔄 **Автоматическая сверка** — алгоритм сопоставляет транзакции из выписки с чеками по времени, сумме и контрагенту (RapidFuzz)
- ⚖️ **Проверка балансовой цепочки** — контроль корректности остатков в выписке
- 🔐 **Авторизация через Google** — без паролей, JWT на 7 дней
- 📊 **Дашборд** с KPI-карточками, таблицей остатков на счетах и разбивкой расходов по типам за выбранный месяц

---

## Стек технологий

### Backend
| Компонент | Технология |
|-----------|-----------|
| Web-фреймворк | FastAPI |
| ORM / модели | SQLModel (SQLAlchemy 2.0 + Pydantic v2) |
| Миграции | Alembic |
| БД (dev) | SQLite |
| БД (prod) | PostgreSQL |
| Авторизация | Google OAuth2 + JWT (python-jose) |
| Fuzzy-поиск | RapidFuzz |
| Хранилище файлов | LocalStorage / Яндекс Object Storage (boto3) |
| Конфигурация | pydantic-settings |

### Frontend
| Компонент | Технология |
|-----------|-----------|
| UI-фреймворк | React 19 + Vite |
| Язык | TypeScript |
| Стили | Tailwind CSS v4 (кастомные компоненты) |
| Маршрутизация | React Router v7 |
| Серверное состояние | TanStack Query |
| HTTP-клиент | Axios |
| Формы | React Hook Form + Zod |

---

## Структура проекта

```
buh-manager/
├── .github/workflows/ci.yml      # GitHub Actions CI
├── backend/
│   ├── app/
│   │   ├── main.py               # Сборка FastAPI приложения
│   │   ├── config.py             # Настройки через pydantic-settings
│   │   ├── constants.py          # Enum-классы и числовые константы
│   │   ├── database.py           # SQLite/PostgreSQL engine + get_session
│   │   ├── models/               # SQLModel table-models (14 таблиц)
│   │   ├── schemas/              # Pydantic request/response схемы
│   │   ├── db/                   # Слой доступа к данным
│   │   ├── services/             # Бизнес-логика (импорт, сверка, баланс)
│   │   ├── routers/              # FastAPI роутеры
│   │   └── dependencies/         # auth.py — get_current_user
│   ├── storage/                  # StorageProvider Protocol + реализации
│   ├── alembic/                  # Миграции БД
│   ├── tests/
│   │   ├── unit/                 # Unit-тесты (дедупликация, алгоритмы)
│   │   └── integration/          # Integration-тесты (HTTP + реальная БД)
│   ├── .dockerignore
│   ├── .env.example
│   ├── Dockerfile                # Многостадийная сборка: test / prod
│   └── pyproject.toml
├── deploy/buh-manager.service    # systemd-юнит для автозапуска
├── frontend/
│   ├── nginx.conf                # Nginx: статика + proxy /api/, /docs
│   └── src/
│       ├── api/                  # Axios-клиенты для каждого ресурса
│       ├── hooks/                # TanStack Query хуки
│       ├── pages/                # Login, Dashboard, Transactions, Receipts...
│       ├── components/layout/    # AppShell, навигация
│       └── types/                # TypeScript интерфейсы
└── docker-compose.yml
```

---

## Запуск на локальном компьютере

### Требования

- Python 3.12+
- Node.js 20+
- Google OAuth2 credentials (создаются в [Google Cloud Console](https://console.cloud.google.com/))

### 1. Клонировать репозиторий

```bash
git clone https://github.com/the-lans/buh-manager.git
cd buh-manager
```

### 2. Настроить и запустить backend

```bash
cd backend

# Вариант A — через uv (рекомендуется)
uv sync --all-extras               # создаёт .venv и устанавливает все зависимости
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Вариант B — через pip
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Скопировать и заполнить переменные окружения
cp .env.example .env
# Отредактируйте .env: заполните GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY, JWT_SECRET_KEY

# Создать таблицы БД (SQLite, файл buh.db)
alembic upgrade head

# Запустить сервер с авторелоадом
uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

### 3. Настроить и запустить frontend

```bash
cd frontend

# Установить зависимости
npm install

# Запустить dev-сервер (Vite проксирует /api → localhost:8000)
npm run dev
```

Приложение: http://localhost:5173

> 💡 Все запросы `/api/*` автоматически проксируются на backend — CORS не нужен для локальной разработки.

### 4. Настроить Google OAuth2 для локалки

В [Google Cloud Console](https://console.cloud.google.com/):
- Authorized redirect URIs: `http://localhost:8000/api/v1/auth/google/callback`
- Authorized JavaScript origins: `http://localhost:5173`

---

## Запуск на production-сервере

### Вариант A — без Docker (прямой деплой)

#### Backend

```bash
cd backend

# Установить зависимости (без dev)
pip install -e "."

# Создать .env с prod-настройками (см. раздел Конфигурация)
# DATABASE_URL=postgresql://user:pass@localhost:5432/buhmanager
# ENVIRONMENT=production

# Применить миграции к PostgreSQL
alembic upgrade head

# Запустить через Gunicorn + Uvicorn worker
# Актуальная команда — в prod-стадии backend/Dockerfile
pip install gunicorn psycopg2-binary
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 --forwarded-allow-ips='*' --access-logfile - --error-logfile -
```

#### Frontend — сборка статики

```bash
cd frontend

# Создать .env.production с адресом API
echo "VITE_API_URL=https://api.your-domain.com" > .env.production

npm install
npm run build
# Статические файлы будут в frontend/dist/
```

Раздавайте `frontend/dist/` через Nginx или любой CDN.

#### Пример конфига Nginx

За актуальным примером обращайтесь к [`frontend/nginx.conf`](frontend/nginx.conf) — там уже настроены проксирование `/api/`, `/docs`, `/redoc`, `/openapi.json` и корректная передача `X-Forwarded-Proto`.

### Вариант B — Docker Compose

Все необходимые файлы (`docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`) уже находятся в репозитории. PostgreSQL должен быть запущен на сервере заранее.

**1. Клонируйте репозиторий на сервер:**

```bash
git clone https://github.com/the-lans/buh-manager.git /opt/buh-manager
cd /opt/buh-manager
```

**2. Подготовьте `.env` для backend:**

```bash
cp backend/.env.example backend/.env
```

Заполните переменные согласно [разделу Конфигурация](#конфигурация) и чеклисту ниже.

**3. Соберите образы и запустите:**

```bash
docker compose up -d --build
```

**4. Настройте автозапуск при старте сервера:**

```bash
# Убедитесь, что Docker запускается вместе с системой
sudo systemctl enable docker

# Установите systemd-юнит для приложения
sudo cp deploy/buh-manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable buh-manager
```

**Полезные команды:**

```bash
# Статус сервисов
sudo systemctl status buh-manager

# Логи всех контейнеров
docker compose -f /opt/buh-manager/docker-compose.yml logs -f

# Обновить приложение (пересобрать образы)
cd /opt/buh-manager && git pull && docker compose up -d --build

# Остановить
sudo systemctl stop buh-manager
```

### Чеклист перед деплоем в prod

- [ ] `ENVIRONMENT=production` в `.env`
- [ ] `DATABASE_URL` указывает на внешний PostgreSQL
- [ ] `SECRET_KEY` и `JWT_SECRET_KEY` — случайные строки ≥ 32 символа
- [ ] `FRONTEND_URL` — реальный домен фронтенда (для CORS)
- [ ] Google OAuth redirect URI обновлён на prod-домен
- [ ] Для Яндекс S3: заполнены `YANDEX_S3_BUCKET`, `YANDEX_ACCESS_KEY`, `YANDEX_SECRET_KEY` (см. [инструкцию ниже](#где-взять-ключи-яндекс-object-storage))
- [ ] HTTPS настроен (Let's Encrypt / Certbot)

---

## Конфигурация

Скопируйте [`backend/.env.example`](backend/.env.example) в `backend/.env` и заполните значения. Файл содержит комментарии для каждой переменной.

Ключевые переменные:

| Переменная | Описание |
|------------|----------|
| `ENVIRONMENT` | `local` или `production` |
| `SECRET_KEY` | Секрет для сессий (≥ 32 символа) |
| `DATABASE_URL` | SQLite (dev) или PostgreSQL (prod) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Credentials Google OAuth2 |
| `JWT_SECRET_KEY` | Секрет подписи JWT (≥ 32 символа) |
| `FRONTEND_URL` | Домен фронтенда (для CORS и OAuth redirect) |
| `ALLOWED_EMAILS` | Белый список email через запятую; если не задан — пускаются все |
| `YANDEX_S3_BUCKET` / `YANDEX_ACCESS_KEY` / `YANDEX_SECRET_KEY` | Яндекс Object Storage (только prod) |

### Где взять ключи Яндекс Object Storage

Яндекс Object Storage совместим с S3 API. Ключи привязаны к сервисному аккаунту в Яндекс Облаке.

**Шаг 1 — Создать бакет**

1. Откройте [console.yandex.cloud](https://console.yandex.cloud/) → **Object Storage** → **Создать бакет**.
2. Задайте имя (например `buh-manager-files`), выберите регион и уровень доступа **Приватный**.
3. Имя бакета → `YANDEX_S3_BUCKET`.

**Шаг 2 — Создать сервисный аккаунт**

1. В боковом меню → **IAM** → **Сервисные аккаунты** → **Создать сервисный аккаунт**.
2. Имя: например `buh-manager-s3`.
3. Назначьте роль **storage.editor** (или `storage.uploader` если нужны только загрузки).

**Шаг 3 — Создать статический ключ доступа**

1. Перейдите в только что созданный сервисный аккаунт → вкладка **Ключи доступа** → **Создать статический ключ**.
2. Сохраните оба значения — **идентификатор ключа** и **секретный ключ** (секрет показывается один раз):
   - Идентификатор ключа → `YANDEX_ACCESS_KEY`
   - Секретный ключ → `YANDEX_SECRET_KEY`

> ⚠️ При `ENVIRONMENT=local` файлы сохраняются локально в `backend/media/` и Yandex S3 не используется. Ключи нужны только для `ENVIRONMENT=production`.

---

## API

Все эндпоинты доступны с префиксом `/api/v1`. Защищённые маршруты требуют заголовок `Authorization: Bearer <token>`.

Интерактивная документация: **`/docs`** (Swagger UI) · **`/redoc`** (ReDoc)

### 🔐 Auth

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/auth/google` | Редирект на страницу входа Google OAuth2 |
| `GET` | `/auth/google/callback` | Callback после авторизации — создаёт/обновляет пользователя, возвращает JWT |
| `GET` | `/auth/me` | Профиль текущего пользователя |

### 📄 Документы

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/documents` | Загрузить документ (PDF/изображение); дедупликация по SHA-256; `?doc_type=RECEIPT\|BANK_STATEMENT` |
| `GET` | `/documents` | Список документов; фильтры по типу/статусу, пагинация; новые сверху |
| `GET` | `/documents/{id}` | Получить документ по ID |
| `PUT` | `/documents/{id}` | Обновить поля документа (например, `payload`) |
| `GET` | `/documents/{id}/download` | Скачать / открыть документ (`?inline=true` для просмотра в браузере, возвращает presigned URL или локальный файл) |
| `POST` | `/documents/{id}/link-receipt` | Привязать PENDING-документ типа `RECEIPT` к существующему чеку; статус → `PROCESSED` |
| `POST` | `/documents/{id}/link-statement` | Привязать PENDING-документ типа `BANK_STATEMENT` к транзакциям/остаткам по счёту в диапазоне дат; статус → `PROCESSED` или `ERROR` |
| `POST` | `/documents/{id}/reset` | Сбросить документ из статуса `ERROR` обратно в `PENDING` для повторной обработки |

### 🧾 Чеки

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/receipts` | Создать чек с позициями; дедупликация по фискальным данным ФН+ФД+ФПД |
| `GET` | `/receipts` | Список чеков текущего пользователя; сортировка по дате (новые сверху); пагинация; фильтры: `?document_id=`, `?unmatched=true` (только не привязанные к транзакции), `?max_age_days=N` (не старше N дней); ответ включает поле `transaction_id` |
| `GET` | `/receipts/{id}` | Получить чек по ID |
| `PUT` | `/receipts/{id}` | Обновить чек и его позиции |
| `DELETE` | `/receipts/{id}` | Удалить чек (нельзя удалить, если привязан к транзакции) |

### 🏦 Банковские выписки

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/bank-statements` | Импортировать выписку (привязывается к документу); возвращает отчёт: добавлено / дубликаты / конфликты |

### 💳 Транзакции

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/transactions` | Список транзакций; фильтры по счёту, дате, типу, статусу сверки (`reconciled_status`), статусу импорта (`import_status`); ответ включает `receipt_id`, `document_id`, `expense_type_id` |
| `POST` | `/transactions` | Создать транзакцию вручную |
| `PUT` | `/transactions/{id}` | Обновить транзакцию; поддерживает поле `receipt_id` для ручной привязки/отвязки чека (изменяет `reconciled_status` соответственно); изменение фиксируется в audit_log |
| `DELETE` | `/transactions/{id}` | Удалить транзакцию |

### 🔄 Сверка

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/reconciliation/run` | Запустить автоматическую сверку транзакций с чеками |
| `GET` | `/reconciliation/report` | Последний сохранённый отчёт о сверке |
| `POST` | `/reconciliation/match` | Вручную связать транзакцию с чеком |
| `POST` | `/reconciliation/ignore` | Пометить транзакцию как `IGNORED_BY_USER` (чек не нужен) |
| `POST` | `/reconciliation/resolve-conflict` | Разрешить незакрытый конфликт импорта: `KEEP_OLD` или `UPDATE_FROM_NEW` |

### 📋 Журнал аудита

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/audit-log` | Список записей аудита (создание/обновление/удаление сущностей); фильтр по `?entity_type=` |

### 🔑 API-ключи

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api-keys` | Список API-ключей текущего пользователя |
| `POST` | `/api-keys` | Создать новый API-ключ с набором разрешений (`scopes`) |
| `PATCH` | `/api-keys/{id}` | Обновить API-ключ (имя, scopes, активность) |
| `DELETE` | `/api-keys/{id}` | Отозвать API-ключ |

### ⚙️ Пользовательские настройки

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/app-constants` | Получить поддерживаемые настройки с текущими или дефолтными значениями; для API-ключа нужен scope `read:app_constants` |
| `PUT` | `/app-constants/{key}` | Обновить настройку; поддерживаются только известные ключи, значение валидируется по типу и диапазону; для API-ключа нужен scope `write:app_constants` |

### ⚙️ Справочники

| Метод | Путь | Описание |
|-------|------|----------|
| `GET/POST` | `/accounts` | Список / создать банковский счёт; поддерживает `zero_balance` — базовый остаток до первой записи в `balances` |
| `PUT/DELETE` | `/accounts/{id}` | Обновить / удалить счёт, включая `zero_balance` |
| `POST` | `/accounts/{id}/initialize-balance` | Установить начальный баланс вручную (для банков без остатков в выписке) |
| `GET` | `/balances` | История подтверждённых остатков по счетам; фильтр по `?account_id=`; новые сверху |
| `GET/POST` | `/expense-types` | Список / создать тип расходов; поддерживает необязательное поле `description` |
| `PUT/DELETE` | `/expense-types/{id}` | Обновить (в т.ч. `description`) / удалить тип расходов |
| `GET/POST` | `/counterparties` | Список / создать контрагента; поддерживает произвольное поле `payload` (JSON) |
| `PUT/DELETE` | `/counterparties/{id}` | Обновить (в т.ч. `payload`) / удалить контрагента (нельзя удалить, если привязан к чекам или транзакциям — 409) |
| `POST` | `/exchange-rates` | Добавить курс валюты |
| `GET` | `/exchange-rates/latest` | Последние курсы по каждой валютной паре |

---

## Тестирование

```bash
cd backend

# Запустить все тесты
uv run pytest          # если используется uv
# или
pytest tests/ -v

# С измерением покрытия
pytest tests/ --cov=app --cov-report=term-missing
```

### Результаты покрытия

| Категория | Покрытие |
|-----------|---------|
| `app/` в целом | **94%** |
| `app/services/` | 92% |
| `app/routers/` | 94% |
| `app/db/` | 97% |

> Непокрытые строки — это исключительно OAuth-callback (требует реального Google) и Yandex S3 (требует реальных credentials).

### Типы тестов

- **Unit** (`tests/unit/`): дедупликация файлов, балансовая цепочка, алгоритм импорта, скоринг сверки, аудит-сервис
- **Integration** (`tests/integration/`): полный HTTP-цикл через `httpx.AsyncClient` + in-memory SQLite с `StaticPool`

---

## Линтеры и типизация

```bash
cd backend

# Ruff (lint + format)
ruff check app/ tests/ storage/
ruff format app/ tests/ storage/

# mypy (строгая типизация)
mypy app/ --ignore-missing-imports
```

```bash
cd frontend

# TypeScript
npx tsc --noEmit

# ESLint
npx eslint src/ --ext .ts,.tsx
```

Все проверки проходят без ошибок ✅

---

## CI

GitHub Actions запускается автоматически на каждый push и pull request в `main` (`.github/workflows/ci.yml`):

1. Устанавливает зависимости через `uv sync --all-extras`
2. Запускает полный тест-сьют: `uv run pytest`

Зависимости устанавливаются из `pyproject.toml` при каждой сборке — если транзитивный пакет пропадёт, CI упадёт до попадания в прод.

---

## Основные концепции

### 📄 Жизненный цикл документов

Документ при загрузке получает статус `PENDING`. Затем его нужно обработать — привязать к данным в базе:

**Документ типа `RECEIPT`** → `POST /documents/{id}/link-receipt`
- Выбирается существующий чек без документа
- Устанавливается `receipt.document_id = document.id`
- Статус документа → `PROCESSED`

**Документ типа `BANK_STATEMENT`** → `POST /documents/{id}/link-statement`
- Указывается счёт и диапазон дат
- Все транзакции и остатки без `document_id` в этом диапазоне получают привязку
- Если найдены записи → статус `PROCESSED`; если нет → `ERROR`

Документ в статусе `PROCESSED` или `ERROR` нельзя обработать повторно (409).

### 📊 Остатки по счетам

Остатки создаются автоматически при импорте банковской выписки (`OPENING` и `CLOSING`) или вручную через `/accounts/{id}/initialize-balance`. Доступны через `GET /balances` с фильтром по счёту. Используются для верификации цепочки транзакций.

У счёта есть поле `zero_balance`: базовый остаток до первой записи в `balances`. При ручном расчёте через `/balances/calculate`, если у счёта ещё нет записей остатков, сервис берёт `zero_balance` как стартовую точку и суммирует поверх неё транзакции счёта.

### ⚙️ Пользовательские настройки

Настройки сверки хранятся отдельно для каждого пользователя и доступны через `/app-constants`. Сейчас поддерживаются:

| Ключ | Тип | Описание |
|-----|-----|----------|
| `RECONCILE_AUTO_MATCH_MAX_HOURS` | положительное целое число | Максимальный временной зазор в часах для автоматического матча |
| `RECONCILE_AMOUNT_TOLERANCE` | неотрицательное число | Допустимое отклонение суммы при сопоставлении транзакции и чека |

API-ключи должны иметь scope `read:app_constants` для чтения настроек и `write:app_constants` для изменения.

### 🔑 Дедупликация чеков

Фискальные данные (ФН + ФД + ФПД) используются как уникальный ключ. Если все три поля `NULL` — дедупликация не срабатывает (чеки без QR-кода).

### 🔁 Дедупликация транзакций

- Если `balance_after` заполнен (Сбербанк): ключ `(account_id, occurred_at ± 60с, balance_after)`
- Если `balance_after = NULL` (Т-Банк, Яндекс Банк): fallback-ключ `(account_id, occurred_at ± 60с, amount)`

### 🏗 Изоляция данных

Каждый запрос к БД ограничивает выборку владельцем:

- **Транзакции, документы, счета** — через `JOIN accounts WHERE accounts.user_id = ?`
- **Чеки** — через поле `receipts.user_id` (прямая привязка к пользователю); если чек создан через документ — дополнительно через `documents.user_id`
- **POST /transactions** — перед созданием проверяется, что `account_id` принадлежит текущему пользователю (иначе 403)

Доступ к данным другого пользователя — security bug.

### 🗄 Токен авторизации

Хранится в `sessionStorage` — теряется при закрытии вкладки. Это поведение по ТЗ.

---

## 🔄 Алгоритм сопоставления чеков

Запускается вручную через `POST /api/v1/reconciliation/run`. Результат сохраняется в БД и доступен через `GET /api/v1/reconciliation/report`.

### Шаг 1 — Сбор данных

Система берёт:
- все транзакции со статусом `UNMATCHED`, у которых тип расходов требует чек (`expense_type.receipt_required = true`) или тип расходов не задан;
- все чеки, ещё не привязанные ни к одной транзакции.

### Шаг 2 — Группировка по сумме (корзины)

Транзакции и чеки раскладываются в «корзины» по абсолютному значению суммы: `abs(amount)` и `abs(total_amount)`. Сопоставление возможно только внутри одной корзины — чек на 500 ₽ никогда не будет сопоставлен с транзакцией на 501 ₽.

```
Корзина 500 ₽: [tx1, tx2]  ←→  [receipt_A]        → коллизия (N:M)
Корзина 1200 ₽: [tx3]      ←→  [receipt_B]        → оценка пары
Корзина 300 ₽: [tx4]       ←→  []                 → нет чека
Корзина 800 ₽: []          ←→  [receipt_C]        → чек без транзакции
```

### Шаг 3 — Разбор каждой корзины

| Ситуация | Результат |
|----------|-----------|
| Транзакции есть, чеков нет | Транзакции → `missing_receipts` |
| Чеки есть, транзакций нет | Чеки → `unmatched_receipts` |
| N транзакций + M чеков (N > 1 или M > 1) | **Коллизия** — ручной разбор |
| 1 транзакция + 1 чек | Оценка пары (см. ниже) |

### Шаг 4 — Временно́е окно

Прежде чем оценивать пару 1:1, система проверяет, попадает ли транзакция в допустимый временной диапазон относительно чека:

```
paid_at − 12 часов  ≤  occurred_at  ≤  paid_at + 3 дня
```

Если транзакция вне окна — оба объекта попадают в соответствующие «без пары» списки.

### Шаг 5 — Скоринг пары

Каждая прошедшая временно́е окно пара получает балл (0–100):

| Критерий | Условие | Баллы |
|----------|---------|-------|
| ⏱ Разница во времени | < 1 часа | +40 |
| ⏱ Разница во времени | < 12 часов | +25 |
| ⏱ Разница во времени | < 3 дней | +10 |
| 🏷 Fuzzy-схожесть контрагентов | > 80 % (RapidFuzz `token_set_ratio`) | +40 |
| 🏷 Fuzzy-схожесть контрагентов | > 50 % | +20 |
| 🎯 Единственная пара в корзине | — | +20 |

**Порог автоматического матча: 75 баллов.**

- Балл ≥ 75 → транзакция получает `reconciled_status = MATCHED`, к ней прикрепляется чек (`receipt_id`), в аудит-логе фиксируется `action = MATCH, changed_by = AGENT`.
- Балл < 75 → оба объекта остаются несопоставленными.

> **Пример:** транзакция произошла через 30 минут после оплаты чека (+40), контрагенты совпадают на 85% (+40), единственная пара в корзине (+20) → итого **100 баллов** → автоматический матч.

### Ручные операции после сверки

| Действие | Способ | Описание |
|----------|--------|----------|
| Вручную сопоставить (из UI сверки) | `POST /reconciliation/match` | Принудительно связать транзакцию с чеком; после матча автоматически перезапускается сверка |
| Вручную сопоставить (из редактора транзакции) | `PUT /transactions/{id}` с `receipt_id` | Прикрепить или открепить чек прямо из формы редактирования транзакции |
| Игнорировать | `POST /reconciliation/ignore` | Пометить транзакцию как `IGNORED_BY_USER` (чек не нужен); после игнора автоматически перезапускается сверка |
| Разрешить конфликт импорта | `POST /reconciliation/resolve-conflict` | `KEEP_OLD` — оставить как есть; `UPDATE_FROM_NEW` — применить входящие данные конфликтной выписки, сохранённые на сервере |

---

## ⚖️ Расчёт и проверка балансов

### Откуда берётся начальный баланс

При **первом** импорте выписки для счёта (нет ни одной записи в таблице `balances`) система автоматически создаёт входящий баланс из поля `opening_balance` выписки. Это называется «начальная инициализация».

Если баланс в выписке отсутствует (Т-Банк), инициализировать его можно вручную через `POST /accounts/{id}/initialize-balance` или задать `accounts.zero_balance` как базовый остаток для последующего ручного расчёта `/balances/calculate`.

### Балансовая цепочка

После импорта транзакций сервис `verify_balance_chain` проверяет математическую согласованность остатков:

```
Входящий остаток
       │
       ▼
  ┌─────────┐   + amount₁   ┌─────────┐   + amount₂   ┌─────────┐
  │ opening │ ────────────► │  tx₁   │ ────────────► │  tx₂   │  ...
  │ balance │               │ bal_aft │               │ bal_aft │
  └─────────┘               └─────────┘               └─────────┘
                                  │                         │
                           balance_mismatch?         balance_mismatch?
                           (bank ≠ calculated)
```

Для каждой транзакции вычисляется `calculated_balance_after = running_balance + amount`. Если банк указал другой `balance_after` — выставляется флаг `balance_mismatch = true`.

В конце сравниваются `closing_balance_calculated` (сумма по цепочке) и `closing_balance_statement` (остаток из выписки). Расхождение фиксируется в поле `discrepancy`.

### Когда расчёт недоступен

| Банк | `balance_after` в транзакции | Статус цепочки |
|------|------------------------------|----------------|
| Сбербанк | ✅ есть | `is_available = true`, полный расчёт |
| Яндекс Банк | ❌ нет | `is_available = false`, цепочка пропускается |
| Т-Банк | ❌ нет | `is_available = false`, цепочка пропускается |

Отсутствие расчёта — **не ошибка**: выписки Т-Банка и Яндекс Банка просто не содержат остатка после каждой операции. Транзакции всё равно импортируются корректно.
