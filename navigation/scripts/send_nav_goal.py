#!/usr/bin/env python3

import math
import sys
import time
import yaml

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from nav2_msgs.action import NavigateToPose
from tf2_ros import Buffer, TransformListener


def quat_to_yaw(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def yaw_to_quat(yaw):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


class NavGoalClient(Node):
    def __init__(self):
        super().__init__("nav_goal_client")
        self.client = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

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

    def send_goal(self, x, y, yaw):
        print("Waiting for navigate_to_pose action server...")
        if not self.client.wait_for_server(timeout_sec=10.0):
            raise RuntimeError("navigate_to_pose action server not available")

        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(x)
        goal.pose.pose.position.y = float(y)
        goal.pose.pose.position.z = 0.0

        qx, qy, qz, qw = yaw_to_quat(float(yaw))
        goal.pose.pose.orientation.x = qx
        goal.pose.pose.orientation.y = qy
        goal.pose.pose.orientation.z = qz
        goal.pose.pose.orientation.w = qw

        print("")
        print("Sending goal:")
        print(f"  x: {x:.4f}")
        print(f"  y: {y:.4f}")
        print(f"  yaw: {yaw:.6f}")
        print("")

        future = self.client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future)
        goal_handle = future.result()

        if not goal_handle.accepted:
            print("Goal rejected.")
            return 1

        print("Goal accepted.")
        result_future = goal_handle.get_result_async()

        while not result_future.done():
            rclpy.spin_once(self, timeout_sec=0.5)

        result = result_future.result()
        print("Navigation result status:", result.status)
        return result.status


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  send_nav_goal.py relative dx dy dyaw")
        print("  send_nav_goal.py anchor semantic.yaml anchor_name")
        sys.exit(1)

    rclpy.init()
    node = NavGoalClient()

    try:
        mode = sys.argv[1]

        if mode == "relative":
            if len(sys.argv) != 5:
                print("Usage: send_nav_goal.py relative dx dy dyaw")
                sys.exit(1)

            dx = float(sys.argv[2])
            dy = float(sys.argv[3])
            dyaw = float(sys.argv[4])

            x, y, yaw = node.current_pose()
            gx = x + dx * math.cos(yaw) - dy * math.sin(yaw)
            gy = y + dx * math.sin(yaw) + dy * math.cos(yaw)
            gyaw = yaw + dyaw

            print(f"Current pose: x={x:.4f}, y={y:.4f}, yaw={yaw:.6f}")
            status = node.send_goal(gx, gy, gyaw)

        elif mode == "anchor":
            if len(sys.argv) != 4:
                print("Usage: send_nav_goal.py anchor semantic.yaml anchor_name")
                sys.exit(1)

            yaml_path = sys.argv[2]
            anchor_name = sys.argv[3]

            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)

            pose = data["anchors"][anchor_name]["pose"]
            status = node.send_goal(float(pose["x"]), float(pose["y"]), float(pose["yaw"]))

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
