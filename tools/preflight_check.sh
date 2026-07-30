#!/usr/bin/env bash
set -u

MODE="${1:-all}"
PASS=0
WARN=0
FAIL=0

ok()   { printf '[ OK ] %s\n' "$*"; PASS=$((PASS+1)); }
warn() { printf '[WARN] %s\n' "$*"; WARN=$((WARN+1)); }
fail() { printf '[FAIL] %s\n' "$*"; FAIL=$((FAIL+1)); }

have() { command -v "$1" >/dev/null 2>&1; }

check_vm() {
  echo '=== VM / network checks ==='
  have ip && ok 'ip command is available' || fail 'ip command is missing'
  have nmcli && ok 'NetworkManager CLI is available' || warn 'nmcli is unavailable'

  if have ip; then
    ip -br addr || true
    ip route || true
    ip route | grep -q '^default ' && ok 'a default route exists' || fail 'no default route found'
    ip route | grep -q '192\.168\.123\.0/24' && ok 'Go2 subnet route exists' || warn 'no 192.168.123.0/24 route found'
  fi
}

check_dock() {
  echo '=== Dock / ROS runtime checks ==='
  [ -r /etc/os-release ] && . /etc/os-release
  printf 'OS: %s %s\n' "${NAME:-unknown}" "${VERSION_ID:-unknown}"

  have ros2 && ok 'ros2 CLI is available' || fail 'ros2 CLI is not available; source the Foxy environment first'
  [ "${ROS_DISTRO:-}" = 'foxy' ] && ok 'ROS_DISTRO is foxy' || warn "ROS_DISTRO is '${ROS_DISTRO:-unset}', archived runtime used foxy"
  [ "${RMW_IMPLEMENTATION:-}" = 'rmw_cyclonedds_cpp' ] && ok 'CycloneDDS RMW selected' || warn "RMW_IMPLEMENTATION is '${RMW_IMPLEMENTATION:-unset}'"
  [ -n "${CYCLONEDDS_URI:-}" ] && ok 'CYCLONEDDS_URI is set' || warn 'CYCLONEDDS_URI is not set'

  if have ros2; then
    for pkg in unitree_go unitree_api slam_toolbox robot_localization nav2_map_server nav2_amcl nav2_planner nav2_controller; do
      if ros2 pkg prefix "$pkg" >/dev/null 2>&1; then
        ok "package found: $pkg ($(ros2 pkg prefix "$pkg" 2>/dev/null))"
      else
        warn "package not found: $pkg"
      fi
    done

    for pkg in go2_perception go2_slam go2_twist_bridge; do
      ros2 pkg prefix "$pkg" >/dev/null 2>&1 && ok "Go2 package found: $pkg" || warn "Go2 package not found: $pkg"
    done
  fi

  [ -f reference/nav2_foxy_floor3.yaml ] && ok 'reference Nav2 config exists' || warn 'run from repository root to check project files'
  [ -f reference/floor_3_semantic.yaml ] && ok 'Floor 3 semantic file exists' || warn 'Floor 3 semantic file not found from current directory'
}

case "$MODE" in
  vm) check_vm ;;
  dock) check_dock ;;
  all) check_vm; echo; check_dock ;;
  *) echo "Usage: $0 [vm|dock|all]" >&2; exit 2 ;;
esac

echo
echo "Summary: $PASS ok, $WARN warnings, $FAIL failures"
[ "$FAIL" -eq 0 ]
