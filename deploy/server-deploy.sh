#!/bin/bash
# Root-owned; restricted SSH key can invoke only deploy <40-hex SHA>.
set -Eeuo pipefail
umask 077
[[ $# == 1 && $1 =~ ^deploy\ ([0-9a-f]{40})$ ]] || exit 64
release=${BASH_REMATCH[1]}
cd /opt/alfa-potok
exec 9>deploy.lock
flock -w 600 9
incoming=$(mktemp /opt/alfa-potok/incoming.XXXXXX)
trap 'rm -f "$incoming"' EXIT
timeout 300 cat > "$incoming"
gzip -t "$incoming"
gzip -dc "$incoming" | docker image load
for name in backend ml; do docker image inspect "alfa-potok-$name:$release" >/dev/null; done
docker image inspect postgres:17-alpine >/dev/null
previous=$(cat current-release 2>/dev/null || true)
backup="/opt/alfa-potok/backups/$(date -u +%Y%m%dT%H%M%S)-$release"
compose_config=compose.yaml
export RELEASE_SHA=$release
compose() { docker compose --project-name alfa-potok --file "$compose_config" --env-file .env "$@"; }
old_compose() { RELEASE_SHA="$previous" docker compose --project-name alfa-potok --file last-good-compose.yaml --env-file .env "$@"; }
was_pg=false
[[ -f postgres-migrated ]] && was_pg=true

backup_current() {
    [[ -n $previous ]] || return 0
    old_compose stop backend || return
    if $was_pg; then
        old_compose exec -T db sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup.dump" || return
    elif [[ -f data/db.sqlite3 ]]; then
        python3 - "$backup.sqlite3" <<'PY' || return
import sqlite3,sys
with sqlite3.connect('/opt/alfa-potok/data/db.sqlite3') as source:
    with sqlite3.connect(sys.argv[1]) as target: source.backup(target)
PY
        docker run --rm --network none --user 0 \
            -v "$backup.sqlite3:/app/data/db.sqlite3:ro" \
            -e DJANGO_DEBUG=true -e DATABASE_ENGINE=sqlite \
            "alfa-potok-backend:$previous" python manage.py dumpdata \
            --natural-foreign \
            --exclude contenttypes --exclude auth.permission > "$backup.json" || return
        cp "$backup.json" data/legacy.fixture.json || return
    fi
}

deploy_new() {
    backup_current || return
    compose up -d --wait --wait-timeout 90 db || return
    compose run --rm --no-deps -T backend python manage.py migrate --noinput || return
    if ! $was_pg && [[ -s data/legacy.fixture.json ]]; then
        compose run --rm --no-deps -T --user 0 backend python manage.py loaddata /app/data/legacy.fixture.json || return
        compose run --rm --no-deps -T --user 0 backend python manage.py verify_legacy_import /app/data/legacy.fixture.json || return
    fi
    if docker container inspect alfa-potok-frontend-1 >/dev/null 2>&1; then
        docker stop alfa-potok-frontend-1 >/dev/null || return
    fi
    compose up -d --remove-orphans --wait --wait-timeout 150 || return
    curl --fail --silent --show-error --retry 3 -H 'Host: alpha.srv-node.com' http://127.0.0.1:8092/api/v1/health/ || return
}

if deploy_new; then
    cp compose.yaml last-good-compose.yaml
    touch postgres-migrated
    printf '%s\n' "$release" > current-release
    printf 'Deployed %s; PostgreSQL active\n' "$release"
else
    compose logs --tail 60 || true
    compose stop backend ml || true
    if [[ -n $previous ]]; then
        if $was_pg && [[ -s $backup.dump ]]; then
            compose exec -T db sh -c 'exec pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --exit-on-error' < "$backup.dump"
        elif ! $was_pg; then
            compose stop db || true
            if [[ -s $backup.sqlite3 ]]; then cp "$backup.sqlite3" data/db.sqlite3; chown 10001:10001 data/db.sqlite3; fi
        fi
        export RELEASE_SHA=$previous
        compose_config=last-good-compose.yaml
        compose up -d --remove-orphans --wait --wait-timeout 150
        cp last-good-compose.yaml compose.yaml
        echo "Rolled back to $previous" >&2
    fi
    exit 1
fi
