#!/usr/bin/env bash
set -euo pipefail

GO2_IF="${1:-ens33}"
INTERNET_IF="${2:-ens37}"
GO2_PROFILE="${GO2_PROFILE:-$GO2_IF}"
INTERNET_PROFILE="${INTERNET_PROFILE:-$INTERNET_IF}"
GO2_ADDRESS="${GO2_ADDRESS:-192.168.123.222/24}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing command: $1" >&2
    exit 1
  }
}
need nmcli

ensure_profile() {
  local profile="$1"
  local iface="$2"
  if ! nmcli -t -f NAME connection show | grep -Fxq "$profile"; then
    sudo nmcli connection add type ethernet ifname "$iface" con-name "$profile"
  fi
}

ensure_profile "$GO2_PROFILE" "$GO2_IF"
ensure_profile "$INTERNET_PROFILE" "$INTERNET_IF"

sudo nmcli connection modify "$GO2_PROFILE" \
  connection.interface-name "$GO2_IF" \
  connection.autoconnect yes \
  ipv4.method manual \
  ipv4.addresses "$GO2_ADDRESS" \
  ipv4.gateway "" \
  ipv4.dns "" \
  ipv4.never-default yes \
  ipv6.method ignore

sudo nmcli connection modify "$INTERNET_PROFILE" \
  connection.interface-name "$INTERNET_IF" \
  connection.autoconnect yes \
  ipv4.method auto \
  ipv4.dns "8.8.8.8,1.1.1.1" \
  ipv4.never-default no \
  ipv6.method ignore

sudo nmcli connection up "$GO2_PROFILE"
sudo nmcli connection up "$INTERNET_PROFILE"

echo
echo "========== addresses =========="
ip -br addr

echo
echo "========== routes =========="
ip route

echo
echo "========== devices =========="
nmcli device status
