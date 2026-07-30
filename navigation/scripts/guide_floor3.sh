#!/bin/bash

set -e

WS=/home/unitree/go2_nav_official_ws
PROJECT=/home/unitree/go2_guide_project
SEMANTIC=$PROJECT/semantic/floor_3_semantic.yaml

source_ros() {
  source /opt/ros/foxy/setup.bash
  source /home/unitree/graph_pid_ws/install/setup.bash
  source /home/unitree/go2_nav_official_ws/install/setup.bash
}

wait_tf() {
  source_ros
  echo "Checking map -> base_footprint..."
  timeout 8s ros2 run tf2_ros tf2_echo map base_footprint >/tmp/floor3_tf_check.log 2>&1 || true

  if grep -q "Translation" /tmp/floor3_tf_check.log; then
    echo "[OK] map -> base_footprint is available."
  else
    echo "[ERROR] map -> base_footprint is not available."
    echo "Run: ./floor3_localize.sh status"
    exit 1
  fi
}

wait_cmd_subscriber() {
  source_ros
  echo "Checking /cmd_vel subscriber..."
  info=$(ros2 topic info /cmd_vel || true)
  echo "$info"

  if echo "$info" | grep -q "Subscription count: 1"; then
    echo "[OK] /cmd_vel has subscriber."
  else
    echo "[ERROR] /cmd_vel has no subscriber. Bridge may not be running."
    echo "Run: ./floor3_nav_test.sh bridge"
    exit 1
  fi
}

prepare_hci() {
  source_ros

  echo "========== Floor 3 guide prepare: HCI lab start =========="
  echo "Make sure the robot is physically near hci_lab_view."
  echo ""

  echo "[1/6] Stop old Nav2 stack..."
  $WS/floor3_nav_test.sh stop 2>/dev/null || true

  echo "[2/6] Stop old localization stack..."
  $WS/floor3_localize.sh stop 2>/dev/null || true

  echo "[3/6] Start floor_3 localization..."
  $WS/floor3_localize.sh start
  sleep 10

  echo "[4/6] Publish initial pose: hci_lab_view..."
  $WS/floor3_localize.sh init_hci
  sleep 3
  wait_tf

  echo "[5/6] Start Nav2 planner/controller..."
  $WS/floor3_nav_test.sh start
  sleep 10

  echo "[6/6] Start go2_twist_bridge..."
  $WS/floor3_nav_test.sh bridge
  sleep 2
  wait_cmd_subscriber

  echo ""
  echo "[READY] Floor 3 guide stack is ready."
  echo "Next:"
  echo "  ./guide_floor3.sh to_elevator"
  echo "  ./guide_floor3.sh zero"
  echo "  ./guide_floor3.sh stop"
}

to_elevator() {
  source_ros
  wait_tf
  wait_cmd_subscriber

  echo "========== Navigating to elevator_3f_safe =========="
  echo "Safety: keep remote controller ready."
  python3 $WS/scripts/send_path_goal.py anchor $SEMANTIC elevator_3f_safe
}

to_hci() {
  source_ros
  wait_tf
  wait_cmd_subscriber

  echo "========== Navigating to hci_lab_view =========="
  echo "Safety: keep remote controller ready."
  python3 $WS/scripts/send_path_goal.py anchor $SEMANTIC hci_lab_view
}

status_all() {
  source_ros

  echo "========== Localization =========="
  $WS/floor3_localize.sh status || true

  echo ""
  echo "========== Nav2 =========="
  $WS/floor3_nav_test.sh status || true

  echo ""
  echo "========== cmd_vel =========="
  ros2 topic info /cmd_vel || true
}

zero_cmd() {
  source_ros
  $WS/floor3_nav_test.sh zero
}

stop_all() {
  source_ros
  echo "Stopping floor 3 guide stack..."
  $WS/floor3_nav_test.sh zero 2>/dev/null || true
  $WS/floor3_nav_test.sh stop 2>/dev/null || true
  $WS/floor3_localize.sh stop 2>/dev/null || true
  echo "Stopped."
}

case "$1" in
  prepare_hci)
    prepare_hci
    ;;
  to_elevator)
    to_elevator
    ;;
  to_hci)
    to_hci
    ;;
  status)
    status_all
    ;;
  zero)
    zero_cmd
    ;;
  stop)
    stop_all
    ;;
  *)
    echo "Usage: $0 {prepare_hci|to_elevator|to_hci|status|zero|stop}"
    echo ""
    echo "Typical workflow:"
    echo "  ./guide_floor3.sh prepare_hci"
    echo "  ./guide_floor3.sh to_elevator"
    echo "  ./guide_floor3.sh zero"
    echo "  ./guide_floor3.sh stop"
    ;;
esac
