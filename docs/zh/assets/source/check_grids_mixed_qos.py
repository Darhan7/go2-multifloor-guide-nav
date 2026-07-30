#!/usr/bin/env python3
import sys, time
import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

def qos_for(topic):
    durability = DurabilityPolicy.TRANSIENT_LOCAL if topic == "/map" else DurabilityPolicy.VOLATILE
    return QoSProfile(
        history=HistoryPolicy.KEEP_LAST,
        depth=1,
        reliability=ReliabilityPolicy.RELIABLE,
        durability=durability,
    )

class N(Node):
    def __init__(self, topic):
        super().__init__("check_grid_once")
        self.msg = None
        self.sub = self.create_subscription(OccupancyGrid, topic, self.cb, qos_for(topic))
    def cb(self, msg):
        self.msg = msg

def read(topic, timeout=12.0):
    rclpy.init()
    n = N(topic)
    t0 = time.time()
    while time.time() - t0 < timeout and n.msg is None:
        rclpy.spin_once(n, timeout_sec=0.1)
    msg = n.msg
    n.destroy_node()
    rclpy.shutdown()
    if msg is None:
        raise RuntimeError(f"no message from {topic}")
    return msg

def show(topic, msg):
    data = list(msg.data)
    total = len(data)
    occ = sum(1 for v in data if v >= 65)
    free = sum(1 for v in data if v == 0)
    unk = sum(1 for v in data if v < 0)
    mid = sum(1 for v in data if 1 <= v < 65)
    print(f"========== {topic} ==========")
    print(f"frame_id: {msg.header.frame_id}")
    print(f"size: {msg.info.width} x {msg.info.height}")
    print(f"resolution: {msg.info.resolution}")
    print(f"origin: {msg.info.origin.position.x}, {msg.info.origin.position.y}")
    print(f"occupied>=65: {occ} ({occ/total*100:.2f}%)")
    print(f"free=0: {free} ({free/total*100:.2f}%)")
    print(f"unknown=-1: {unk} ({unk/total*100:.2f}%)")
    print(f"mid=1~64: {mid} ({mid/total*100:.2f}%)")
    print(f"min/max: {min(data)} / {max(data)}")

for topic in sys.argv[1:]:
    try:
        show(topic, read(topic))
    except Exception as e:
        print(f"ERROR reading {topic}: {e}")
