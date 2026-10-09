#!/bin/sh
set -eu
PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
export PATH
cd /volume1/docker/hollister
umask 022
live() { docker compose -p hollister-live -f compose.live.yaml "$@"; }
echo 'Build progress: /volume1/docker/hollister/live-build.log'
live config --quiet
live build live >live-build.log 2>&1 || { tail -n 30 live-build.log; exit 1; }
docker compose -p hollister -f compose.yaml stop hollister
docker compose -p hollister-manual -f compose.manual.yaml stop manual
if ! live up -d --no-deps --force-recreate live; then
    live stop live
    docker compose -p hollister -f compose.yaml start hollister
    exit 1
fi
log="verification-live-$(date +%Y%m%d-%H%M%S).log"
nohup timeout 1800 docker compose -p hollister-live -f compose.live.yaml logs --follow --since=1m --no-color live >"$log" 2>&1 </dev/null &
attempt=0
until live logs --no-color live 2>&1 | grep -q manual_browser_ready; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
        live logs --tail=30 live
        live stop live
        docker compose -p hollister -f compose.yaml start hollister
        echo 'Live browser did not become ready; previous monitor resumed.'
        exit 1
    fi
    sleep 2
done
echo "Started live monitor. Logs: $log"
echo 'Solve the CAPTCHA via the SSH tunnel. Keep the browser open; do NOT run manual-session.sh resume.'
