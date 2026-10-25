# Архитектура и модель данных

Команда ITigers. Одна компания на демо-профиль, четыре кредитных
продукта, клиент и андеррайтер, сквозной путь до демонстрационной выдачи.
Технические администраторы работают отдельно через Django Admin.

```mermaid
flowchart LR
    U[Браузер: предприниматель / сотрудник] -->|HTTPS| N[Nginx: alpha.srv-node.com]
    N --> V[Vue 3: статическая сборка]
    N -->|/api /admin /static| D[Django + DRF + Gunicorn]
    D --> S[(PostgreSQL: заявки, аудит, документы)]
    D -->|внутренний HTTP, таймаут 2.5 с| M[FastAPI + неизменённый LightGBM]
    D --> A[Асинхронный AI-консультант]
    A -.->|Chat Completions; задан LLM_BASE_URL| L[Подключаемый LLM-провайдер]
    F[Синтетические компания и БКИ] --> D
    D --> P[Локальная генерация PDF]
    G[GitHub Actions: проверки и сборки] -->|SSH: только deploy SHA| R[Изолированный Compose alfa-potok]
    R -.-> D
    R -.-> V
    R -.-> M
```

ML оценивает риск; Django применяет отдельную политику и управляет статусами.
AI-консультант подбирает продукт по описанию задачи и передаёт параметры
в форму заявки. LLM-вызовы включаются отдельно; по умолчанию используются
базовые параметры ответа без обращения к провайдеру.
Стоп-фактор или score < 520 → отказ. Score ≥ 620 и сумма не выше доступного
лимита → одобрение. Остальное и недоступность ML → сотрудник. Предложение
хранится отдельно от исходного запроса: при встречных условиях исходные
сумма/срок остаются в заявке, выдача использует принятую сумму оффера.

```mermaid
erDiagram
    USER ||--o{ APPLICATION : owns
    APPLICATION ||--o{ STATUS_EVENT : records
    APPLICATION ||--o{ DECISION : receives
    APPLICATION ||--o{ OFFER : has
    APPLICATION ||--o{ INFO_REQUEST : has
    APPLICATION ||--o{ DOCUMENT : stores
    APPLICATION ||--o| DISBURSEMENT : completes
    OFFER ||--o| DOCUMENT : contract
    OFFER ||--o| DISBURSEMENT : accepted_terms
    APPLICATION {
      uuid id PK
      string number
      int owner_id FK
      string company_id
      json company
      string product_id
      int amount
      int term_months
      int monthly_revenue
      int current_monthly_payments
      string status
      json enrichment
      json scoring
      bool scoring_unavailable
      uuid request_id
      datetime updated_at
    }
    OFFER {
      uuid id PK
      uuid application_id FK
      string kind
      int amount
      int term_months
      decimal annual_rate_percent
      int monthly_payment
      string status
    }
    DOCUMENT {
      uuid id PK
      uuid application_id FK
      uuid offer_id FK
      string kind
      string filename
      binary content
      string sha256
      datetime signed_at
    }
    INFO_REQUEST {
      uuid id PK
      uuid application_id FK
      string message
      json requested_fields
      bool document_required
      json response
      string status
    }
    DISBURSEMENT {
      uuid id PK
      uuid application_id FK
      uuid offer_id FK
      int amount
      string reference
      bool simulated
    }
```

Вспомогательные модели: StatusEvent (переход, роль, сообщение, время), Decision
(вердикт, причина, роль, итоговый статус), стандартные User и DRF Token.
Компания, продукты и статьи — синтетические справочники; в заявке сохраняется
снимок компании. Уникальные ограничения: один pending-оффер, один открытый
дозапрос, один договор на оффер, одна выдача на заявку и на оффер.

## Надёжность и доступ

- Владелец проверяется при каждом обращении; банковские операции требуют роли bank.
- Score/PD и внутренние проверки доступны сотруднику, клиенту — объяснение и следующее действие.
- Статус изменяет сервер. PATCH доступен только черновику; сравнение updated_at защищает от устаревшей записи.
- Внешний вызов ML выполняется вне транзакции записи. request_id связывает ответ с запуском.
- Повторные submit/accept/sign не создают повторную оценку, договор или выдачу после завершения действия.
- Документы: PDF/XLSX, до 10 МиБ, до 6 вложений. Файлы не исполняются и не распознаются; проверяются тип/структура/макросы и принадлежность. Скачивание — только через авторизованный API.
- Хранение PDF/XLSX в PostgreSQL выбрано для переносимого MVP и согласованных резервных копий. Для нагрузки нужны объектное хранилище, антивирус, PostgreSQL и очередь задач.
- Перед деплоем создаётся PostgreSQL backup. Неуспешная проверка запуска возвращает предыдущие образы, compose и БД.
- Контейнер ML без внешнего порта; лимиты памяти/CPU и один поток. Собственная сеть Compose и отдельный домен защищают соседние проекты от изменений конфигурации.

## Режим работы и интеграции

DEMO_MODE включает готовые профили для проверки клиентского и банковского
процесса. ФНС/ЕГРЮЛ/БКИ представлены тестовыми наборами данных.
Подписание и выдача в этом режиме смоделированы. PostgreSQL хранит заявки,
историю, офферы и документы в одной согласованной базе. Сервис ML подключён
через отдельный HTTP-контракт; развёртывание управляется Docker Compose.
