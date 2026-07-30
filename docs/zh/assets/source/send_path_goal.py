#!/usr/bin/env python3

import math
import sys
import time
import yaml

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import ComputePathToPose, FollowPath
from tf2_ros import Buffer, TransformListener


def quat_to_yaw(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def yaw_to_quat(yaw):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


class PathGoalClient(Node):
    def __init__(self):
        super().__init__("path_goal_client")
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.compute_client = ActionClient(self, ComputePathToPose, "compute_path_to_pose")
        self.follow_client = ActionClient(self, FollowPath, "follow_path")

    def current_pose(self):
        deadline = time.time() + 8.0
        while time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
            try:
                tf = self.tf_buffer.lookup_transform("map", "base_footprint", rclpy.time.Time())
                x = tf.transform.translation.x
                y = tf.transform.translation.y
                yaw = quat_to_yaw(tf.transform.rotation)
                return x, y, yaw
            except Exception:
                pass
        raise RuntimeError("Failed to get current map -> base_footprint pose")

    def make_pose(self, x, y, yaw):
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(x)
        pose.pose.position.y = float(y)
        pose.pose.position.z = 0.0

        qx, qy, qz, qw = yaw_to_quat(float(yaw))
        pose.pose.orientation.x = qx
        pose.pose.orientation.y = qy
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw
        return pose

    def compute_path(self, goal_pose):
        print("Waiting for compute_path_to_pose action server...")
        if not self.compute_client.wait_for_server(timeout_sec=10.0):
            raise RuntimeError("compute_path_to_pose action server not available")

        goal = ComputePathToPose.Goal()
        goal.pose = goal_pose
        goal.planner_id = "GridBased"

        future = self.compute_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future)
        goal_handle = future.result()

        if not goal_handle.accepted:
            raise RuntimeError("ComputePathToPose goal rejected")

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        result = result_future.result()
        path = result.result.path

        print(f"Computed path poses: {len(path.poses)}")

        if len(path.poses) == 0:
            raise RuntimeError("Computed empty path")

        return path

    def follow_path(self, path):
        print("Waiting for follow_path action server...")
        if not self.follow_client.wait_for_server(timeout_sec=10.0):
            raise RuntimeError("follow_path action server not available")

        goal = FollowPath.Goal()
        goal.path = path
        goal.controller_id = "FollowPath"

        future = self.follow_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future)
        goal_handle = future.result()

        if not goal_handle.accepted:
            raise RuntimeError("FollowPath goal rejected")

        print("FollowPath goal accepted.")
        print("Dry run note: if go2_twist_bridge is not running, robot will not move.")
        print("Controller may later abort due no progress. That is acceptable for dry run.")

        result_future = goal_handle.get_result_async()

        while not result_future.done():
            rclpy.spin_once(self, timeout_sec=0.5)

        result = result_future.result()
        print("FollowPath result status:", result.status)
        return result.status

    def run_relative(self, dx, dy, dyaw):
        x, y, yaw = self.current_pose()

        gx = x + dx * math.cos(yaw) - dy * math.sin(yaw)
        gy = y + dx * math.sin(yaw) + dy * math.cos(yaw)
        gyaw = yaw + dyaw

        print(f"Current pose: x={x:.4f}, y={y:.4f}, yaw={yaw:.6f}")
        print(f"Goal pose:    x={gx:.4f}, y={gy:.4f}, yaw={gyaw:.6f}")

        goal_pose = self.make_pose(gx, gy, gyaw)
        path = self.compute_path(goal_pose)
        return self.follow_path(path)

    def run_anchor(self, semantic_yaml, anchor_name):
        with open(semantic_yaml, "r") as f:
            data = yaml.safe_load(f)

        pose = data["anchors"][anchor_name]["pose"]

        print(f"Goal anchor: {anchor_name}")
        print(f"x={pose['x']}, y={pose['y']}, yaw={pose['yaw']}")

        goal_pose = self.make_pose(float(pose["x"]), float(pose["y"]), float(pose["yaw"]))
        path = self.compute_path(goal_pose)
        return self.follow_path(path)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  send_path_goal.py relative dx dy dyaw")
        print("  send_path_goal.py anchor semantic.yaml anchor_name")
        sys.exit(1)

    rclpy.init()
    node = PathGoalClient()

    try:
        mode = sys.argv[1]

        if mode == "relative":
            if len(sys.argv) != 5:
                print("Usage: send_path_goal.py relative dx dy dyaw")
                sys.exit(1)
            node.run_relative(float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]))

        elif mode == "anchor":
            if len(sys.argv) != 4:
                print("Usage: send_path_goal.py anchor semantic.yaml anchor_name")
                sys.exit(1)
            node.run_anchor(sys.argv[2], sys.argv[3])

        else:
            print("Unknown mode:", mode)
            sys.exit(1)

    except KeyboardInterrupt:
        print("Interrupted.")
    except Exception as e:
        print("ERROR:", e)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
