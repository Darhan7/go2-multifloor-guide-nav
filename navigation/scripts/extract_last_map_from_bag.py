#!/usr/bin/env python3

import os
import sys
import math
import sqlite3
import yaml

import rclpy
from rclpy.serialization import deserialize_message
from nav_msgs.msg import OccupancyGrid


def quat_to_yaw(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def save_map(msg, out_prefix):
    width = msg.info.width
    height = msg.info.height
    resolution = msg.info.resolution
    origin = msg.info.origin
    yaw = quat_to_yaw(origin.orientation)

    pgm_path = out_prefix + ".pgm"
    yaml_path = out_prefix + ".yaml"

    data = list(msg.data)

    with open(pgm_path, "wb") as f:
        f.write(f"P5\n# CREATOR: extract_last_map_from_bag.py\n{width} {height}\n255\n".encode())

        # ROS map_saver 会把 y 方向翻转，这里也照做
        for y in range(height - 1, -1, -1):
            for x in range(width):
                occ = data[y * width + x]

                if occ < 0:
                    val = 205      # unknown
                elif occ >= 65:
                    val = 0        # occupied, black
                elif occ <= 25:
                    val = 254      # free, white
                else:
                    val = 205      # uncertain

                f.write(bytes([val]))

    meta = {
        "image": os.path.basename(pgm_path),
        "mode": "trinary",
        "resolution": float(resolution),
        "origin": [
            float(origin.position.x),
            float(origin.position.y),
            float(yaw),
        ],
        "negate": 0,
        "occupied_thresh": 0.65,
        "free_thresh": 0.25,
    }

    with open(yaml_path, "w") as f:
        yaml.safe_dump(meta, f, allow_unicode=True, sort_keys=False)

    print("saved:", pgm_path)
    print("saved:", yaml_path)
    print("width:", width)
    print("height:", height)
    print("resolution:", resolution)
    print("origin:", meta["origin"])


def main():
    if len(sys.argv) != 3:
        print("Usage: extract_last_map_from_bag.py BAG_DIR OUT_PREFIX")
        sys.exit(1)

    bag_dir = sys.argv[1]
    out_prefix = sys.argv[2]

    db_files = [f for f in os.listdir(bag_dir) if f.endswith(".db3")]
    if not db_files:
        raise RuntimeError(f"No .db3 file found in {bag_dir}")

    db_path = os.path.join(bag_dir, db_files[0])
    print("reading:", db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id FROM topics WHERE name = '/map'")
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("No /map topic found in bag")

    topic_id = row[0]

    cur.execute(
        "SELECT data, timestamp FROM messages WHERE topic_id = ? ORDER BY timestamp DESC LIMIT 1",
        (topic_id,)
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("No /map messages found in bag")

    raw, timestamp = row
    print("using last /map message timestamp:", timestamp)

    msg = deserialize_message(raw, OccupancyGrid)
    save_map(msg, out_prefix)

    conn.close()


if __name__ == "__main__":
    main()
