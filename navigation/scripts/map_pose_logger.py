#!/usr/bin/env python3

import math
import csv
import sys
import rclpy
from rclpy.node import Node
from tf2_ros import Buffer, TransformListener


def quat_to_yaw(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class MapPoseLogger(Node):
    def __init__(self, csv_path):
        super().__init__("map_pose_logger")
        self.csv_path = csv_path
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)

        self.file = open(csv_path, "w", newline="")
        self.writer = csv.writer(self.file)
        self.writer.writerow(["ros_time_sec", "map_x", "map_y", "yaw_rad"])

        self.timer = self.create_timer(1.0, self.on_timer)
        self.get_logger().info(f"logging map->base_footprint pose to {csv_path}")

    def on_timer(self):
        try:
            tf = self.buffer.lookup_transform(
                "map",
                "base_footprint",
                rclpy.time.Time()
            )
            t = self.get_clock().now().nanoseconds / 1e9
            x = tf.transform.translation.x
            y = tf.transform.translation.y
            yaw = quat_to_yaw(tf.transform.rotation)

            self.writer.writerow([
                f"{t:.3f}",
                f"{x:.4f}",
                f"{y:.4f}",
                f"{yaw:.6f}"
            ])
            self.file.flush()

        except Exception as e:
            self.get_logger().warn(f"pose not available yet: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: map_pose_logger.py output.csv")
        sys.exit(1)

    rclpy.init()
    node = MapPoseLogger(sys.argv[1])

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.file.close()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
