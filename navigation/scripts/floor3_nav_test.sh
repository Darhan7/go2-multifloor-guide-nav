#!/bin/bash

set -e

WS=/home/unitree/go2_nav_official_ws
PROJECT=/home/unitree/go2_guide_project
NAV_CFG=$PROJECT/navigation/config/nav2_foxy_floor3.yaml
SEMANTIC=$PROJECT/semantic/floor_3_semantic.yaml
LOG_DIR=$PROJECT/navigation/logs/floor_3

source_ros() {
  source /opt/ros/foxy/setup.bash
  source /home/unitree/graph_pid_ws/install/setup.bash
  source /home/unitree/go2_nav_official_ws/install/setup.bash
}

make_dirs() {
  mkdir -p "$LOG_DIR"
}

start_nav() {
  make_dirs
  source_ros

  echo "Starting Nav2 planner/controller nodes without bt_navigator..."

  echo "[1/3] controller_server"
  nohup ros2 run nav2_controller controller_server --ros-args \
    --params-file $NAV_CFG \
    > $LOG_DIR/controller_server.log 2>&1 &
  echo $! > $LOG_DIR/controller_server.pid

  sleep 1

  echo "[2/3] planner_server"
  nohup ros2 run nav2_planner planner_server --ros-args \
    -r __node:=planner_server \
    --params-file $NAV_CFG \
    > $LOG_DIR/planner_server.log 2>&1 &
  echo $! > $LOG_DIR/planner_server.pid

  sleep 2

  echo "[3/3] lifecycle_manager_path"
  nohup ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args \
    -r __node:=lifecycle_manager_path \
    -p use_sim_time:=false \
    -p autostart:=true \
    -p node_names:="[controller_server,planner_server]" \
    > $LOG_DIR/lifecycle_manager_path.log 2>&1 &
  echo $! > $LOG_DIR/lifecycle_manager_path.pid

  echo ""
  echo "Nav2 path stack started."
  echo "Wait 10 seconds, then run:"
  echo "  $0 status"
}

status_nav() {
  source_ros

  echo "========== nav2 nodes =========="
  ros2 node list | grep -E "controller|planner|costmap|lifecycle" || true

  echo ""
  echo "========== lifecycle states =========="
  ros2 lifecycle get /controller_server || true
  ros2 lifecycle get /planner_server || true

  echo ""
  echo "========== actions =========="
  ros2 action list | grep -E "compute_path|follow_path|navigate" || true

  echo ""
  echo "========== /cmd_vel info =========="
  ros2 topic info /cmd_vel || true

  echo ""
  echo "========== tf map -> base_footprint =========="
  timeout 4s ros2 run tf2_ros tf2_echo map base_footprint || true
}

goal_short() {
  source_ros
  python3 $WS/scripts/send_path_goal.py relative 0.60 0.0 0.0
}

goal_elevator() {
  source_ros
  python3 $WS/scripts/send_path_goal.py anchor $SEMANTIC elevator_3f_wait
}

goal_hci() {
  source_ros
  python3 $WS/scripts/send_path_goal.py anchor $SEMANTIC hci_lab_view
}

start_bridge() {
  make_dirs
  source_ros

  echo "Available go2_twist_bridge executables:"
  ros2 pkg executables go2_twist_bridge || true

  echo ""
  echo "Trying: ros2 run go2_twist_bridge twist_bridge"
  nohup ros2 run go2_twist_bridge twist_bridge \
    > $LOG_DIR/go2_twist_bridge.log 2>&1 &
  echo $! > $LOG_DIR/go2_twist_bridge.pid

  sleep 2
  echo "Bridge started. Check logs with:"
  echo "  $0 logs"
}

zero_cmd() {
  source_ros
  ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
}

watch_cmd() {
  source_ros
  timeout 10s ros2 topic echo /cmd_vel || true
}

logs_nav() {
  make_dirs

  echo "========== controller_server.log =========="
  tail -n 100 $LOG_DIR/controller_server.log 2>/dev/null || true

  echo ""
  echo "========== planner_server.log =========="
  tail -n 100 $LOG_DIR/planner_server.log 2>/dev/null || true

  echo ""
  echo "========== lifecycle_manager_path.log =========="
  tail -n 100 $LOG_DIR/lifecycle_manager_path.log 2>/dev/null || true

  echo ""
  echo "========== go2_twist_bridge.log =========="
  tail -n 100 $LOG_DIR/go2_twist_bridge.log 2>/dev/null || true
}

stop_nav() {
  make_dirs
  source_ros

  echo "Publishing zero cmd_vel..."
  ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" || true

  echo "Stopping bridge and Nav2 path stack..."

  for f in \
    $LOG_DIR/go2_twist_bridge.pid \
    $LOG_DIR/lifecycle_manager_path.pid \
    $LOG_DIR/planner_server.pid \
    $LOG_DIR/controller_server.pid
  do
    if [ -f "$f" ]; then
      pid=$(cat "$f")
      if ps -p "$pid" > /dev/null 2>&1; then
        kill "$pid" || true
        echo "Stopped $(basename "$f") pid=$pid"
      fi
    fi
  done

  sleep 1

  pkill -f "go2_twist_bridge" 2>/dev/null || true
  pkill -f "controller_server" 2>/dev/null || true
  pkill -f "planner_server" 2>/dev/null || true
  pkill -f "lifecycle_manager_path" 2>/dev/null || true

  echo "Stopped Nav2 path stack."
}

case "$1" in
  start)
    start_nav
    ;;
  status)
    status_nav
    ;;
  goal_short)
    goal_short
    ;;
  goal_elevator)
    goal_elevator
    ;;
  goal_hci)
    goal_hci
    ;;
  bridge)
    start_bridge
    ;;
  zero)
    zero_cmd
    ;;
  watch_cmd)
    watch_cmd
    ;;
  logs)
    logs_nav
    ;;
  stop)
    stop_nav
    ;;
  *)
    echo "Usage: $0 {start|status|goal_short|goal_elevator|goal_hci|bridge|zero|watch_cmd|logs|stop}"
    ;;
esac
