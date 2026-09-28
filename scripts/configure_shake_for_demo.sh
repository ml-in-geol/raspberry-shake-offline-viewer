#!/usr/bin/env bash
# Configure a directly connected Raspberry Shake for this offline Mac demo.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SHAKE_HOST="myshake@rs.local"
HOST_IP="169.254.8.11"
PORT="8888"

usage() {
  cat <<'USAGE'
Usage: configure_shake_for_demo.sh [--shake myshake@rs.local] [--host-ip 169.254.8.11] [--port 8888] [--no-reboot]

Copies the UDP DATACAST destination to the Shake, sets its clock from this Mac
in UTC, enables stand-alone (offline) mode, then reboots it unless --no-reboot
is given. SSH password entry is interactive.
USAGE
}

REBOOT=true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --shake) SHAKE_HOST="${2:-}"; shift 2 ;;
    --host-ip) HOST_IP="${2:-}"; shift 2 ;;
    --port) PORT="${2:-}"; shift 2 ;;
    --no-reboot) REBOOT=false; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ ! "$HOST_IP" =~ ^169\.254\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
  echo "The target IP must be in the direct-link range (169.254.x.x)." >&2
  exit 2
fi
if [[ ! "$PORT" =~ ^[0-9]{1,5}$ ]] || (( PORT < 1 || PORT > 65535 )); then
  echo "Port must be between 1 and 65535." >&2
  exit 2
fi

TEMP_CONFIG="$(mktemp)"
cleanup() { rm -f "$TEMP_CONFIG"; }
trap cleanup EXIT
cat > "$TEMP_CONFIG" <<EOF
{
  "UDP-destinations": [
    { "dest": "OFFLINE-DEMO-MAC" }
  ],
  "OFFLINE-DEMO-MAC": {
    "Hostname": "$HOST_IP",
    "Port": "$PORT"
  }
}
EOF

echo "Checking connection to $SHAKE_HOST …"
ssh -o ConnectTimeout=8 "$SHAKE_HOST" 'true'

echo "Installing UDP destination $HOST_IP:$PORT …"
scp "$TEMP_CONFIG" "$SHAKE_HOST:/tmp/UDP-data-streams.conf"
ssh "$SHAKE_HOST" 'sudo install -m 0644 /tmp/UDP-data-streams.conf /opt/settings/user/UDP-data-streams.conf && rm -f /tmp/UDP-data-streams.conf'

UTC_NOW="$(date -u '+%Y-%m-%d %H:%M:%S')"
echo "Setting Shake time to $UTC_NOW UTC and enabling stand-alone mode …"
ssh "$SHAKE_HOST" "sudo date -u -s '$UTC_NOW'; rsh-stand-alone ON"

if [[ "$REBOOT" == true ]]; then
  echo "Rebooting the Shake. Wait about two minutes before starting the viewer."
  ssh "$SHAKE_HOST" 'sudo reboot' || true
else
  echo "Configuration complete. Reboot the Shake before the demo."
fi
