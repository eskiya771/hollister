#!/bin/sh
# Use the original project and existing volume. Never start a monitor here.
set -eu
PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
export PATH
cd /volume1/docker/hollister
umask 022
echo 'Progress: /volume1/docker/hollister/setup-manual-browser.log'
exec >setup-manual-browser.log 2>&1
test "$(id -u)" = 0
dc() { docker compose -p hollister -f compose.yaml --profile manual "$@"; }
dc config --quiet
docker volume inspect --format '{{.Name}}' hollister_browser-data
if test -f compose.live.yaml; then
    docker compose -p hollister-live -f compose.live.yaml stop live
fi
if test -f compose.manual.yaml; then
    docker compose -p hollister-manual -f compose.manual.yaml stop manual
fi
dc stop hollister
dc build manual-browser
dc run --rm --no-deps manual-browser python -m unittest -v test_profile_lock
dc up -d --no-deps manual-browser
log="verification-manual-browser-$(date +%Y%m%d-%H%M%S).log"
nohup timeout 3600 docker compose -p hollister -f compose.yaml --profile manual logs --follow --since=1m --no-color manual-browser >"$log" 2>&1 </dev/null &
attempt=0
until curl -fsS --max-time 3 -o /dev/null http://127.0.0.1:6080/vnc.html && dc logs --since=3m --no-color manual-browser 2>&1 | grep -q 'Manueller Browser bereit'; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
        dc logs --tail=80 manual-browser
        echo 'Manual browser readiness failed. Monitor remains stopped; inspect logs.'
        exit 1
    fi
    sleep 2
done
dc ps --all hollister manual-browser
id=$(dc ps -q manual-browser)
docker inspect --format '{{range .Mounts}}{{if eq .Destination "/data"}}browser_volume={{.Name}}{{end}}{{end}}' "$id"
echo "READY: manual-browser running in project hollister. Log: $log"
echo 'Browser stays running until explicitly stopped. No stock checks or Telegram loop started.'
