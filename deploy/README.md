# Production: https://alpha.srv-node.com

Push в `main` запускает `.github/workflows/deploy.yml`: pytest, Django check,
проверка миграций, сборка Vue, сборка двух production-образов и доставка
по SSH. Pull request выполняет проверки и сборки без деплоя.
Повторный деплой: Actions → CI and production deploy → Run workflow → main.

## Изоляция

- Сервер: `2.27.205.29`, SSH `22222`.
- Compose project: `alfa-potok`; только собственная сеть и контейнеры.
- Рабочий каталог: `/opt/alfa-potok`; закрытый `.env` содержит Django secret.
- SQLite: `/opt/alfa-potok/data/db.sqlite3`, сохраняется между деплоями.
- Внешний вход: отдельный Nginx virtual host `alpha.srv-node.com` →
  `127.0.0.1:8092`; Django доступен только внутри сети проекта.
- Лимиты памяти: backend 384 MiB, frontend 128 MiB. Ротация Docker-логов.
- HTTPS: Let's Encrypt, webroot `/var/www/alfa-potok-acme`, certbot timer.
- Пользователь `alfa-deploy` без Docker-группы и общего sudo-доступа.
  Отдельный ключ разрешает только фиксированную команду деплоя с SHA.
  SSH forwarding, PTY и произвольные команды запрещены.
- GitHub secrets: `ALFA_DEPLOY_SSH_KEY`, `ALFA_DEPLOY_KNOWN_HOSTS`.
  Ключи и `.env` в Git не хранятся.

Frontend сохраняет существующее поведение: интерфейс работает на демоданных.
Django API и Swagger доступны на `/api/v1/` и `/api/docs/`.
`DEMO_MODE=true` намеренно включает синтетические демонстрационные профили.

## Обновление конфигурации сервера

`compose.production.yaml` установлен как `/opt/alfa-potok/compose.yaml`,
`deploy/server-deploy.sh` — как `/usr/local/sbin/alfa-potok-deploy`,
`deploy/nginx.conf` — как `/etc/nginx/sites-available/alfa-potok.conf`.
Это root-owned конфигурация. CI обновляет только образы приложения;
изменения этих трёх файлов нужно отдельно установить администратором,
проверив `docker compose config --quiet` и `nginx -t` перед reload.
Не выполнять глобальные `docker system prune`, `docker compose down`
или перезапуск Docker/Nginx для обновления приложения.

## Проверки и откат

Сервер блокирует параллельные деплои через flock, перед обновлением делает
согласованную SQLite backup в `/opt/alfa-potok/backups/`, затем ждёт
healthcheck обоих контейнеров и проверяет API через frontend.
При ошибке останавливает только контейнеры этого проекта, восстанавливает
предыдущую БД и предыдущие образы. Неуспешный первый деплой остаётся
остановленным. Неудачный rollback требует вмешательства администратора.
Автооткат теряет записи, сделанные после преддеплойной резервной копии;
для текущего демонстрационного стенда это допустимо. Для реальных данных
потребуются окно обслуживания и отдельная стратегия миграций.

Текущий SHA записан в `/opt/alfa-potok/current-release`. Старые образы и
резервные копии автоматически не удаляются. Контролировать место на диске
и удалять только заведомо ненужные артефакты проекта.

Ручной откат администратором на сохранённый SHA (без восстановления БД):

```sh
cd /opt/alfa-potok
sudo env RELEASE_SHA=<40-символьный-SHA> docker compose \
  --project-name alfa-potok --file compose.yaml --env-file .env \
  up -d --wait --wait-timeout 150
```

БД восстанавливать отдельно из нужной копии при остановленном backend.
После успешного ручного отката обновить `current-release` на выбранный SHA.
