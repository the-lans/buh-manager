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
- 📊 **Дашборд** с KPI, графиками расходов по категориям и балансом во времени

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
| Стили | Tailwind CSS v4 |
| Маршрутизация | React Router v7 |
| Серверное состояние | TanStack Query |
| HTTP-клиент | Axios |
| Компоненты | shadcn/ui |
| Графики | Recharts |

---

## Структура проекта

```
buh-manager/
├── backend/
│   ├── app/
│   │   ├── main.py               # Сборка FastAPI приложения
│   │   ├── config.py             # Настройки через pydantic-settings
│   │   ├── constants.py          # Enum-классы и числовые константы
│   │   ├── database.py           # SQLite/PostgreSQL engine + get_session
│   │   ├── models/               # SQLModel table-models (11 таблиц)
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
│   ├── .env.example
│   └── pyproject.toml
└── frontend/
    └── src/
        ├── api/                  # Axios-клиенты для каждого ресурса
        ├── hooks/                # TanStack Query хуки
        ├── pages/                # Login, Dashboard, Transactions, Receipts...
        ├── components/layout/    # AppShell, навигация
        └── types/                # TypeScript интерфейсы
```

---

## Запуск на локальном компьютере

### Требования

- Python 3.12+
- Node.js 20+
- Google OAuth2 credentials (создаются в [Google Cloud Console](https://console.cloud.google.com/))

### 1. Клонировать репозиторий

```bash
git clone https://github.com/your-org/buh-manager.git
cd buh-manager
```

### 2. Настроить и запустить backend

```bash
cd backend

# Создать виртуальное окружение и установить зависимости
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
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
pip install gunicorn
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
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

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend (статика)
    root /var/www/buh-manager/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Вариант B — Docker Compose

> Создайте `docker-compose.yml` в корне репозитория:

```yaml
version: "3.9"

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: buhmanager
      POSTGRES_USER: buh
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    env_file: ./backend/.env
    environment:
      DATABASE_URL: postgresql://buh:${DB_PASSWORD}@db:5432/buhmanager
    depends_on:
      - db
    ports:
      - "8000:8000"
    command: >
      sh -c "alembic upgrade head &&
             gunicorn app.main:app
             --workers 4
             --worker-class uvicorn.workers.UvicornWorker
             --bind 0.0.0.0:8000"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"

volumes:
  postgres_data:
```

```bash
# Запустить всё одной командой
docker compose up -d
```

#### Dockerfile для backend

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e "."
COPY . .
```

#### Dockerfile для frontend

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

### Чеклист перед деплоем в prod

- [ ] `ENVIRONMENT=production` в `.env`
- [ ] `DATABASE_URL` указывает на PostgreSQL
- [ ] `SECRET_KEY` и `JWT_SECRET_KEY` — случайные строки ≥ 32 символа
- [ ] `FRONTEND_URL` — реальный домен фронтенда (для CORS)
- [ ] Google OAuth redirect URI обновлён на prod-домен
- [ ] Для Яндекс S3: заполнены `YANDEX_S3_BUCKET`, `YANDEX_ACCESS_KEY`, `YANDEX_SECRET_KEY`
- [ ] HTTPS настроен (Let's Encrypt / Certbot)

---

## Конфигурация

Скопируйте `backend/.env.example` в `backend/.env` и заполните значения:

```dotenv
# Режим запуска: local / production
ENVIRONMENT=local

# Секретный ключ для сессий
SECRET_KEY=your-secret-key-here

# SQLite (dev) или PostgreSQL (prod)
DATABASE_URL=sqlite:///./buh.db

# Google OAuth2
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# JWT
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080

# URL фронтенда (для CORS и OAuth redirect)
FRONTEND_URL=http://localhost:5173

# Яндекс Object Storage (только для prod)
YANDEX_S3_BUCKET=
YANDEX_ACCESS_KEY=
YANDEX_SECRET_KEY=
```

---

## API

Все эндпоинты доступны с префиксом `/api/v1`. Защищённые маршруты требуют заголовок `Authorization: Bearer <token>`.

| Группа | Эндпоинты |
|--------|-----------|
| 🔐 Auth | `GET /auth/google`, `GET /auth/google/callback`, `GET /auth/me` |
| 📄 Документы | `POST /documents`, `GET /documents`, `GET /documents/{id}` |
| 🧾 Чеки | CRUD `/receipts`, `/receipts/{id}` |
| 🏦 Выписки | `POST /bank-statements` |
| 💳 Транзакции | CRUD `/transactions`, фильтрация по дате/типу/статусу |
| 🔄 Сверка | `POST /reconciliation/run`, `GET /reconciliation/report`, `/match`, `/ignore`, `/resolve-conflict` |
| ⚙️ Справочники | CRUD счетов, типов расходов, контрагентов, курсов валют |

---

## Тестирование

```bash
cd backend

# Запустить все тесты
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

## Основные концепции

### 🔑 Дедупликация чеков

Фискальные данные (ФН + ФД + ФПД) используются как уникальный ключ. Если все три поля `NULL` — дедупликация не срабатывает (чеки без QR-кода).

### 🔁 Дедупликация транзакций

- Если `balance_after` заполнен (Сбербанк): ключ `(account_id, occurred_at ± 60с, balance_after)`
- Если `balance_after = NULL` (Т-Банк, Яндекс Банк): fallback-ключ `(account_id, occurred_at ± 60с, amount)`

### 🏗 Изоляция данных

Каждый запрос к БД соединяет таблицы через `accounts.user_id`. Доступ к чужим данным — security bug.

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

| Действие | Эндпоинт | Описание |
|----------|----------|----------|
| Вручную сопоставить | `POST /reconciliation/match` | Принудительно связать транзакцию с чеком |
| Игнорировать | `POST /reconciliation/ignore` | Пометить транзакцию как `IGNORED_BY_USER` (чек не нужен) |
| Разрешить коллизию | `POST /reconciliation/resolve-conflict` | `KEEP_OLD` — оставить как есть; `UPDATE_FROM_NEW` — пересчитать |

---

## ⚖️ Расчёт и проверка балансов

### Откуда берётся начальный баланс

При **первом** импорте выписки для счёта (нет ни одной записи в таблице `balances`) система автоматически создаёт входящий баланс из поля `opening_balance` выписки. Это называется «начальная инициализация».

Если баланс в выписке отсутствует (Т-Банк), инициализировать его можно вручную через `POST /accounts/{id}/initialize-balance`.

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
