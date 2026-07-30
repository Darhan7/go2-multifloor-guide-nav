#!/usr/bin/env python3

import sys
import time
import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy


class GridCheck(Node):
    def __init__(self, topic):
        super().__init__("grid_check_qos")
        self.msg = None

        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        self.sub = self.create_subscription(OccupancyGrid, topic, self.cb, qos)

    def cb(self, msg):
        self.msg = msg


def summarize(name, msg):
    data = list(msg.data)
    total = len(data)

    unknown = sum(1 for v in data if v < 0)
    free = sum(1 for v in data if v == 0)
    occupied = sum(1 for v in data if v >= 65)
    mid = sum(1 for v in data if 1 <= v < 65)

    print(f"========== {name} ==========")
    print(f"frame_id: {msg.header.frame_id}")
    print(f"width x height: {msg.info.width} x {msg.info.height}")
    print(f"resolution: {msg.info.resolution}")
    print(f"origin: x={msg.info.origin.position.x}, y={msg.info.origin.position.y}")
    print(f"total cells: {total}")
    print(f"unknown(-1): {unknown} ({unknown / total * 100:.2f}%)")
    print(f"free(0): {free} ({free / total * 100:.2f}%)")
    print(f"occupied(>=65): {occupied} ({occupied / total * 100:.2f}%)")
    print(f"mid(1~64): {mid} ({mid / total * 100:.2f}%)")
    print(f"min/max: {min(data)} / {max(data)}")


def get_grid(topic, timeout=10.0):
    rclpy.init()
    node = GridCheck(topic)

    start = time.time()
    while time.time() - start < timeout and node.msg is None:
        rclpy.spin_once(node, timeout_sec=0.1)

    msg = node.msg
    node.destroy_node()
    rclpy.shutdown()

    if msg is None:
        raise RuntimeError(f"no message received from {topic}")
    return msg


def main():
    topics = sys.argv[1:] if len(sys.argv) > 1 else ["/map", "/global_costmap/costmap"]
    for topic in topics:
        try:
            msg = get_grid(topic)
            summarize(topic, msg)
        except Exception as e:
            print(f"ERROR reading {topic}: {e}")


if __name__ == "__main__":
    main()
