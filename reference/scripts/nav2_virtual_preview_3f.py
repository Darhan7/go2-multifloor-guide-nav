#!/usr/bin/env python3

import csv
import math
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import ComputePathToPose


MAP_YAML = Path("/home/unitree/go2_guide_project/maps/floor_3/floor_3.yaml")
SEMANTIC_YAML = Path("/home/unitree/go2_guide_project/semantic/floor_3_semantic.yaml")
OUT_DIR = Path("/home/unitree/go2_nav_official_ws/debug_routes")


def yaw_to_quat(yaw):
    return math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def yaw_from_q(q):
    return math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y * q.y + q.z * q.z),
    )


def load_anchor(name):
    data = yaml.safe_load(SEMANTIC_YAML.read_text())
    if name not in data["anchors"]:
        raise RuntimeError(f"anchor not found: {name}. Available: {list(data['anchors'].keys())}")
    p = data["anchors"][name]["pose"]
    return float(p["x"]), float(p["y"]), float(p["yaw"])


def load_map_info():
    m = yaml.safe_load(MAP_YAML.read_text())
    img_path = Path(m["image"])
    if not img_path.is_absolute():
        img_path = MAP_YAML.parent / img_path
    return img_path, float(m["resolution"]), m["origin"]


def world_to_img(x, y, origin, resolution, height):
    u = int(round((x - origin[0]) / resolution))
    v = int(round(height - 1 - (y - origin[1]) / resolution))
    return u, v


class PlannerClient(Node):
    def __init__(self):
        super().__init__("nav2_virtual_preview_3f")
        self.client = ActionClient(self, ComputePathToPose, "compute_path_to_pose")

    def compute(self, gx, gy, gyaw):
        if not self.client.wait_for_server(timeout_sec=15.0):
            raise RuntimeError("compute_path_to_pose action server not available")

        goal_pose = PoseStamped()
        goal_pose.header.frame_id = "map"
        goal_pose.header.stamp = self.get_clock().now().to_msg()
        goal_pose.pose.position.x = gx
        goal_pose.pose.position.y = gy
        goal_pose.pose.position.z = 0.0
        qz, qw = yaw_to_quat(gyaw)
        goal_pose.pose.orientation.z = qz
        goal_pose.pose.orientation.w = qw

        goal = ComputePathToPose.Goal()
        goal.pose = goal_pose
        goal.planner_id = "GridBased"

        fut = self.client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut)
        gh = fut.result()
        if not gh or not gh.accepted:
            raise RuntimeError("planner rejected goal")

        rf = gh.get_result_async()
        rclpy.spin_until_future_complete(self, rf)
        result = rf.result().result
        return result.path


def draw_overlay(path, start_name, sx, sy, goal_name, gx, gy, out_png):
    try:
        import cv2
    except Exception as e:
        print("ERROR: cv2 not available, cannot draw png:", e)
        return

    img_path, resolution, origin = load_map_info()
    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError(f"cannot read map image: {img_path}")

    h, w = img.shape[:2]
    color = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    pts = []
    for ps in path.poses:
        u, v = world_to_img(ps.pose.position.x, ps.pose.position.y, origin, resolution, h)
        if 0 <= u < w and 0 <= v < h:
            pts.append((u, v))

    # red planned path
    for a, b in zip(pts[:-1], pts[1:]):
        cv2.line(color, a, b, (0, 0, 255), 2)

    # blue start
    su, sv = world_to_img(sx, sy, origin, resolution, h)
    if 0 <= su < w and 0 <= sv < h:
        cv2.circle(color, (su, sv), 7, (255, 0, 0), -1)
        cv2.putText(color, f"START:{start_name}", (su + 8, sv), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 0), 1)

    # green goal
    gu, gv = world_to_img(gx, gy, origin, resolution, h)
    if 0 <= gu < w and 0 <= gv < h:
        cv2.circle(color, (gu, gv), 7, (0, 255, 0), -1)
        cv2.putText(color, f"GOAL:{goal_name}", (gu + 8, gv), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 160, 0), 1)

    cv2.putText(color, "RED = Nav2 planned path", (20, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)
    cv2.putText(color, "BLUE = virtual start", (20, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 0, 0), 2)
    cv2.putText(color, "GREEN = goal", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 160, 0), 2)

    cv2.imwrite(str(out_png), color)


def main():
    if len(sys.argv) != 3:
        print("Usage: nav2_virtual_preview_3f.py <start_anchor> <goal_anchor>")
        print("Example:")
        print("  python3 scripts/nav2_virtual_preview_3f.py hci_lab_view elevator_3f_safe")
        sys.exit(1)

    start_anchor = sys.argv[1]
    goal_anchor = sys.argv[2]

    sx, sy, syaw = load_anchor(start_anchor)
    gx, gy, gyaw = load_anchor(goal_anchor)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = OUT_DIR / f"{stamp}_virtual_{start_anchor}_to_{goal_anchor}"

    print("========== virtual start ==========")
    print(f"{start_anchor}: x={sx:.4f}, y={sy:.4f}, yaw={syaw:.6f}")
    print("========== goal ==========")
    print(f"{goal_anchor}: x={gx:.4f}, y={gy:.4f}, yaw={gyaw:.6f}")

    # Publish fake static TF: map -> base_footprint
    # This is the virtual robot pose that Nav2 planner will use as current robot pose.
    tf_cmd = [
        "ros2", "run", "tf2_ros", "static_transform_publisher",
        str(sx), str(sy), "0.0",
        str(syaw), "0.0", "0.0",
        "map", "base_footprint"
    ]

    print("========== starting fake TF ==========")
    print(" ".join(tf_cmd))
    tf_proc = subprocess.Popen(tf_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        time.sleep(2.0)

        rclpy.init()
        node = PlannerClient()
        path = node.compute(gx, gy, gyaw)
        node.destroy_node()
        rclpy.shutdown()

        print("========== Nav2 planned path ==========")
        print(f"poses={len(path.poses)}")

        out_csv = prefix.with_suffix(".csv")
        with out_csv.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["x", "y", "yaw"])
            for ps in path.poses:
                w.writerow([
                    ps.pose.position.x,
                    ps.pose.position.y,
                    yaw_from_q(ps.pose.orientation),
                ])

        out_png = prefix.with_suffix(".png")
        draw_overlay(path, start_anchor, sx, sy, goal_anchor, gx, gy, out_png)

        print("========== saved ==========")
        print(out_csv)
        print(out_png)

    finally:
        try:
            os.kill(tf_proc.pid, signal.SIGTERM)
        except Exception:
            pass


if __name__ == "__main__":
    main()
