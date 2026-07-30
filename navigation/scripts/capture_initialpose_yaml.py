#!/usr/bin/env python3

import math
import sys
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped


def quat_to_yaw(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class CaptureInitialPose(Node):
    def __init__(self, anchor_name):
        super().__init__("capture_initialpose_yaml")
        self.anchor_name = anchor_name
        self.sub = self.create_subscription(
            PoseWithCovarianceStamped,
            "/initialpose",
            self.callback,
            10
        )
        self.get_logger().info("Waiting for RViz 2D Pose Estimate on /initialpose...")

    def callback(self, msg):
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        yaw = quat_to_yaw(msg.pose.pose.orientation)

        print("")
        print("========== COPY THIS YAML ==========")
        print(f"{self.anchor_name}:")
        print("  pose:")
        print(f"    x: {x:.4f}")
        print(f"    y: {y:.4f}")
        print(f"    yaw: {yaw:.6f}")
        print("====================================")
        print("")

        rclpy.shutdown()


def main():
    anchor_name = sys.argv[1] if len(sys.argv) > 1 else "anchor"
    rclpy.init()
    node = CaptureInitialPose(anchor_name)
    rclpy.spin(node)


if __name__ == "__main__":
    main()
