#!/bin/bash
# One-time bootstrap, run as root from a directory containing the deployment
# files plus deploy-key.pub. Refuses to overwrite an existing installation.
set -Eeuo pipefail
[[ $EUID == 0 ]]
[[ ! -e /opt/alfa-potok ]]
[[ ! -e /etc/nginx/sites-available/alfa-potok.conf ]]
! getent passwd alfa-deploy >/dev/null
! ss -H -ltn 'sport = :8092' | grep -q .
install -d -m 750 /opt/alfa-potok /opt/alfa-potok/backups
docker ps --format '{{.Names}}|{{.ID}}' | sort > /opt/alfa-potok/neighbors.before
sha256sum /etc/nginx/sites-enabled/* > /opt/alfa-potok/nginx.before
install -d -m 700 -o 10001 -g 10001 /opt/alfa-potok/data
install -m 600 compose.production.yaml /opt/alfa-potok/compose.yaml
install -m 600 compose.production.yaml /opt/alfa-potok/last-good-compose.yaml
install -m 755 server-deploy.sh /usr/local/sbin/alfa-potok-deploy
umask 077
python3 - <<'PY' > /opt/alfa-potok/.env
import secrets
print('DJANGO_SECRET_KEY=' + secrets.token_urlsafe(64))
PY
useradd --create-home --shell /bin/bash alfa-deploy
install -d -m 700 -o alfa-deploy -g alfa-deploy /home/alfa-deploy/.ssh
printf '%s %s\n' \
    'restrict,command="sudo /usr/local/sbin/alfa-potok-deploy \"$SSH_ORIGINAL_COMMAND\""' \
    "$(cat deploy-key.pub)" > /home/alfa-deploy/.ssh/authorized_keys
chown alfa-deploy:alfa-deploy /home/alfa-deploy/.ssh/authorized_keys
chmod 600 /home/alfa-deploy/.ssh/authorized_keys
printf 'alfa-deploy ALL=(root) NOPASSWD: /usr/local/sbin/alfa-potok-deploy\n' \
    > /etc/sudoers.d/alfa-potok-deploy
chmod 440 /etc/sudoers.d/alfa-potok-deploy
visudo -cf /etc/sudoers.d/alfa-potok-deploy
RELEASE_SHA=0000000000000000000000000000000000000000 docker compose \
    -f /opt/alfa-potok/compose.yaml --env-file /opt/alfa-potok/.env config --quiet
install -d -m 755 /var/www/alfa-potok-acme
cat > /etc/nginx/sites-available/alfa-potok.conf <<'NGINX'
server {
    listen 80;
    server_name alpha.srv-node.com;
    location /.well-known/acme-challenge/ { root /var/www/alfa-potok-acme; }
    location / { return 503; }
}
NGINX
ln -s /etc/nginx/sites-available/alfa-potok.conf /etc/nginx/sites-enabled/alfa-potok.conf
nginx -t
systemctl reload nginx
certbot certonly --webroot -w /var/www/alfa-potok-acme \
    -d alpha.srv-node.com --non-interactive --agree-tos \
    --register-unsafely-without-email \
    --deploy-hook '/usr/sbin/nginx -t && /bin/systemctl reload nginx'
install -m 644 nginx.conf /etc/nginx/sites-available/alfa-potok.conf
nginx -t
systemctl reload nginx
sha256sum --check /opt/alfa-potok/nginx.before
docker ps --format '{{.Names}}|{{.ID}}' | sort > /opt/alfa-potok/neighbors.after-bootstrap
diff -u /opt/alfa-potok/neighbors.before /opt/alfa-potok/neighbors.after-bootstrap
