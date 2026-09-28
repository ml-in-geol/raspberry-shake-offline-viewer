#!/usr/bin/env bash
# Return the active wired network service to ordinary DHCP configuration.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Restore Ethernet DHCP"
echo "====================="
echo
bash "$PROJECT_DIR/scripts/setup_direct_ethernet_macos.sh" --auto --restore-dhcp
echo
echo "The wired Ethernet service is back on DHCP."
read -r -p "Press Return to close this window…" _
