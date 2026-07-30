#!/usr/bin/env python3

import csv
import sys
import yaml


def read_map_yaml(path):
    with open(path, "r") as f:
        meta = yaml.safe_load(f)

    resolution = float(meta["resolution"])
    origin = meta["origin"]

    if not isinstance(origin, list) or len(origin) < 2:
        raise RuntimeError(f"Bad origin format: {origin}")

    origin = [float(origin[0]), float(origin[1]), float(origin[2]) if len(origin) > 2 else 0.0]
    return resolution, origin


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
        rgb[idx:idx + 3] = bytes(color)


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


def main():
    if len(sys.argv) != 5:
        print("Usage: overlay_pose_on_map.py map.yaml map.pgm pose.csv output.ppm")
        sys.exit(1)

    yaml_path, pgm_path, csv_path, out_path = sys.argv[1:5]

    resolution, origin = read_map_yaml(yaml_path)
    width, height, rgb = read_pgm(pgm_path)

    points = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            x = float(row["map_x"])
            y = float(row["map_y"])
            px, py = map_to_pixel(x, y, resolution, origin, height)
            points.append((px, py))

    # 红色轨迹线
    for i in range(1, len(points)):
        draw_line(
            rgb, width, height,
            points[i - 1][0], points[i - 1][1],
            points[i][0], points[i][1],
            (255, 0, 0)
        )

    # 这次 find_stop_segments.py 检出的三个停留点
    stops = [
        ("0_start_or_lab_area", 5.3190, 2.0266),
        ("1_elevator_candidate", -20.1587, -1.0769),
        ("2_end_or_lab_area", 4.3134, 1.4932),
    ]

    # 绿色圆点
    for label, x, y in stops:
        px, py = map_to_pixel(x, y, resolution, origin, height)
        draw_circle(rgb, width, height, px, py, 8, (0, 255, 0))
        print(f"{label}: map=({x:.4f}, {y:.4f}) pixel=({px}, {py})")

    save_ppm(out_path, width, height, rgb)

    print("saved:", out_path)
    print("map size:", width, height)
    print("resolution:", resolution)
    print("origin:", origin)


if __name__ == "__main__":
    main()
