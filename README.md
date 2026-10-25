# Альфа.Поток — ITigers

Умный кредитный кабинет предпринимателя: Vue 3, Django/DRF, PostgreSQL и отдельный
FastAPI/LightGBM. Клиент и сотрудник банка проходят один сохранённый процесс:
продукт → заявка → оценка → решение/дозапрос/встречные условия → PDF → демовыдача.

- [Работающий сайт](https://alpha.srv-node.com/)
- [Swagger](https://alpha.srv-node.com/api/docs/), [OpenAPI YAML](backend/openapi.yaml)
- [Репозиторий](https://github.com/Favck/alfa-smart-credit)
- [Презентация и PDF для защиты](deliverables/), [речь на 3–5 минут, демо и ответы](docs/DEFENSE.md)
- [Архитектура и модель данных](docs/ARCHITECTURE.md), [состояния](docs/STATES.md)
- [Продуктовые гипотезы](docs/PRODUCT.md), [проверка сценариев](docs/TEST_SCENARIOS.md)
- [Коллекция Postman](docs/api/ITigers.postman_collection.json), [образец PDF](docs/samples/demo-statement.pdf)
- [Интеграция неизменённого ML](docs/ML_INTEGRATION.md), [CI/CD и откат](deploy/README.md)
- [AI-консультант: API, подключение и проверки](docs/AI_CONSULTANT.md)
- [Сторонние компоненты и смоделированные интеграции](THIRD_PARTY_NOTICES)

## Быстрый запуск

Нужны Git и Docker с Compose v2. Рекомендуется 4 ГБ свободной памяти и
доступ в интернет для первой сборки образов/зависимостей.

```sh
git clone https://github.com/Favck/alfa-smart-credit.git
cd alfa-smart-credit
docker compose up --build
```

Открыть http://127.0.0.1:5173/ . Swagger http://127.0.0.1:8000/api/docs/ .
Django автоматически применяет миграции и создаёт демо-профили. PostgreSQL
сохраняется в volume `postgres_data`. Повторный запуск не очищает заявки.
ML доступен Django по внутреннему адресу `http://ml:8001`.

Готовые профили выбираются по клику, пароли не нужны:

- `green` — ООО «Пекарня Зерно»: стандартные 2 млн / 24 мес. дают автоодобрение.
- `yellow` — ИП Смирнов: стандартный запрос передаётся сотруднику.
- `red` — ООО «СтройВектор»: отказ по синтетическому стоп-фактору.
- `underwriter` — сотрудник банка: очередь, данные ML и решения с причиной.

Полная проверка: green → новая заявка → отправить → принять условия → скачать
PDF → согласие → подписать → «Финансирование выдано · демо». Перезагрузить:
результат сохранён. Для дозапроса и встречного предложения см. сценарии выше.

## Что реализовано

- Четыре продукта, калькулятор и предварительная оценка настоящего ML-сервиса.
- AI-консультант: описание задачи → продукт, обоснование и срок → форма заявки.
- Демо-вход, отзыв токена, роли и проверка владельца каждой заявки/документа.
- Создание/редактирование черновика, отправка, сохранённые статусы и история.
- Автоматические проверки, синтетическое обогащение компанией/БКИ, скоринг.
- Одобрение, отказ, дозапрос и встречные условия с явным принятием клиентом.
- PDF/XLSX до 10 МиБ, до 6 вложений; авторизованное скачивание без OCR.
- Локальный PDF-договор, согласие, демоподпись и одна сохранённая демовыдача.
- Полные статьи и персональная отраслевая лента, адаптивная версия и две темы.
- Swagger без внешнего CDN; Docker и GitHub Actions с проверками и откатом.

В API не осталось плановых обработчиков с HTTP 501. Суммы — целые рубли,
ставки — проценты годовых, время — ISO 8601, идентификаторы — UUID.

## API

Базовый путь `/api/v1/`. Выполнить `POST /auth/demo-login/` с
`{"profile_id":"green"}` и передавать `Authorization: Token <token>`.
В Swagger нажать Authorize и вставить `Token <token>`.

Основные группы: `/products/`, `/company/`, `/news/`, `/scoring/pre-predict/`,
`/applications/`, `/bank/applications/`. Предложения, документы, подписание,
ответ на дозапрос и история вложены в `/applications/{id}/`.
Статус меняет только сервер; невалидные действия дают 400/403/404/409.
Клиент не получает внутренние score/PD и коды проверок банка.

Коллекция Postman содержит два отдельных сценария. Для ручной ветки выбрать
profile=yellow, повторно создать заявку и выполнить только соответствующие
действия: одобрение, отказ и встречные условия — альтернативы.

Админка: `/admin/`. Демо-профили туда доступа не имеют. Пароли не хранятся в
репозитории; локального администратора создаёт владелец установки:

```sh
docker compose exec backend python manage.py createsuperuser
```

## Подключение LLM жюри
+
+Сервис поддерживает подключение любой Open-Weights модели через
+OpenAI-совместимый API (vLLM, Ollama, TGI). Настройки задаются в `.env`.
+В случае отсутствия или недоступности сервера инференса конвейер прозрачно
+переключается на встроенный rule-based fallback без прерывания пользовательского
+сценария. Веса LLM не скачиваются; контейнеров Ollama/vLLM в Compose нет.
+
+```dotenv
+LLM_BASE_URL=http://internal-jury-llm-host:8000/v1
+LLM_API_KEY=jury_token
+LLM_MODEL_NAME=qwen2.5:7b
+```
+
+После задания адреса выполнить `docker compose up --build`. Без адреса работают
+локальные правила: разрыв → overdraft, товар → working_capital, оборудование →
+equipment_purchase, новая точка → investment. Таймаут внешнего запроса — 5 с.
+Compose содержит только backend (Django и готовая Vue-сборка), ml (FastAPI)
+и db (PostgreSQL); PostgreSQL и ML не публикуют порты на хосте.
+
+## Окружение и конфигурация

Python 3.11 (Docker), Node.js 22 (CI/production-сборка). Точные Python-пакеты
в `backend/requirements*.txt`, frontend в `frontend/package-lock.json`.
Версии Linux-окружения ML в `deploy/ml-constraints.txt`; исходная папка `ml/`
не менялась относительно коммита `50af371`.

- `DJANGO_SECRET_KEY` — секрет production, обязательна безопасная генерация владельцем.
- `DJANGO_DEBUG` — true локально, false в production.
- `DJANGO_ALLOWED_HOSTS` — разрешённые имена через запятую.
- `DEMO_MODE` — публичные синтетические входы; true только для стенда.
- `ML_BASE_URL` — внутренний адрес ML; `ML_TIMEOUT_SECONDS` — 2.5 по умолчанию.
- `ML_INTEGRATION=1` — включить проверки реального ML в pytest.
- `API_PROXY_TARGET` — адрес Django для локального Vite.
- `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL_NAME`, `LLM_TIMEOUT_SECONDS` — подключение консультанта через Chat Completions.

Пример переменных в `backend/.env.example`. Локально читается `backend/.env`,
в Docker — корневой `.env`; окружение процесса имеет приоритет.
Отключение DEMO_MODE запрещает новые демо-входы, но ранее
выданные токены нужно отзывать отдельно.

## Разработка без Docker

В Windows для нативного LightGBM нужен путь без кириллицы; Docker использует
`/app` и устраняет это ограничение. Не менять ML для обхода пути.
Python: создать venv, установить `backend/requirements-dev.txt`, выполнить
`python backend/manage.py migrate`, `seed_demo` и `runserver 127.0.0.1:8000`.
ML: в отдельной копии исходного `ml/` установить его requirements и запустить
`uvicorn app.main:app --host 127.0.0.1 --port 8001` из каталога ml.
Frontend: в `frontend/` выполнить `npm ci`, затем `npm run dev`.

## Проверки

Из корня, с установленным backend/requirements-dev.txt:

```sh
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
python backend/manage.py spectacular --validate --fail-on-warn --file backend/openapi.yaml
python -m pytest
```

Для реального ML дополнительно задать ML_INTEGRATION=1 и ML_BASE_URL;
CI делает это автоматически. В frontend: `npm ci && npm run build`.
Форматирование backend: из backend выполнить `python -m isort --check-only .`,
`python -m black --check .`, `python -m flake8 .`.

Проверка неизменности модели: `git diff --exit-code 50af371 -- ml`.
Версия сдаваемого результата фиксируется тегом `hackathon-itigers-v2`;
его SHA: `git rev-parse hackathon-itigers-v2`. Дедлайн организаторов
в репозиторий не закладывается; команда сверяет его отдельно.

## Демонстрационный режим

Готовые профили позволяют проверить клиентский и банковский сценарии.
Компания, кредитная история и статьи входят в комплект тестовых данных.
Подписание и выдача в этом режиме смоделированы и не создают юридических
обязательств. Код и веса ML-разработчика сохраняются без изменений.
Описание процесса — в продуктовой и технической документации.

Production использует отдельный Compose project `alfa-potok`, собственную
сеть и каталог данных. CI доставляет собранные образы только этого проекта.
Соседние приложения на общем сервере не входят в область деплоя.
