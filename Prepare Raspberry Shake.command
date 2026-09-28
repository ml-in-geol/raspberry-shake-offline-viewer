#!/usr/bin/env bash
# One-time owner setup: standardize the Mac address and the Shake DATACAST target.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

pause_on_exit() {
  status=$?
  echo
  if (( status == 0 )); then
    echo "Preparation finished. The Shake is rebooting; give it about two minutes."
  else
    echo "Preparation stopped with an error. Review the message above."
  fi
  read -r -p "Press Return to close this window…" _
  exit "$status"
}
trap pause_on_exit EXIT

echo "Prepare Raspberry Shake for portable offline viewing"
echo "===================================================="
echo
echo "This one-time operation will:"
echo "  1. Set this Mac's active wired adapter to 169.254.8.11/16."
echo "  2. Send the Shake's DATACAST stream to 169.254.8.11:8888."
echo "  3. Enable the Shake's stand-alone mode and reboot it."
echo
read -r -p "Press Return to continue, or close this window to cancel…" _

bash "$PROJECT_DIR/scripts/setup_direct_ethernet_macos.sh" --auto

echo "Waiting for the Raspberry Shake at rs.local…"
shake_ready=false
for _ in {1..30}; do
  if ping -c 1 -W 1000 rs.local >/dev/null 2>&1; then
    shake_ready=true
    break
  fi
  sleep 2
done

if [[ "$shake_ready" != true ]]; then
  echo "The Shake did not respond at rs.local." >&2
  exit 1
fi

bash "$PROJECT_DIR/scripts/configure_shake_for_demo.sh" --host-ip 169.254.8.11
