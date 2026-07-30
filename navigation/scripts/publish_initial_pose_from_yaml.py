#!/usr/bin/env python3

import math
import sys
import time
import yaml

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped


def yaw_to_quat(yaw):
    qz = math.sin(yaw / 2.0)
    qw = math.cos(yaw / 2.0)
    return 0.0, 0.0, qz, qw


class InitialPosePublisher(Node):
    def __init__(self, yaml_path, anchor_name):
        super().__init__("initial_pose_publisher")

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        anchor = data["anchors"][anchor_name]
        pose = anchor["pose"]

        self.x = float(pose["x"])
        self.y = float(pose["y"])
        self.yaw = float(pose["yaw"])
        self.anchor_name = anchor_name

        self.pub = self.create_publisher(PoseWithCovarianceStamped, "/initialpose", 10)

    def publish_pose(self):
        msg = PoseWithCovarianceStamped()
        msg.header.frame_id = "map"
        msg.header.stamp = self.get_clock().now().to_msg()

        msg.pose.pose.position.x = self.x
        msg.pose.pose.position.y = self.y
        msg.pose.pose.position.z = 0.0

        qx, qy, qz, qw = yaw_to_quat(self.yaw)
        msg.pose.pose.orientation.x = qx
        msg.pose.pose.orientation.y = qy
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw

        # 初始不确定性：位置约 0.25m，角度约 0.2rad
        msg.pose.covariance[0] = 0.25 * 0.25
        msg.pose.covariance[7] = 0.25 * 0.25
        msg.pose.covariance[35] = 0.20 * 0.20

        for _ in range(10):
            msg.header.stamp = self.get_clock().now().to_msg()
            self.pub.publish(msg)
            time.sleep(0.2)

        print("")
        print("Published initial pose:")
        print(f"  anchor: {self.anchor_name}")
        print(f"  x: {self.x:.4f}")
        print(f"  y: {self.y:.4f}")
        print(f"  yaw: {self.yaw:.6f}")
        print("")


def main():
    if len(sys.argv) != 3:
        print("Usage: publish_initial_pose_from_yaml.py semantic.yaml anchor_name")
        sys.exit(1)

    rclpy.init()
    node = InitialPosePublisher(sys.argv[1], sys.argv[2])
    node.publish_pose()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
