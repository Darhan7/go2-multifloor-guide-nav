#!/usr/bin/env python3

import csv
import math
import sys


def angle_diff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def circular_mean(angles):
    s = sum(math.sin(a) for a in angles)
    c = sum(math.cos(a) for a in angles)
    return math.atan2(s, c)


def main():
    if len(sys.argv) < 2:
        print("Usage: find_stop_segments.py map_pose_log.csv")
        sys.exit(1)

    csv_path = sys.argv[1]

    rows = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "t": float(r["ros_time_sec"]),
                "x": float(r["map_x"]),
                "y": float(r["map_y"]),
                "yaw": float(r["yaw_rad"]),
            })

    if len(rows) < 2:
        print("Not enough pose rows.")
        return

    # 这两个阈值可以微调：
    # 每秒位移小于 3cm，yaw变化小于 0.03rad，就认为基本停住。
    dist_thresh = 0.03
    yaw_thresh = 0.03
    min_duration = 3.0

    groups = []
    current = []

    for i in range(1, len(rows)):
        a = rows[i - 1]
        b = rows[i]

        dist = math.hypot(b["x"] - a["x"], b["y"] - a["y"])
        dyaw = abs(angle_diff(b["yaw"], a["yaw"]))

        stopped = dist < dist_thresh and dyaw < yaw_thresh

        if stopped:
            if not current:
                current.append(a)
            current.append(b)
        else:
            if current:
                groups.append(current)
                current = []

    if current:
        groups.append(current)

    print("Detected stop segments:")
    print("idx,duration_sec,start_time,end_time,mean_x,mean_y,mean_yaw")

    idx = 0
    for g in groups:
        duration = g[-1]["t"] - g[0]["t"]
        if duration < min_duration:
            continue

        xs = [p["x"] for p in g]
        ys = [p["y"] for p in g]
        yaws = [p["yaw"] for p in g]

        mean_x = sum(xs) / len(xs)
        mean_y = sum(ys) / len(ys)
        mean_yaw = circular_mean(yaws)

        print(
            f"{idx},"
            f"{duration:.1f},"
            f"{g[0]['t']:.3f},"
            f"{g[-1]['t']:.3f},"
            f"{mean_x:.4f},"
            f"{mean_y:.4f},"
            f"{mean_yaw:.6f}"
        )
        idx += 1


if __name__ == "__main__":
    main()
