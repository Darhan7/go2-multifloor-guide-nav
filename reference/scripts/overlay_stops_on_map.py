#!/usr/bin/env python3

import csv
import math
import sys
import yaml


def angle_diff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def circular_mean(angles):
    s = sum(math.sin(a) for a in angles)
    c = sum(math.cos(a) for a in angles)
    return math.atan2(s, c)


def read_pgm(path):
    with open(path, "rb") as f:
        magic = f.readline().strip()
        if magic != b"P5":
            raise RuntimeError("Only P5 PGM is supported")

        line = f.readline()
        while line.startswith(b"#"):
            line = f.readline()

        width, height = map(int, line.split())
        maxval = int(f.readline().strip())
        if maxval != 255:
            raise RuntimeError("Only maxval=255 is supported")

        data = bytearray(f.read())

    rgb = bytearray()
    for v in data:
        rgb.extend([v, v, v])

    return width, height, rgb


def save_ppm(path, width, height, rgb):
    with open(path, "wb") as f:
        f.write(f"P6\n{width} {height}\n255\n".encode())
        f.write(rgb)


def map_to_pixel(x, y, resolution, origin, height):
    ox, oy, _ = origin
    px = int((x - ox) / resolution)
    py = int(height - 1 - (y - oy) / resolution)
    return px, py


def set_pixel(rgb, width, height, x, y, color):
    if 0 <= x < width and 0 <= y < height:
        idx = (y * width + x) * 3
        rgb[idx:idx+3] = bytes(color)


def draw_circle(rgb, width, height, cx, cy, r, color):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r ** 2:
                set_pixel(rgb, width, height, x, y, color)


def draw_line(rgb, width, height, x0, y0, x1, y1, color):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy

    while True:
        set_pixel(rgb, width, height, x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def load_pose_csv(csv_path):
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
    return rows


def detect_stops(rows):
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

    stops = []
    idx = 0
    for g in groups:
        duration = g[-1]["t"] - g[0]["t"]
        if duration < min_duration:
            continue

        xs = [p["x"] for p in g]
        ys = [p["y"] for p in g]
        yaws = [p["yaw"] for p in g]

        stops.append({
            "idx": idx,
            "duration": duration,
            "start": g[0]["t"],
            "end": g[-1]["t"],
            "x": sum(xs) / len(xs),
            "y": sum(ys) / len(ys),
            "yaw": circular_mean(yaws),
        })
        idx += 1

    return stops


def main():
    if len(sys.argv) != 5:
        print("Usage: overlay_stops_on_map.py map.yaml map.pgm pose.csv output.ppm")
        sys.exit(1)

    yaml_path, pgm_path, pose_csv, out_path = sys.argv[1:5]

    with open(yaml_path, "r") as f:
        meta = yaml.safe_load(f)

    resolution = float(meta["resolution"])
    origin = meta["origin"]
    origin = [float(origin[0]), float(origin[1]), float(origin[2]) if len(origin) > 2 else 0.0]

    width, height, rgb = read_pgm(pgm_path)
    rows = load_pose_csv(pose_csv)
    stops = detect_stops(rows)

    # 红色轨迹
    points = []
    for r in rows:
        px, py = map_to_pixel(r["x"], r["y"], resolution, origin, height)
        points.append((px, py))

    for i in range(1, len(points)):
        draw_line(rgb, width, height, points[i-1][0], points[i-1][1], points[i][0], points[i][1], (255, 0, 0))

    # 绿色停留点
    print("Detected stop segments:")
    print("idx,duration_sec,start_time,end_time,mean_x,mean_y,mean_yaw,yaw_deg,pixel_x,pixel_y")
    for s in stops:
        px, py = map_to_pixel(s["x"], s["y"], resolution, origin, height)
        draw_circle(rgb, width, height, px, py, 8, (0, 255, 0))

        # 朝向小线，蓝色
        arrow_len = 22
        px2 = int(px + arrow_len * math.cos(s["yaw"]))
        py2 = int(py - arrow_len * math.sin(s["yaw"]))
        draw_line(rgb, width, height, px, py, px2, py2, (0, 0, 255))

        print(
            f"{s['idx']},"
            f"{s['duration']:.1f},"
            f"{s['start']:.3f},"
            f"{s['end']:.3f},"
            f"{s['x']:.4f},"
            f"{s['y']:.4f},"
            f"{s['yaw']:.6f},"
            f"{math.degrees(s['yaw']):.2f},"
            f"{px},"
            f"{py}"
        )

    save_ppm(out_path, width, height, rgb)
    print("saved:", out_path)


if __name__ == "__main__":
    main()
