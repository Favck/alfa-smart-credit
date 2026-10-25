# Развёртывание Альфа.Поток

Compose project `alfa-potok`: только backend, ml, db. Backend-образ содержит
Django, Gunicorn и готовую Vue-сборку, которую отдаёт WhiteNoise. Nginx
направляет alpha.srv-node.com на 127.0.0.1:8092. У ML и PostgreSQL внешних
портов нет. Другие проекты не входят в команды Compose или миграции.

LLM-веса и контейнеры Ollama/vLLM/TGI не устанавливаются и не скачиваются.
При заданном LLM_BASE_URL используется внешний Chat Completions endpoint;
без адреса и при ошибках работают правила. Окружение хранится в закрытом
/opt/alfa-potok/.env. Лимиты памяти: backend 384 МиБ, ML 384 МиБ, db 192 МиБ.
PostgreSQL: shared_buffers=32MB, work_mem=2MB, max_connections=40.
Данные: /opt/alfa-potok/postgres; резервные копии: /opt/alfa-potok/backups.

## CI/CD

Push main запускает проверки Django, OpenAPI и тесты на PostgreSQL с настоящим
ML. Затем собираются образы, запускается полный трёхсервисный стенд,
проверяются UI/API и перенос SQLite-фикстуры в PostgreSQL. По SSH передаются
образы backend, ML и PostgreSQL. Ветки проверяются без production-деплоя.

Ключ ALFA_DEPLOY_SSH_KEY разрешает только deploy SHA через alfa-deploy.
Root-owned скрипт: /usr/local/sbin/alfa-potok-deploy; конфигурация:
/opt/alfa-potok/compose.yaml. Перед установкой выполняется compose config
--quiet. Текущая версия — current-release, рабочая конфигурация —
last-good-compose.yaml. Глобальные перезапуски Docker/Nginx и prune не нужны.

## Перенос базы

При первом переходе останавливается только backend проекта и создаётся
SQLite-копия. Экспорт сохраняет первичные ключи пользователей и естественные
внешние ссылки. После миграций PostgreSQL импортируются пользователи,
токены, заявки, история, офферы и документы. verify_legacy_import проверяет
количества, ID пользователей, пароли и хеши документов до включения сайта.
Исходная SQLite-база и копия сохраняются.

При следующих обновлениях создаётся pg_dump. Неуспешный запуск возвращает
предыдущие образы, конфигурацию и данные. При неуспехе первого перехода
возвращается исходный SQLite-стенд. Операции ограничены собственной базой
и контейнерами проекта.

## Сервер жюри

В .env задаются LLM_BASE_URL, LLM_API_KEY, LLM_MODEL_NAME. Далее запускается
`docker compose up --build`. Дополнительного флага включения нет.
При пустом адресе обращения к внешней модели не отправляются.
