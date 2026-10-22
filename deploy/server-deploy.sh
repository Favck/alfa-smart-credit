#!/bin/bash
# Installed root-owned as /usr/local/sbin/alfa-potok-deploy.
set -Eeuo pipefail
umask 077
[[ $# == 1 && $1 =~ ^deploy\ ([0-9a-f]{40})$ ]] || exit 64
release=${BASH_REMATCH[1]}
cd /opt/alfa-potok
exec 9>/opt/alfa-potok/deploy.lock
flock -w 600 9
incoming=$(mktemp /opt/alfa-potok/incoming.XXXXXX)
trap 'rm -f "$incoming"' EXIT
timeout 300 cat > "$incoming"
gzip -t "$incoming"
gzip -dc "$incoming" | docker image load
docker image inspect "alfa-potok-backend:$release" >/dev/null
docker image inspect "alfa-potok-frontend:$release" >/dev/null
previous=$(cat current-release 2>/dev/null || true)
backup="/opt/alfa-potok/backups/$(date -u +%Y%m%dT%H%M%S)-$release.sqlite3"
if [[ -f data/db.sqlite3 ]]; then
    python3 - "$backup" <<'PY'
import sqlite3
import sys
with sqlite3.connect('/opt/alfa-potok/data/db.sqlite3') as source:
    with sqlite3.connect(sys.argv[1]) as target:
        source.backup(target)
PY
fi
export RELEASE_SHA=$release
compose() {
    docker compose --project-name alfa-potok --file compose.yaml \
        --env-file .env "$@"
}
if compose up -d --wait --wait-timeout 150 \
    && curl --fail --silent --show-error --retry 3 \
        -H 'Host: alpha.srv-node.com' \
        http://127.0.0.1:8092/api/v1/health/; then
    printf '%s\n' "$release" > current-release
    printf 'Deployed %s\n' "$release"
else
    compose logs --tail 80
    compose stop backend frontend
    if [[ -n $previous ]]; then
        if [[ -f $backup ]]; then
            cp "$backup" data/db.sqlite3
            chown 10001:10001 data/db.sqlite3
        fi
        export RELEASE_SHA=$previous
        compose up -d --wait --wait-timeout 150
        echo "Rolled back to $previous" >&2
    fi
    exit 1
fi
