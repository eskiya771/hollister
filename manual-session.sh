#!/bin/sh
# Only this project's monitor and manual browser are controlled.
set -eu
PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
export PATH
cd /volume1/docker/hollister
umask 022
monitor() { docker compose -p hollister -f compose.yaml "$@"; }
manual() { docker compose -p hollister-manual -f compose.manual.yaml "$@"; }
if test -f compose.live.yaml; then
    if test -n "$(docker compose -p hollister-live -f compose.live.yaml ps -q --status running live)"; then
        echo 'The live monitor already owns the browser profile. Leave it running; do not use start/resume.'
        exit 1
    fi
fi
case "${1:-}" in
  start)
    echo 'Building the manual browser; the monitor continues during the build.'
    manual config --quiet
    manual build manual >manual-build.log 2>&1 || {
      tail -n 30 manual-build.log
      exit 1
    }
    monitor stop hollister
    if ! manual up -d --no-deps --force-recreate manual; then
      manual stop manual
      monitor start hollister
      exit 1
    fi
    attempt=0
    until manual logs --no-color manual 2>&1 | grep -q manual_browser_ready; do
      attempt=$((attempt + 1))
      if [ "$attempt" -ge 60 ]; then
        manual logs --tail=30 manual
        manual stop manual
        monitor start hollister
        echo 'Manual browser failed to become ready. Monitor resumed.'
        exit 1
      fi
      sleep 2
    done
    echo 'READY: use the SSH tunnel and http://127.0.0.1:6080/vnc.html'
    ;;
  resume)
    manual stop manual
    monitor start hollister
    nohup timeout 1100 docker compose -p hollister -f compose.yaml logs --follow --since=1m --no-color hollister >verification-manual.log 2>&1 </dev/null &
    echo 'Monitor resumed. Logs: /volume1/docker/hollister/verification-manual.log'
    ;;
  *)
    echo 'Usage: sudo /bin/sh /volume1/docker/hollister/manual-session.sh start|resume'
    exit 2
    ;;
esac
