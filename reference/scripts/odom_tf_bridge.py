#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster


class OdomTFBridge(Node):
    def __init__(self):
        super().__init__("odom_tf_bridge")

        self.odom_pub = self.create_publisher(Odometry, "/odom", 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.static_tf_broadcaster = StaticTransformBroadcaster(self)

        self.publish_static_base_tf()

        self.sub = self.create_subscription(
            Odometry,
            "/utlidar/robot_odom",
            self.odom_callback,
            20
        )

        self.get_logger().info(
            "odom_tf_bridge started: /utlidar/robot_odom -> /odom + TF odom->base_footprint->base_link"
        )

    def publish_static_base_tf(self):
        # 静态 TF: base_footprint -> base_link
        # 这里先设为单位变换。后面如果要更精确，可以再根据机器狗 URDF 调整 z 偏移。
        tf_msg = TransformStamped()
        tf_msg.header.stamp = self.get_clock().now().to_msg()
        tf_msg.header.frame_id = "base_footprint"
        tf_msg.child_frame_id = "base_link"

        tf_msg.transform.translation.x = 0.0
        tf_msg.transform.translation.y = 0.0
        tf_msg.transform.translation.z = 0.0

        tf_msg.transform.rotation.x = 0.0
        tf_msg.transform.rotation.y = 0.0
        tf_msg.transform.rotation.z = 0.0
        tf_msg.transform.rotation.w = 1.0

        self.static_tf_broadcaster.sendTransform(tf_msg)

    def odom_callback(self, msg: Odometry):
        now_stamp = self.get_clock().now().to_msg()

        # 1. 发布标准 /odom
        # 这里 child_frame_id 改成 base_footprint，让 slam_toolbox 即使使用 base_footprint 也能工作
        msg.header.stamp = now_stamp
        msg.header.frame_id = "odom"
        msg.child_frame_id = "base_footprint"
        self.odom_pub.publish(msg)

        # 2. 动态 TF: odom -> base_footprint
        tf_msg = TransformStamped()
        tf_msg.header.stamp = now_stamp
        tf_msg.header.frame_id = "odom"
        tf_msg.child_frame_id = "base_footprint"

        tf_msg.transform.translation.x = msg.pose.pose.position.x
        tf_msg.transform.translation.y = msg.pose.pose.position.y
        tf_msg.transform.translation.z = msg.pose.pose.position.z
        tf_msg.transform.rotation = msg.pose.pose.orientation

        self.tf_broadcaster.sendTransform(tf_msg)


def main():
    rclpy.init()
    node = OdomTFBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
