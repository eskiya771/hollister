#!/bin/sh
# Authorized exception: mevi may forward only to the NAS noVNC endpoint.
set -eu
PATH=/usr/bin:/bin:/usr/sbin:/sbin
export PATH
mode=${1:-apply}
original=/etc/ssh/sshd_config
sshd=/usr/bin/sshd
scratch=$(mktemp -d /tmp/hollister-ssh-check.XXXXXX)
trap 'rm -f "$scratch/config" "$scratch/key" "$scratch/key.pub" "$scratch/effective"; rmdir "$scratch"' 0
cp "$original" "$scratch/config"
if ! grep -q '^# BEGIN HOLLISTER BROWSER TUNNEL$' "$scratch/config"; then
    cat >>"$scratch/config" <<'CONFIG'

# BEGIN HOLLISTER BROWSER TUNNEL
Match User mevi
    AllowTcpForwarding local
    PermitOpen 127.0.0.1:6080
# END HOLLISTER BROWSER TUNNEL
CONFIG
fi
if [ "$mode" = check ]; then
    # A disposable key permits syntax testing as mevi without reading host keys.
    ssh-keygen -q -t ed25519 -N '' -f "$scratch/key"
    "$sshd" -t -h "$scratch/key" -f "$scratch/config"
    "$sshd" -T -h "$scratch/key" -f "$scratch/config" -C user=mevi,host=localhost,addr=127.0.0.1 >"$scratch/effective"
elif [ "$mode" = apply ]; then
    test "$(id -u)" = 0 || { echo 'Run with sudo.'; exit 1; }
    "$sshd" -t -f "$scratch/config"
    "$sshd" -T -f "$scratch/config" -C user=mevi,host=localhost,addr=127.0.0.1 >"$scratch/effective"
else
    echo 'Usage: enable-browser-tunnel.sh [check|apply]'
    exit 1
fi
grep -qx 'allowtcpforwarding local' "$scratch/effective"
grep -qx 'permitopen 127.0.0.1:6080' "$scratch/effective"
echo 'Validated: mevi, local forwarding, destination 127.0.0.1:6080 only.'
if [ "$mode" = check ]; then
    echo 'Check only: no SSH settings changed.'
    exit 0
fi
backup=$(mktemp /etc/ssh/sshd_config.before-hollister.XXXXXX)
cp -p "$original" "$backup"
cat "$scratch/config" >"$original"
if ! "$sshd" -t || ! systemctl reload sshd.service; then
    cp -p "$backup" "$original"
    systemctl reload sshd.service || true
    echo "Apply failed; restored $backup"
    exit 1
fi
echo "SSH reloaded successfully. Backup: $backup"
echo 'Reconnect the SSH tunnel; existing connections keep their previous permissions.'
