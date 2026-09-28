#!/usr/bin/env bash
# Set a Mac wired network service for a direct Raspberry Shake connection.
set -euo pipefail

HOST_IP="169.254.8.11"
NETMASK="255.255.0.0"
SERVICE=""
AUTO_SERVICE=false
RESTORE_DHCP=false

usage() {
  cat <<'USAGE'
Usage:
  setup_direct_ethernet_macos.sh --list
  setup_direct_ethernet_macos.sh --auto [--host-ip 169.254.8.11]
  setup_direct_ethernet_macos.sh --service "Service Name" [--host-ip 169.254.8.11]
  setup_direct_ethernet_macos.sh (--auto | --service "Service Name") --restore-dhcp

--list does not change any network configuration. The other forms require a
macOS administrator password and modify only the specified network service.
USAGE
}

if [[ $# -eq 0 ]]; then
  usage
  exit 2
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list)
      networksetup -listallnetworkservices
      exit 0
      ;;
    --service)
      SERVICE="${2:-}"
      shift 2
      ;;
    --auto)
      AUTO_SERVICE=true
      shift
      ;;
    --host-ip)
      HOST_IP="${2:-}"
      shift 2
      ;;
    --restore-dhcp)
      RESTORE_DHCP=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This helper supports macOS only." >&2
  exit 1
fi

if [[ "$AUTO_SERVICE" == true && -n "$SERVICE" ]]; then
  echo "Use either --auto or --service, not both." >&2
  exit 2
fi

if [[ "$AUTO_SERVICE" == true ]]; then
  while IFS=$'\t' read -r candidate_service candidate_device; do
    [[ -n "$candidate_service" && -n "$candidate_device" ]] || continue
    interface_state="$(ifconfig "$candidate_device" 2>/dev/null || true)"
    if grep -q 'status: active' <<<"$interface_state" && grep -Eq 'media:.*(baseT|Ethernet)' <<<"$interface_state"; then
      SERVICE="$candidate_service"
      break
    fi
  done < <(
    networksetup -listnetworkserviceorder | awk '
      /^\([0-9]+\)/ {
        service=$0
        sub(/^\([0-9]+\) /, "", service)
      }
      /\(Hardware Port: .* Device: / {
        device=$0
        sub(/^.*Device: /, "", device)
        sub(/\).*$/, "", device)
        print service "\t" device
      }
    '
  )
  if [[ -z "$SERVICE" ]]; then
    echo "No active wired Ethernet service was found." >&2
    echo "Connect and power the Raspberry Shake, then try again." >&2
    exit 1
  fi
  echo "Detected active wired service: $SERVICE"
fi

if [[ -z "$SERVICE" ]]; then
  echo "A network service is required. Use --auto or run with --list first." >&2
  exit 2
fi

if [[ "$RESTORE_DHCP" == true ]]; then
  echo "Restoring DHCP on: $SERVICE"
  sudo networksetup -setdhcp "$SERVICE"
else
  if [[ ! "$HOST_IP" =~ ^169\.254\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    echo "The host IP must be in the Raspberry Shake discovery range (169.254.x.x)." >&2
    exit 2
  fi
  current_ip="$(networksetup -getinfo "$SERVICE" | awk -F': ' '/^IP address:/{print $2}')"
  if [[ "$current_ip" == "$HOST_IP" ]]; then
    echo "$SERVICE is already set to $HOST_IP/$NETMASK"
  else
    echo "Setting $SERVICE to $HOST_IP/$NETMASK for the direct Raspberry Shake link"
    sudo networksetup -setmanual "$SERVICE" "$HOST_IP" "$NETMASK" ""
  fi
fi
