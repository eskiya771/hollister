#!/bin/sh
# Run once via sudo on this NAS. Only the hollister Compose project is changed.
set -eu
PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
export PATH
cd /volume1/docker/hollister
umask 022
echo 'Installation: /volume1/docker/hollister/deploy.log'
exec >deploy.log 2>&1
trap 'echo "Installation stopped: inspect deploy.log before retrying."' 0
test "$(id -u)" = 0
test -s .env
chmod 600 .env
docker compose -p hollister config --quiet
docker compose -p hollister build hollister
docker compose -p hollister run --rm --no-deps hollister python smoke_browser.py
docker compose -p hollister up -d --no-deps hollister
# Capture both scheduled checks for remote review without granting Docker access.
nohup timeout 1100 docker compose -p hollister logs --follow --since=2m --no-color hollister >verification.log 2>&1 </dev/null &
docker compose -p hollister exec -T hollister python app.py --test-telegram
docker compose -p hollister ps hollister
echo 'Container started. Stock/Telegram confirmation still requires verification.log review.'
trap - 0
