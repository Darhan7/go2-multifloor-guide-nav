#!/usr/bin/env python3

import sys
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class CmdVelTestPub(Node):
    def __init__(self):
        super().__init__("cmd_vel_test_pub")
        self.pub = self.create_publisher(Twist, "/cmd_vel", 10)

    def run(self, vx, vy, wz, duration, rate):
        msg = Twist()
        msg.linear.x = float(vx)
        msg.linear.y = float(vy)
        msg.angular.z = float(wz)

        dt = 1.0 / float(rate)
        n = int(float(duration) * float(rate))

        print(f"Publishing /cmd_vel: vx={vx}, vy={vy}, wz={wz}, duration={duration}s, rate={rate}Hz")

        # 先等订阅关系建立
        time.sleep(1.0)

        for i in range(n):
            self.pub.publish(msg)
            if i % int(rate) == 0:
                print(f"published {i+1}/{n}: vx={msg.linear.x:.3f}, vy={msg.linear.y:.3f}, wz={msg.angular.z:.3f}")
            rclpy.spin_once(self, timeout_sec=0.0)
            time.sleep(dt)

        stop = Twist()
        for _ in range(10):
            self.pub.publish(stop)
            time.sleep(dt)

        print("Done. Published stop command.")


def main():
    if len(sys.argv) != 6:
        print("Usage: pub_cmd_vel_test.py vx vy wz duration_sec rate_hz")
        sys.exit(1)

    rclpy.init()
    node = CmdVelTestPub()
    node.run(float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]))
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
