#!/bin/bash

set -e

WS=/home/unitree/go2_nav_official_ws
PROJECT=/home/unitree/go2_guide_project

MAP=$PROJECT/maps/floor_3/floor_3.yaml
SEMANTIC=$PROJECT/semantic/floor_3_semantic.yaml
AMCL_CFG=$PROJECT/localization/config/amcl_foxy.yaml
LOG_DIR=$PROJECT/localization/logs/floor_3

source_ros() {
  source /opt/ros/foxy/setup.bash
  source /home/unitree/graph_pid_ws/install/setup.bash
  source /home/unitree/go2_nav_official_ws/install/setup.bash
}

make_dirs() {
  mkdir -p "$LOG_DIR"
}

start_stack() {
  make_dirs
  source_ros

  echo "[1/5] Starting odom_tf_bridge..."
  nohup python3 $WS/scripts/odom_tf_bridge.py \
    > $LOG_DIR/odom_tf_bridge.log 2>&1 &
  echo $! > $LOG_DIR/odom_tf_bridge.pid

  sleep 2

  echo "[2/5] Starting pointcloud_to_laserscan..."
  nohup ros2 launch go2_perception go2_pointcloud.launch.py \
    > $LOG_DIR/go2_perception.log 2>&1 &
  echo $! > $LOG_DIR/go2_perception.pid

  sleep 3

  echo "[3/5] Starting map_server..."
  nohup ros2 run nav2_map_server map_server --ros-args \
    -p yaml_filename:=$MAP \
    > $LOG_DIR/map_server.log 2>&1 &
  echo $! > $LOG_DIR/map_server.pid

  sleep 2

  echo "[4/5] Starting AMCL..."
  nohup ros2 run nav2_amcl amcl --ros-args \
    --params-file $AMCL_CFG \
    > $LOG_DIR/amcl.log 2>&1 &
  echo $! > $LOG_DIR/amcl.pid

  sleep 2

  echo "[5/5] Starting lifecycle manager..."
  nohup ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args \
    -p use_sim_time:=false \
    -p autostart:=true \
    -p node_names:="[map_server, amcl]" \
    > $LOG_DIR/lifecycle_manager.log 2>&1 &
  echo $! > $LOG_DIR/lifecycle_manager.pid

  echo ""
  echo "floor_3 localization stack started."
  echo "Next:"
  echo "  $0 status"
  echo "  $0 init_hci"
}

init_hci() {
  source_ros
  python3 $WS/scripts/publish_initial_pose_from_yaml.py \
    $SEMANTIC hci_lab_view
}

init_elevator() {
  source_ros
  python3 $WS/scripts/publish_initial_pose_from_yaml.py \
    $SEMANTIC elevator_3f_wait
}

status_stack() {
  source_ros

  echo "========== nodes =========="
  ros2 node list | grep -E "map_server|amcl|lifecycle|odom_tf|pointcloud" || true

  echo ""
  echo "========== topics =========="
  ros2 topic list | grep -E "^/map$|^/scan$|^/odom$|^/tf$|^/amcl_pose$|^/particle_cloud$" || true

  echo ""
  echo "========== /scan hz =========="
  timeout 5s ros2 topic hz /scan || true

  echo ""
  echo "========== /map info =========="
  ros2 topic info /map || true

  echo ""
  echo "========== /amcl_pose sample =========="
  timeout 5s ros2 topic echo /amcl_pose || true

  echo ""
  echo "========== tf map -> base_footprint =========="
  timeout 5s ros2 run tf2_ros tf2_echo map base_footprint || true
}

logs_stack() {
  make_dirs

  echo "========== map_server.log =========="
  tail -n 30 $LOG_DIR/map_server.log 2>/dev/null || true

  echo ""
  echo "========== amcl.log =========="
  tail -n 30 $LOG_DIR/amcl.log 2>/dev/null || true

  echo ""
  echo "========== lifecycle_manager.log =========="
  tail -n 30 $LOG_DIR/lifecycle_manager.log 2>/dev/null || true

  echo ""
  echo "========== go2_perception.log =========="
  tail -n 20 $LOG_DIR/go2_perception.log 2>/dev/null || true
}

stop_stack() {
  make_dirs

  echo "Stopping floor_3 localization stack..."

  for f in \
    $LOG_DIR/lifecycle_manager.pid \
    $LOG_DIR/amcl.pid \
    $LOG_DIR/map_server.pid \
    $LOG_DIR/go2_perception.pid \
    $LOG_DIR/odom_tf_bridge.pid
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

  pkill -f "nav2_map_server" 2>/dev/null || true
  pkill -f "nav2_amcl" 2>/dev/null || true
  pkill -f "lifecycle_manager" 2>/dev/null || true
  pkill -f "go2_pointcloud.launch.py" 2>/dev/null || true
  pkill -f "odom_tf_bridge.py" 2>/dev/null || true

  echo "Stopped."
}

case "$1" in
  start)
    start_stack
    ;;
  init_hci)
    init_hci
    ;;
  init_elevator)
    init_elevator
    ;;
  status)
    status_stack
    ;;
  logs)
    logs_stack
    ;;
  stop)
    stop_stack
    ;;
  *)
    echo "Usage: $0 {start|init_hci|init_elevator|status|logs|stop}"
    ;;
esac
