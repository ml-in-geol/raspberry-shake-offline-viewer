#!/usr/bin/env bash
# Double-clickable launcher for a prepared Raspberry Shake and macOS laptop.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

pause_on_error() {
  status=$?
  if (( status != 0 )); then
    echo
    echo "Setup stopped with an error. Review the message above."
    read -r -p "Press Return to close this window…" _
  fi
  exit "$status"
}
trap pause_on_error EXIT

echo "Raspberry Shake Live"
echo "===================="
echo

bash "$PROJECT_DIR/scripts/setup_direct_ethernet_macos.sh" --auto

echo "Waiting for the Raspberry Shake at rs.local…"
shake_ready=false
for _ in {1..60}; do
  if ping -c 1 -W 1000 rs.local >/dev/null 2>&1; then
    shake_ready=true
    break
  fi
  sleep 2
done

if [[ "$shake_ready" != true ]]; then
  echo "The Ethernet link is active, but rs.local did not respond within two minutes." >&2
  echo "Confirm that the Shake is powered and was prepared for the standard 169.254.8.11 viewer address." >&2
  exit 1
fi

echo "Raspberry Shake found. Starting the live viewer…"
trap - EXIT

if [[ -d "$PROJECT_DIR/Raspberry Shake Live.app" ]]; then
  open "$PROJECT_DIR/Raspberry Shake Live.app"
  echo "The dashboard will open in your browser. You can close this Terminal window."
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is not installed." >&2
  echo "Use the packaged GitHub Release, or install Python 3 before running this source checkout." >&2
  read -r -p "Press Return to close this window…" _
  exit 1
fi

cd "$PROJECT_DIR"
exec python3 offline_viewer.py
