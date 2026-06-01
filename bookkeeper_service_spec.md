# ТЗ: Сервис «Персональный бухгалтер»

> Техническое задание для Claude Code
> Версия: 1.2
> Дата: 2026-05-03 (обновлено)

---

## 1. Обзор системы

Сервис «Персональный бухгалтер» — это backend-платформа с REST API (FastAPI) и React-фронтендом для хранения, обработки и анализа персональных финансовых данных.

**Главные задачи системы:**
- Предоставить API для AI-агента, который загружает чеки (со скриншотов и из почты) и банковские выписки.
- Хранить финансовые данные в структурированном виде (транзакции, чеки, остатки, документы).
- При загрузке выписок: автоматически определять дубликаты и конфликты (перекрывающиеся периоды выписок).
- Автоматически сверять банковские транзакции с загруженными чеками.
- Предоставить веб-интерфейс для ручного управления данными и ручного запуска сверки.

---

## 2. Технический стек

### Бэкенд
- **Python 3.12+**
- **FastAPI** — основной фреймворк
- **SQLModel** — ORM (над SQLAlchemy 2.0 + Pydantic v2)
- **Alembic** — миграции БД
- **SQLite** — локальная разработка
- **PostgreSQL** — продакшн
- **pydantic-settings** — управление конфигурацией через `.env`
- **boto3** — загрузка файлов в S3-совместимое хранилище
- **RapidFuzz** — нечёткое сравнение строк для алгоритма сверки чеков
- **uvicorn** — ASGI-сервер

### Фронтенд
- **React 19 + Vite**
- **TypeScript**
- **React Router** — навигация
- **TanStack Query** (React Query) — управление состоянием и запросами к API
- **Tailwind CSS** — стили
- **shadcn/ui** — UI-компоненты
- **Recharts** — графики и дашборд
- **React Hook Form + Zod** — формы и валидация

### Хранение файлов
- **Локально:** файлы сохраняются в папке `media/` в корне проекта, раздаются через FastAPI `StaticFiles`.
- **Продакшн:** файлы хранятся в **Yandex Object Storage** (S3-совместимый API).
- Реализовать через **паттерн Strategy (StorageProvider Protocol)**, чтобы подмена провайдера происходила через `.env` без изменения кода.

---

## 3. Архитектура хранилища файлов

### Интерфейс (Protocol)
```python
class StorageProvider(Protocol):
    async def upload_file(self, file: UploadFile, file_id: str) -> str:
        """Сохраняет файл и возвращает URL"""
        ...
```

### Реализации
- `LocalStorageProvider` — сохраняет в `media/{file_id}.{ext}`, возвращает `/media/{file_id}.{ext}`.
- `YandexS3Provider` — загружает через boto3 в Yandex Object Storage, возвращает `https://{bucket}.storage.yandexcloud.net/{filename}`.

### Конфигурация (`.env`)
```
ENVIRONMENT=local          # или prod
YANDEX_S3_BUCKET=
YANDEX_ACCESS_KEY=
YANDEX_SECRET_KEY=
```

---

## 4. Схема базы данных

> Все модели описываются через SQLModel (table=True).
> UUID генерируется на стороне Python (`default_factory=uuid4`).
> Поля `created_at` / `updated_at` проставляются автоматически.

### 4.1 users
| Поле | Тип | Описание |
|---|---|---|
| `id` | UUID (PK) | Уникальный ID пользователя |
| `email` | VARCHAR | Логин пользователя |
| `password_hash` | VARCHAR | Хэш пароля |
| `created_at` | TIMESTAMP | Дата регистрации |

### 4.2 accounts
| Поле | Тип | Описание |
|---|---|---|
| `id` | UUID (PK) | Уникальный ID счёта |
| `user_id` | UUID (FK → users.id) | Владелец счёта |
| `bank` | VARCHAR | Название банка |
| `account_number` | VARCHAR | Номер счёта или карты |
| `currency` | VARCHAR | Валюта (ISO 4217: RUB, USD, EUR) |
| `is_active` | BOOLEAN | Активен ли счёт (default: true) |

### 4.3 documents
| Поле | Тип | Описание |
|---|---|---|
| `id` | UUID (PK) | Уникальный ID документа |
| `user_id` | UUID (FK → users.id) | Владелец документа |
| `type` | VARCHAR | Тип: RECEIPT, BANK_STATEMENT |
| `url` | VARCHAR | URL файла (локальный путь или S3) |
| `name` | VARCHAR | Исходное имя файла |
| `status` | VARCHAR | PENDING, PROCESSED, ERROR |
| `email_source` | VARCHAR (NULL) | Email отправителя (если из почты) |
| `file_hash` | VARCHAR | SHA-256 файла (для дедупликации) |
| `raw_parsed_data` | TEXT (NULL) | Сырой JSON-ответ от агента (для отладки) |
| `uploaded_at` | TIMESTAMP | Дата загрузки |

> **Дедупликация:** UNIQUE INDEX на `file_hash`.

### 4.4 counterparties
| Поле | Тип | Описание |
|---|---|---|
| `id` | VARCHAR (PK) | Slug, сгенерированный из названия |
| `name` | VARCHAR | Название магазина/компании/ФИО |
| `type` | VARCHAR | STORE, PERSON, COMPANY |
| `inn` | VARCHAR(12) (NULL) | ИНН — 10 цифр (юрлицо) или 12 цифр (ИП) |
| `kpp` | VARCHAR(9) (NULL) | КПП — 9 цифр (только для юрлиц) |

> **Дедупликация:** при создании контрагента с заполненным ИНН сначала ищется существующий по `inn`; если не найден — по `name`. Это предотвращает дубли при разном написании названия одной компании.

### 4.5 expense_types
| Поле | Тип | Описание |
|---|---|---|
| `id` | VARCHAR (PK) | Slug категории (например, `grocery`) |
| `name` | VARCHAR | Человекочитаемое название |
| `receipt_required` | BOOLEAN | Обязателен ли чек для сверки |

### 4.6 receipts
| Поле | Тип | Описание |
|---|---|---|
| `id` | UUID (PK) | Уникальный ID чека |
| `document_id` | UUID (FK → documents.id) | Исходный скан/фото чека |
| `paid_at` | TIMESTAMP | Дата и время оплаты |
| `total_amount` | NUMERIC | Итоговая сумма чека |
| `counterparty_id` | VARCHAR (FK → counterparties.id, NULL) | Магазин |
| `fn` | VARCHAR (NULL) | Фискальный накопитель (ФН) |
| `fd` | VARCHAR (NULL) | Фискальный документ (ФД) |
| `fpd` | VARCHAR (NULL) | Фискальный признак документа (ФПД) |

> **Дедупликация:** UNIQUE INDEX на `(fn, fd, fpd)` (применяется только если все три поля заполнены).

### 4.7 receipt_items
| Поле | Тип | Описание |
|---|---|---|
| `id` | UUID (PK) | Уникальный ID позиции |
| `receipt_id` | UUID (FK → receipts.id) | Привязка к чеку |
| `code` | VARCHAR (NULL) | Артикул / штрихкод товара |
| `name` | VARCHAR | Наименование товара |
| `unit` | VARCHAR (NULL) | Единица измерения (шт., кг, л) |
| `quantity` | NUMERIC | Количество |
| `price` | NUMERIC | Цена за единицу |
| `amount` | NUMERIC | Итоговая сумма по позиции (`quantity × price`) |
| `tags` | TEXT (NULL) | JSON-массив тегов (например, `["FOOD", "dairy"]`) |

### 4.8 transactions
| Поле | Тип | Описание |
|---|---|---|
| `id` | UUID (PK) | Уникальный ID транзакции |
| `account_id` | UUID (FK → accounts.id) | Счёт |
| `occurred_at` | TIMESTAMP | Дата и время операции (МСК) |
| `processed_at` | TIMESTAMP (NULL) | Дата обработки банком (дата клиринга) |
| `auth_code` | VARCHAR (NULL) | Код авторизации из выписки |
| `amount` | NUMERIC | Сумма (отрицательная = расход) |
| `type` | VARCHAR | INCOME, EXPENSE, TRANSFER |
| `bank_category` | VARCHAR (NULL) | Категория из классификатора банка (текст) |
| `counterparty_id` | VARCHAR (FK → counterparties.id, NULL) | Контрагент |
| `expense_type_id` | VARCHAR (FK → expense_types.id, NULL) | Внутренняя категория траты |
| `description` | TEXT (NULL) | Назначение платежа |
| `balance_after` | NUMERIC (NULL) | Остаток средств после операции (из выписки) |
| `calculated_balance_after` | NUMERIC (NULL) | Расчётный остаток по формуле (заполняется при импорте) |
| `balance_mismatch` | BOOLEAN | true, если `balance_after ≠ calculated_balance_after` |
| `receipt_id` | UUID (FK → receipts.id, NULL) | Привязанный чек |
| `reconciled_status` | VARCHAR | UNMATCHED, MATCHED, NOT_REQUIRED, IGNORED_BY_USER |
| `import_status` | VARCHAR | IMPORTED, DUPLICATE_SKIPPED, CONFLICT |
| `document_id` | UUID (FK → documents.id, NULL) | Выписка, из которой загружена транзакция |

> **Дедупликация:** UNIQUE INDEX на `(account_id, occurred_at, balance_after)`.
> Ключ дедупликации — `(occurred_at + balance_after)`, а не `(occurred_at + amount)`, т.к. `balance_after` уникален в цепочке операций даже при одинаковых суммах.

### 4.9 balances
| Поле | Тип | Описание |
|---|---|---|
| `id` | UUID (PK) | Уникальный ID записи |
| `account_id` | UUID (FK → accounts.id) | Счёт |
| `amount` | NUMERIC | Зафиксированный остаток из шапки выписки |
| `recorded_at` | TIMESTAMP | Дата фиксации (начало или конец периода выписки) |
| `source` | VARCHAR | OPENING (начало) или CLOSING (конец периода) |
| `document_id` | UUID (FK → documents.id, NULL) | Источник (выписка) |

### 4.10 exchange_rates
| Поле | Тип | Описание |
|---|---|---|
| `id` | UUID (PK) | Уникальный ID |
| `base_currency` | VARCHAR | Базовая валюта (USD) |
| `quote_currency` | VARCHAR | Котируемая валюта (RUB) |
| `rate` | NUMERIC | Курс обмена |
| `recorded_at` | TIMESTAMP | Дата фиксации курса |

### 4.11 audit_log
| Поле | Тип | Описание |
|---|---|---|
| `id` | UUID (PK) | Уникальный ID записи |
| `entity_type` | VARCHAR | Тип сущности: "transaction", "receipt", "match", "import" |
| `entity_id` | UUID | ID изменённой записи |
| `action` | VARCHAR | CREATE, UPDATE, DELETE, MATCH, UNMATCH, IMPORT_CONFLICT |
| `changed_by` | VARCHAR | AGENT или USER |
| `changed_at` | TIMESTAMP | Метка времени |
| `diff` | TEXT | JSON-снапшот: `{"before": {...}, "after": {...}}` |

---

## 5. API Эндпоинты

Все эндпоинты имеют префикс `/api/v1`.

### 5.1 Документы
| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/documents` | Загрузить файл документа. Дедупликация по `file_hash` — при совпадении возвращает `409 Conflict` с `document_id` существующего документа. |
| `GET` | `/documents` | Список документов с пагинацией, фильтр по `type`, `status`. |
| `GET` | `/documents/{id}` | Детали документа. |

### 5.2 Чеки
| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/receipts` | Агент передаёт распознанный чек. Бэкенд создаёт запись в `receipts`, позиции в `receipt_items`, находит или создаёт контрагента. Обновляет статус документа на PROCESSED. |
| `GET` | `/receipts` | Список чеков с пагинацией, фильтр по дате и магазину. |
| `GET` | `/receipts/{id}` | Детали чека с позициями. |
| `PUT` | `/receipts/{id}` | Ручное редактирование чека. |
| `DELETE` | `/receipts/{id}` | Удаление чека. |

#### Схема запроса `POST /receipts`
```json
{
  "document_id": "uuid",
  "counterparty_name": "Пятёрочка",
  "paid_at": "2026-05-01T10:30:00Z",
  "total_amount": 1250.50,
  "fn": "9999078900016350",
  "fd": "88923",
  "fpd": "1234567890",
  "items": [
    {
      "code": "4607034732117",
      "name": "Молоко Простоквашино 3.2% 1л",
      "unit": "шт.",
      "quantity": 2,
      "price": 89.90,
      "amount": 179.80,
      "tags": ["FOOD", "dairy"]
    }
  ]
}
```

### 5.3 Банковские выписки
| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/bank-statements` | Агент передаёт транзакции и остатки из выписки. Запускает алгоритм импорта (раздел 6). Возвращает полный `ImportReport`. |

#### Схема запроса `POST /bank-statements`
```json
{
  "document_id": "uuid",
  "account_id": "uuid",
  "statement_start": "2026-03-27T00:00:00Z",
  "statement_end": "2026-04-02T23:59:59Z",
  "opening_balance": 427110.40,
  "closing_balance": 433429.40,
  "transactions": [
    {
      "occurred_at": "2026-04-02T12:09:00Z",
      "processed_at": "2026-04-02T00:00:00Z",
      "auth_code": "945422",
      "amount": -499.00,
      "type": "EXPENSE",
      "bank_category": "Прочие расходы",
      "counterparty_name": "TIMEWEB.CLOUD",
      "description": "SANKT-PETERBU TIMEWEB.CLOUD. Операция по карте ****7514",
      "balance_after": 433429.40
    }
  ]
}
```

#### Схема ответа `POST /bank-statements` — `ImportReport`
```json
{
  "document_id": "uuid",
  "account_id": "uuid",
  "period": {"start": "2026-03-27", "end": "2026-04-02"},
  "summary": {
    "imported_count": 3,
    "duplicate_count": 1,
    "conflict_count": 0
  },
  "balance_check": {
    "opening_balance_statement": 427110.40,
    "closing_balance_statement": 433429.40,
    "closing_balance_calculated": 433429.40,
    "is_consistent": true,
    "discrepancy": 0.00
  },
  "conflicts": [],
  "imported_transaction_ids": ["uuid1", "uuid2", "uuid3"]
}
```

### 5.4 Транзакции
| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/transactions` | Список. Фильтры: `account_id`, `start_date`, `end_date`, `type`, `reconciled_status`, `import_status`. |
| `POST` | `/transactions` | Ручное добавление транзакции. |
| `PUT` | `/transactions/{id}` | Редактирование. |
| `DELETE` | `/transactions/{id}` | Удаление. |

### 5.5 Сверка (Reconciliation)
| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/reconciliation/run` | Запуск сверки чеков с транзакциями по кнопке. Возвращает отчёт. |
| `GET` | `/reconciliation/report` | Последний отчёт без перезапуска. |
| `POST` | `/reconciliation/match` | Ручная привязка: `{"transaction_id": "uuid", "receipt_id": "uuid"}`. |
| `POST` | `/reconciliation/ignore` | Пометить транзакцию как `IGNORED_BY_USER`: `{"transaction_id": "uuid"}`. |
| `POST` | `/reconciliation/resolve-conflict` | Разрешить конфликт импорта: `{"transaction_id": "uuid", "action": "KEEP_OLD" или "UPDATE_FROM_NEW"}`. |

#### Схема ответа `POST /reconciliation/run`
```json
{
  "report_generated_at": "2026-05-03T01:00:00Z",
  "summary": {
    "auto_matched_count": 12,
    "missing_receipts_count": 5,
    "unmatched_receipts_count": 2,
    "collisions_count": 1
  },
  "collisions": [
    {
      "collision_id": "collision-group-id",
      "amount": 150.00,
      "reason": "MULTIPLE_MATCHES",
      "message": "Найдено 2 транзакции и 2 чека на одинаковую сумму. Требуется ручное сопоставление.",
      "involved_transactions": [
        {"id": "uuid", "occurred_at": "...", "counterparty_name": "..."}
      ],
      "involved_receipts": [
        {"id": "uuid", "paid_at": "...", "store_name": "..."}
      ]
    }
  ],
  "missing_receipts": [
    {"transaction_id": "uuid", "occurred_at": "...", "amount": -500.00,
     "counterparty_name": "...", "expense_type": "grocery"}
  ],
  "unmatched_receipts": [
    {"receipt_id": "uuid", "paid_at": "...", "total_amount": 300.00, "store_name": "..."}
  ]
}
```

### 5.6 Справочники
| Метод | Путь | Описание |
|---|---|---|
| `GET/POST/PUT/DELETE` | `/accounts` | CRUD для счетов |
| `GET/POST/PUT/DELETE` | `/expense-types` | CRUD для типов трат |
| `GET/POST` | `/counterparties` | Список / создать контрагента (с дедупликацией по ИНН) |
| `PUT/DELETE` | `/counterparties/{id}` | Обновить / удалить контрагента |
| `POST` | `/exchange-rates` | Добавление курса валют |
| `GET` | `/exchange-rates/latest` | Последние курсы всех валют |

### 5.7 Журнал изменений
| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/audit-log` | Список записей аудита. Query-параметры: `entity_type` (фильтр), `skip`, `limit` (пагинация, default limit=50). Сортировка по убыванию даты. |

---

## 6. Алгоритм импорта банковской выписки

### Контекст

Выписки от одного банка могут пересекаться по датам (например, первая — с 27.03 по 02.04, вторая — с 01.04 по 07.04). Алгоритм обеспечивает идемпотентность: повторная загрузка одной выписки или загрузка пересекающихся выписок не создаёт дубликатов и фиксирует конфликты данных.

### Ключ дедупликации

Связка `(account_id, occurred_at ± 1 минута, balance_after)` является «отпечатком» транзакции.

**Почему `balance_after`, а не `amount`?**
Если два платежа имеют одинаковую сумму в один день, остаток счёта после каждого из них будет разным — это гарантирует уникальность. `balance_after` — это фактически «хэш состояния счёта» в конкретный момент времени.

### Шаги алгоритма

**Шаг 1: Извлечение метаданных выписки**

Из шапки выписки извлекаются:
- `account_id`, `statement_start`, `statement_end`
- `opening_balance` (остаток на начало периода)
- `closing_balance` (остаток на конец периода)

**Шаг 2: Партиционирование по суммам (Partitioning)**

Транзакции из выписки группируются в корзины по `amount`. Поиск в БД по ключу дедупликации происходит внутри одной корзины.

**Шаг 3: Поиск каждой транзакции в БД**

Для каждой транзакции из выписки выполняется SQL-запрос:

```sql
SELECT id, amount FROM transactions
WHERE account_id = :account_id
  AND occurred_at BETWEEN :occurred_at - INTERVAL '1 minute'
                      AND :occurred_at + INTERVAL '1 minute'
  AND balance_after = :balance_after
LIMIT 1;
```

**Шаг 4: Маркировка каждой транзакции**

По результату поиска транзакция получает статус `import_status`:

| Результат | import_status | Действие |
|---|---|---|
| Не найдена | `IMPORTED` | Создать новую запись в `transactions` |
| Найдена, `amount` совпадает | `DUPLICATE_SKIPPED` | Пропустить, не создавать |
| Найдена, но `amount` отличается | `CONFLICT` | Не обновлять автоматически; записать в `audit_log` с `action=IMPORT_CONFLICT`; вернуть в `conflicts[]` ответа |

**Шаг 5: Проверка целостности цепочки остатков**

После импорта всех транзакций за период выписки вычисляется расчётный остаток:

```
calculated_balance[n] = calculated_balance[n-1] + amount[n]
```

Начальной точкой служит `opening_balance` из шапки выписки.
Для каждой транзакции заполняется поле `calculated_balance_after` и флаг `balance_mismatch = (balance_after ≠ calculated_balance_after)`.

Если `balance_mismatch = true` хотя бы у одной транзакции — в цепочке есть пропущенная операция (например, комиссия банка, обработанная вне периода выписки).

**Шаг 6: Сверка итоговых остатков**

Расчётный закрывающий остаток сравнивается с `closing_balance` из шапки:

```
discrepancy = closing_balance_statement - closing_balance_calculated
is_consistent = (discrepancy == 0)
```

В таблицу `balances` записываются два остатка:
- `OPENING`: `opening_balance` на дату `statement_start`
- `CLOSING`: `closing_balance` на дату `statement_end`

При повторной загрузке той же выписки — `UPSERT` по `(account_id, recorded_at, source)`.

**Шаг 7: Обработка конфликтов**

Конфликты не разрешаются автоматически. Они:
- Записываются в `audit_log` (`action = IMPORT_CONFLICT`)
- Возвращаются в `conflicts[]` поля ответа `ImportReport`
- Доступны для ручного разрешения через `POST /reconciliation/resolve-conflict`

Пользователь выбирает одно из двух действий:
- `KEEP_OLD` — оставить существующую запись без изменений
- `UPDATE_FROM_NEW` — перезаписать данными из новой выписки (с записью в `audit_log`)

### Псевдокод сервиса импорта

```python
def import_bank_statement(statement: BankStatementCreate) -> ImportReport:
    results = {"imported": [], "skipped": [], "conflicts": []}

    for tx in statement.transactions:
        existing = db.find_transaction(
            account_id=statement.account_id,
            occurred_at=tx.occurred_at,     # ±1 минута
            balance_after=tx.balance_after  # точное совпадение
        )

        if not existing:
            db.insert_transaction(tx, import_status="IMPORTED")
            results["imported"].append(tx)
        elif existing.amount == tx.amount:
            results["skipped"].append(tx)   # Дубликат — пропускаем
        else:
            audit_log.write(action="IMPORT_CONFLICT", before=existing, after=tx)
            results["conflicts"].append({"existing": existing, "incoming": tx})

    # Проверяем цепочку остатков
    balance_check = verify_balance_chain(
        account_id=statement.account_id,
        period_start=statement.statement_start,
        period_end=statement.statement_end,
        opening_balance=statement.opening_balance,
        expected_closing=statement.closing_balance
    )

    # Фиксируем остатки из шапки выписки
    db.upsert_balance(account_id, statement.opening_balance,
                      statement.statement_start, source="OPENING")
    db.upsert_balance(account_id, statement.closing_balance,
                      statement.statement_end, source="CLOSING")

    return ImportReport(**results, balance_check=balance_check)
```

---

## 7. Алгоритм сверки чеков с транзакциями (Reconciliation Pipeline)

Запускается при вызове `POST /reconciliation/run`.

### Шаг 1: Выборка кандидатов
- Транзакции: `receipt_id IS NULL` и `expense_types.receipt_required = true`.
- Чеки: не привязаны ни к одной транзакции.

### Шаг 2: Партиционирование по суммам
Кандидаты группируются в корзины по `amount`. Чек и транзакция могут совпасть только внутри одной корзины.

### Шаг 3: Фильтрация по временному окну (Time Window)

Для каждого чека вычисляется окно поиска транзакции с учётом задержки банковского клиринга:

- Если время чека известно: `[paid_at − 12ч ; paid_at + 3 дня]`
- Если известна только дата: `[date 00:00:00 − 12ч ; date 23:59:59 + 3 дня]`

Минус 12 часов — поправка на часовые пояса. Плюс 3 дня — задержка клиринга.

### Шаг 4: Скоринг пар

| Критерий | Баллы |
|---|---|
| Совпадение суммы (обеспечено шагом 2) | Базовое условие |
| Разница во времени < 1 ч | 40 |
| Разница во времени < 12 ч | 25 |
| Разница во времени < 3 дней | 10 |
| Fuzzy-match названий (RapidFuzz token_set_ratio) > 80% | 40 |
| Fuzzy-match названий > 50% | 20 |
| Единственная пара в корзине (1-to-1) | +20 |

### Шаг 5: Разрешение

| Ситуация | Действие |
|---|---|
| 1 транзакция + 1 чек, скор ≥ 75 | Авто-маппинг: `receipt_id`, `reconciled_status = MATCHED` |
| Скор < 75 | `reconciled_status = UNMATCHED` → в `missing_receipts` |
| N транзакций и/или M чеков в одной корзине | Коллизия: в отчёт, ничего не обновляется |
| Тип траты не требует чека | `reconciled_status = NOT_REQUIRED` |

---

## 8. Структура проекта

```
bookkeeper/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py                # pydantic-settings
│   │   ├── database.py              # SQLModel engine, session
│   │   ├── models/                  # SQLModel table-models
│   │   │   ├── user.py
│   │   │   ├── account.py
│   │   │   ├── document.py
│   │   │   ├── receipt.py
│   │   │   ├── transaction.py
│   │   │   ├── balance.py
│   │   │   ├── counterparty.py
│   │   │   ├── expense_type.py
│   │   │   ├── exchange_rate.py
│   │   │   └── audit_log.py
│   │   ├── schemas/                 # Pydantic request/response схемы
│   │   ├── routers/
│   │   │   ├── documents.py
│   │   │   ├── receipts.py
│   │   │   ├── transactions.py
│   │   │   ├── bank_statements.py
│   │   │   ├── reconciliation.py
│   │   │   └── references.py
│   │   └── services/
│   │       ├── import_statement.py  # Алгоритм импорта выписки (раздел 6)
│   │       ├── reconciliation.py    # Алгоритм сверки чеков (раздел 7)
│   │       ├── balance_chain.py     # Проверка цепочки остатков
│   │       ├── deduplication.py     # Проверки уникальности
│   │       └── audit.py             # Запись в audit_log
│   ├── storage/
│   │   ├── base.py                  # StorageProvider Protocol
│   │   ├── local.py                 # LocalStorageProvider
│   │   └── yandex_s3.py             # YandexS3Provider
│   ├── alembic/
│   ├── media/                       # Локальные файлы (gitignore)
│   ├── .env.example
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   ├── Dashboard.tsx
    │   │   ├── Transactions.tsx
    │   │   ├── Receipts.tsx
    │   │   ├── Reconciliation.tsx
    │   │   ├── Accounts.tsx
    │   │   └── Settings.tsx
    │   ├── components/
    │   ├── api/
    │   └── main.tsx
    ├── vite.config.ts
    └── package.json
```

---

## 9. Фронтенд: Страницы и требования

**Дизайн:** современный, читаемый. Нейтральные поверхности, один акцентный цвет, табличные числа (`font-variant-numeric: tabular-nums`). Компоненты из shadcn/ui.

### 9.1 Дашборд (`/`)
- KPI-карточки: расходы за месяц, баланс по всем счетам (с конвертацией через `exchange_rates`), кол-во несверенных транзакций, кол-во конфликтов импорта.
- График расходов по категориям (Recharts, Bar).
- График баланса по времени (Recharts, Line).

### 9.2 Транзакции (`/transactions`)
- Таблица с сортировкой, фильтрами (дата, тип, статус сверки, счёт, статус импорта).
- Визуальная индикация `reconciled_status` и `import_status` (бейджи).
- **Форма ручного ввода** (модальное окно): `occurred_at`, `amount`, `type`, `account`, `counterparty`, `description`, `expense_type`.

### 9.3 Чеки (`/receipts`)
- Таблица чеков с раскрытием позиций.
- **Форма ручного ввода чека**: поля заголовка + динамический список позиций.
- Возможность прикрепить файл-документ.

### 9.4 Сверка (`/reconciliation`)
- Кнопка **«Запустить сверку»** → `POST /reconciliation/run`.
- Сводка: auto_matched, missing, collisions.
- Секция **«Коллизии сверки»**: карточка с двумя колонками — Транзакции и Чеки. Выбор пары → «Подтвердить маппинг».
- Секция **«Конфликты импорта»**: карточка с двумя версиями транзакции (старая vs новая) → кнопки «Оставить старую» / «Обновить».
- Секция **«Транзакции без чеков»**: список с кнопкой «Игнорировать».
- Секция **«Расхождения остатков»**: список транзакций с `balance_mismatch = true`.

### 9.5 Настройки (`/settings`)
- CRUD для типов трат с тогглом `receipt_required`.
- CRUD для счетов.

---

## 10. Дедупликация и защита данных

| Объект | Ключ дедупликации | Реакция на дубликат |
|---|---|---|
| Документ (файл) | `file_hash` (SHA-256) | `409 Conflict` + `document_id` существующего |
| Транзакция | `(account_id, occurred_at ± 1 мин, balance_after)` | `import_status = DUPLICATE_SKIPPED` |
| Транзакция (конфликт) | То же, но `amount` отличается | `import_status = CONFLICT` + запись в `audit_log` |
| Чек (фискальный) | `(fn, fd, fpd)` если все три заполнены | `409 Conflict` |

---

## 11. Audit Log

Записывать при каждом значимом событии:

| Событие | `action` | `entity_type` |
|---|---|---|
| Создание/изменение/удаление транзакции | CREATE / UPDATE / DELETE | transaction |
| Создание/изменение/удаление чека | CREATE / UPDATE / DELETE | receipt |
| Маппинг / размаппинг чека | MATCH / UNMATCH | match |
| Конфликт при импорте выписки | IMPORT_CONFLICT | import |
| Разрешение конфликта пользователем | UPDATE | transaction |

Поле `changed_by`: `"AGENT"` (API-вызов от агента) или `"USER"` (действие с фронта).
Поле `diff`: JSON-снапшот `{"before": {...}, "after": {...}}`.

---

## 12. Переменные окружения (`.env.example`)

```dotenv
ENVIRONMENT=local
SECRET_KEY=your-secret-key

DATABASE_URL=sqlite:///./bookkeeper.db
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/bookkeeper

YANDEX_S3_BUCKET=
YANDEX_ACCESS_KEY=
YANDEX_SECRET_KEY=
```

---

## 13. Что НЕ входит в текущую версию (Out of Scope)

- Очередь фоновых задач — агент сам парсит данные и присылает результат.
- Авторизация (JWT, OAuth2) — может быть добавлена позже.
- Push-уведомления и напоминания о выписках — следующая версия.
- Импорт/экспорт XLSX — следующая версия.

---

*Конец ТЗ. Версия 1.1*

---

## 14. Авторизация через Google OAuth2

### Концепция

Авторизация реализована через **Authorization Code Flow** (Google OAuth2).
Пользователь входит через Google-аккаунт → бэкенд выдаёт собственный **JWT** → фронт передаёт его в заголовке `Authorization: Bearer <token>` при каждом запросе.
Пароли не хранятся.

### Зависимости

```
pip install authlib python-jose[cryptography] httpx
```

Добавить в `requirements.txt`:
```
authlib>=1.3.0
python-jose[cryptography]>=3.3.0
httpx>=0.27.0
```

### Настройка Google Cloud Console

1. Создать проект в [console.cloud.google.com](https://console.cloud.google.com).
2. Перейти в **APIs & Services → Credentials → Create OAuth 2.0 Client ID**.
3. Тип приложения: **Web application**.
4. Добавить **Authorized redirect URIs**:
   - `http://localhost:8000/api/v1/auth/google/callback` — dev
   - `https://yourdomain.com/api/v1/auth/google/callback` — prod
5. Сохранить `GOOGLE_CLIENT_ID` и `GOOGLE_CLIENT_SECRET` в `.env`.

### Обновлённая схема `users`

```python
class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: str | None = None         # Имя из Google-профиля
    google_id: str | None = None         # Google sub (устойчив при смене email)
    avatar_url: str | None = None        # URL аватара из Google
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: datetime | None = None
    # password_hash — не используется, поле отсутствует
```

### Роутер `routers/auth.py`

```python
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from jose import jwt
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# Шаг 1: редирект на страницу Google
@router.get("/google")
async def login_via_google(request: Request):
    redirect_uri = request.url_for("auth_via_google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

# Шаг 2: callback после выбора аккаунта
@router.get("/google/callback", name="auth_via_google_callback")
async def auth_via_google_callback(
    request: Request,
    session: Session = Depends(get_session)
):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token["userinfo"]

    user = session.exec(
        select(User).where(User.email == userinfo["email"])
    ).first()

    if not user:
        user = User(
            email=userinfo["email"],
            full_name=userinfo.get("name"),
            google_id=userinfo.get("sub"),
            avatar_url=userinfo.get("picture"),
        )
        session.add(user)

    user.last_login_at = datetime.utcnow()
    session.commit()
    session.refresh(user)

    jwt_payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes),
    }
    access_token = jwt.encode(
        jwt_payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    # Возвращаем токен фронту через redirect с query-параметром
    return RedirectResponse(
        url=f"{settings.frontend_url}/auth/callback?token={access_token}"
    )

# Получить текущего пользователя (для фронта)
@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email,
            "full_name": current_user.full_name, "avatar_url": current_user.avatar_url}
```

### Dependency `dependencies/auth.py`

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlmodel import Session
from uuid import UUID

bearer_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    token = credentials.credentials
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise exc
    except JWTError:
        raise exc

    user = session.get(User, UUID(user_id))
    if user is None or not user.is_active:
        raise exc
    return user
```

### Подключение в `main.py`

```python
from starlette.middleware.sessions import SessionMiddleware
from app.dependencies.auth import get_current_user

# SessionMiddleware обязателен для authlib (хранит state OAuth2)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Публичные маршруты — без токена
app.include_router(auth_router)   # /auth/google, /auth/google/callback, /auth/me

# Защищённые маршруты — токен проверяется автоматически на уровне роутера
protected = {"dependencies": [Depends(get_current_user)]}
app.include_router(transactions_router, **protected)
app.include_router(receipts_router, **protected)
app.include_router(bank_statements_router, **protected)
app.include_router(reconciliation_router, **protected)
app.include_router(references_router, **protected)
app.include_router(documents_router, **protected)
```

### Изоляция данных пользователей

Каждый запрос к БД **обязан** фильтровать по `current_user.id` через JOIN с `accounts`.
Нарушение этого правила позволяет одному пользователю читать данные другого.

```python
# ПРАВИЛЬНО — фильтрация через JOIN
transactions = session.exec(
    select(Transaction)
    .join(Account, Transaction.account_id == Account.id)
    .where(Account.user_id == current_user.id)
).all()
```

### Фронтенд: страница `/auth/callback`

```tsx
// pages/AuthCallback.tsx
import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

export function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const token = searchParams.get("token");
    if (token) {
      sessionStorage.setItem("access_token", token);
      navigate("/");
    } else {
      navigate("/login");
    }
  }, []);

  return <div>Выполняется вход...</div>;
}
```

### Axios-интерцептор

```typescript
// api/client.ts
import axios from "axios";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL });

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      sessionStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
```

### Переменные окружения (дополнение к разделу 12)

```dotenv
GOOGLE_CLIENT_ID=xxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxx
JWT_SECRET_KEY=your-very-long-random-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080   # 7 дней
FRONTEND_URL=http://localhost:5173
```

### Out of Scope (авторизация)

- Refresh-токены — в данной версии не реализуются; токен живёт 7 дней, после чего пользователь проходит повторный вход через Google.
- Поддержка нескольких OAuth-провайдеров (GitHub, Apple) — следующая версия.
- Ролевая модель (admin/user) — следующая версия.

---

*Конец ТЗ. Версия 1.2*
