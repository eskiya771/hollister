#!/bin/sh
set -eu
ROOT=/volume1/docker/hollister
RELEASE="$ROOT/http-release"
DOCKER=/usr/local/bin/docker
OLD=hollister-session-monitor-1
NEW=hollister-http-monitor
IMAGE=hollister-http-monitor:latest
LOGFILE="$RELEASE/deployment.log"
exec >"$LOGFILE" 2>&1
chmod 644 "$LOGFILE"
test "$(id -u)" = 0 || { echo 'Root erforderlich'; exit 1; }
test -f "$ROOT/.env"
echo "Update gestartet: $(date)"
previous=browser
BACKUP="${NEW}-backup-$(date +%Y%m%d%H%M%S)"
if "$DOCKER" inspect "$NEW" >/dev/null 2>&1; then
    previous=http
    echo 'Bestehenden HTTP-Monitor aktualisieren'
else
    test "$("$DOCKER" inspect -f '{{.State.Running}}' "$OLD")" = true || {
        echo 'Kein aktiver Browser-Monitor für die erste Umstellung'; exit 1;
    }
fi
echo 'HTTP-Image bauen'
"$DOCKER" build -f "$RELEASE/Dockerfile.http" -t "$IMAGE" "$RELEASE"
echo 'Vorprüfung ohne Telegram; bestehender Monitor bleibt aktiv'
"$DOCKER" run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
    --env CHECK_INTERVAL_SECONDS=60 --env HTTP_MAX_CACHE_AGE_SECONDS=900 \
    "$IMAGE" python http_monitor.py --check-only
changed=0
success=0
cleanup() {
    if [ "$changed" = 1 ] && [ "$success" = 0 ]; then
        echo 'Fehler: Rückkehr zum bisherigen Monitor'
        "$DOCKER" rm -f "$NEW" >/dev/null 2>&1 || true
        if [ "$previous" = http ]; then
            if "$DOCKER" inspect "$BACKUP" >/dev/null 2>&1; then
                "$DOCKER" rename "$BACKUP" "$NEW"
            fi
            "$DOCKER" start "$NEW"
        else
            "$DOCKER" start "$OLD"
        fi
    fi
}
trap cleanup EXIT
trap 'exit 1' INT TERM
echo 'Bisherigen Monitor stoppen und aktualisierten HTTP-Monitor starten'
if [ "$previous" = http ]; then
    "$DOCKER" stop -t 90 "$NEW"
    "$DOCKER" rename "$NEW" "$BACKUP"
    changed=1
else
    changed=1
    "$DOCKER" stop -t 90 "$OLD"
fi
"$DOCKER" run -d --name "$NEW" --restart unless-stopped \
    --read-only --tmpfs /tmp:size=16m --cap-drop ALL --security-opt no-new-privileges \
    --log-opt max-size=5m --log-opt max-file=2 \
    --env-file "$ROOT/.env" --env CHECK_INTERVAL_SECONDS=60 \
    --env HTTP_MAX_CACHE_AGE_SECONDS=900 --env TZ=Europe/Berlin "$IMAGE"
n=0
while [ "$n" -lt 45 ]; do
    "$DOCKER" logs "$NEW" > "$RELEASE/first-cycle.log" 2>&1
    chmod 644 "$RELEASE/first-cycle.log"
    if grep -q 'summary variants=5 telegram_message_id=' "$RELEASE/first-cycle.log"; then
        test "$("$DOCKER" inspect -f '{{.State.Running}}' "$NEW")" = true
        success=1
        echo 'SUCCESS: HTTP-Monitor läuft; fünf Varianten an Telegram bestätigt'
        exit 0
    fi
    n=$((n + 1))
    sleep 2
done
echo 'Erster Telegram-Zyklus nicht bestätigt'
exit 1
