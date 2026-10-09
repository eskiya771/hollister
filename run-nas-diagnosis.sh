#!/bin/sh
# One-shot root task. No production code/config changes, no image build.
set -eu
PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
export PATH
umask 077
test "$(id -u)" = 0 || { echo 'Docker access requires this one-shot task to run as root.'; exit 1; }
base=/volume1/docker/hollister/diagnostics-63617320
original=hollister-session-monitor-1
temporary=hollister-availability-diagnostic
url=https://www.hollisterco.com/shop/eu-de/p/camisole-mit-spitzenbesatz-fr-lagenlooks-63270319
mkdir -p "$base"
exec >"$base/job-status.log" 2>&1
chown mevi:users "$base/job-status.log"
test -f "$base/diagnostic_browser_entry.py"
test -f "$base/diagnose_availability.py"
test -f "$base/run_both_diagnostics.py"
test -f "$base/analyze_availability_capture.py"
test -f "$base/session_http_diagnostic.py"
test "$(docker inspect --format '{{.State.Running}}' "$original")" = true
test "$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}' "$original")" = hollister_browser-data
image=$(docker inspect --format '{{.Image}}' "$original")
test -n "$image"
if docker container inspect "$temporary" >/dev/null 2>&1; then
    echo 'Diagnostic container already exists; stopping without touching monitor.'
    exit 1
fi
stopped=0
created=0
cleanup() {
    result=$?
    trap - EXIT HUP INT TERM
    if test "$created" = 1; then
        docker stop --time 45 "$temporary" >/dev/null 2>&1 || true
        docker rm "$temporary" >/dev/null 2>&1 || true
    fi
    if test "$stopped" = 1; then
        if docker start "$original" >/dev/null 2>&1; then
            echo 'Original monitor restarted unchanged.'
        else
            echo 'ERROR: Original monitor restart failed; start hollister-session-monitor-1 in DSM.'
            result=1
        fi
    fi
    echo "Diagnostic job finished, exit=$result."
    exit "$result"
}
trap cleanup EXIT HUP INT TERM
echo 'Stopping original monitor gracefully; preserving browser volume.'
stopped=1
docker stop --time 90 "$original" >/dev/null
test "$(docker inspect --format '{{.State.Running}}' "$original")" = false
# Dedicated container, existing image/profile. CDP is not published to the host.
# No production env file or Telegram credentials are passed to this container.
created=1
docker run -d --name "$temporary" --init --read-only \
    --cap-drop ALL --security-opt no-new-privileges:true \
    --shm-size 512m --tmpfs /tmp:rw,size=512m,mode=1777 \
    --mount type=volume,source=hollister_browser-data,target=/data \
    --mount type=bind,source="$base",target=/diagnostics,readonly \
    -p 127.0.0.1:6080:6080 \
    -e DISPLAY=:99 -e SESSION_MONITOR=0 -e PYTHONPATH=/app \
    -e PRODUCT_URL="$url" -e BROWSER_PROFILE_DIR=/data/browser-profile \
    "$image" python /diagnostics/diagnostic_browser_entry.py >/dev/null
attempt=0
until docker exec "$temporary" python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=2).close()' >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    test "$attempt" -lt 45 || { echo 'Internal browser diagnostic endpoint not ready.'; exit 1; }
    sleep 2
done
echo 'Internal browser ready; comparing browser data with scoped session HTTP requests.'
# Timeout does not kill the original monitor; cleanup always restarts it.
code=0
timeout 600 docker exec -e PYTHONPATH=/app "$temporary" \
    python /diagnostics/run_both_diagnostics.py \
    --cdp http://127.0.0.1:9222 --session-http --output /tmp/availability-session-http.json || code=$?
if docker exec "$temporary" cat /tmp/availability-session-http.json >"$base/availability-session-http.json.pending" 2>/dev/null; then
    mv "$base/availability-session-http.json.pending" "$base/availability-session-http.json"
    chmod 600 "$base/availability-session-http.json"
    chown mevi:users "$base/availability-session-http.json"
    echo 'Sanitized result saved: availability-session-http.json'
else
    rm -f "$base/availability-session-http.json.pending"
    echo 'No completed capture available; no stock conclusion.'
fi
exit "$code"
