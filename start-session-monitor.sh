#!/bin/sh
set -eu
PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
export PATH
case "${1:-}" in
  verify-s) VERIFY_S_ONCE=1; export VERIFY_S_ONCE ;;
  '') ;;
  *) echo 'Usage: start-session-monitor.sh [verify-s]'; exit 2 ;;
esac
cd /volume1/docker/hollister
umask 022
echo 'Progress: /volume1/docker/hollister/session-monitor-start.log'
exec >session-monitor-start.log 2>&1
dc() { docker compose -p hollister -f compose.yaml --profile manual --profile session "$@"; }
dc config --quiet
docker volume inspect --format '{{.Name}}' hollister_browser-data
dc build session-monitor
dc stop hollister manual-browser
if test -f compose.live.yaml; then
    docker compose -p hollister-live -f compose.live.yaml stop live
fi
if test -f compose.manual.yaml; then
    docker compose -p hollister-manual -f compose.manual.yaml stop manual
fi
dc up -d --no-deps session-monitor
log="verification-session-$(date +%Y%m%d-%H%M%S).log"
nohup timeout 3600 docker compose -p hollister -f compose.yaml --profile session logs --follow --since=1m --no-color session-monitor >"$log" 2>&1 </dev/null &
echo "Logs: $log"
echo 'Continuous browser monitor started. Do not run resume or start a second monitor.'
