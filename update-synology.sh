#!/bin/sh
# Rebuild only Hollister, keeping .env and the persistent browser volume.
set -eu
PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
export PATH
cd /volume1/docker/hollister
umask 022
echo 'Update progress: /volume1/docker/hollister/update.log'
exec >update.log 2>&1
trap 'echo "Update stopped: inspect update.log."' 0
test "$(id -u)" = 0
monitor() { docker compose -p hollister -f compose.yaml "$@"; }
monitor config --quiet
echo 'Building latest source (upstream b745f8f plus preserved local changes).'
monitor build hollister
monitor run --rm --no-deps hollister python smoke_browser.py
# The manual browser must release the shared profile before the monitor starts.
if test -f compose.manual.yaml; then
    docker compose -p hollister-manual -f compose.manual.yaml stop manual
fi
if test -f compose.live.yaml; then
    docker compose -p hollister-live -f compose.live.yaml stop live
fi
monitor up -d --no-deps --force-recreate hollister
nohup timeout 1100 docker compose -p hollister -f compose.yaml logs --follow --since=1m --no-color hollister >verification-update.log 2>&1 </dev/null &
monitor exec -T hollister python app.py --test-telegram
monitor ps hollister
echo 'Updated container started. Inspect verification-update.log for the real stock check and Telegram acknowledgement.'
trap - 0
