#!/usr/bin/env python3

import math
import sys
import time
from pathlib import Path

import yaml
import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped


def main():
    if len(sys.argv) != 3:
        print("Usage: publish_initialpose_from_semantic.py semantic_yaml anchor_name")
        sys.exit(1)

    semantic_path = Path(sys.argv[1])
    anchor = sys.argv[2]

    data = yaml.safe_load(semantic_path.read_text())
    if anchor not in data["anchors"]:
        print(f"ERROR: anchor not found: {anchor}")
        print("Available:", list(data["anchors"].keys()))
        sys.exit(2)

    pose = data["anchors"][anchor]["pose"]
    x = float(pose["x"])
    y = float(pose["y"])
    yaw = float(pose["yaw"])

    rclpy.init()
    node = rclpy.create_node("publish_initialpose_from_semantic")
    pub = node.create_publisher(PoseWithCovarianceStamped, "/initialpose", 10)

    msg = PoseWithCovarianceStamped()
    msg.header.frame_id = "map"
    msg.pose.pose.position.x = x
    msg.pose.pose.position.y = y
    msg.pose.pose.position.z = 0.0
    msg.pose.pose.orientation.z = math.sin(yaw / 2.0)
    msg.pose.pose.orientation.w = math.cos(yaw / 2.0)

    cov = [0.0] * 36
    cov[0] = 0.6 * 0.6
    cov[7] = 0.6 * 0.6
    cov[35] = 0.4 * 0.4
    msg.pose.covariance = cov

    print(f"Publishing initialpose from {anchor}: x={x}, y={y}, yaw={yaw}")

    time.sleep(1.0)
    for i in range(10):
        msg.header.stamp = node.get_clock().now().to_msg()
        pub.publish(msg)
        print(f"published {i+1}/10")
        rclpy.spin_once(node, timeout_sec=0.1)
        time.sleep(0.2)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
