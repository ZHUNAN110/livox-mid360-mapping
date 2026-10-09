#!/usr/bin/env python3
"""把 PGM+YAML 地图发布为 ROS2 的 nav_msgs/OccupancyGrid 消息（/map 话题）。

用法（先 source ROS2 环境）：
    source /opt/ros/humble/setup.bash
    python3 occupancy_grid_publisher.py /path/to/map.yaml

这是一个精简版 map_server：nav2_map_server 未安装时用它即可。
发布采用 TRANSIENT_LOCAL（latched），后订阅者也能收到完整地图。
"""
import os
import sys
import yaml
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import Pose


def load_pgm(path):
    """读取 P5 格式（8bit 灰度）PGM，返回 (二维数组, 宽, 高)。行 0 = 图像顶部。"""
    raw = open(path, "rb").read()
    parts = raw.split(b"\n", 3)  # [P5, "w h", "maxval", 数据...]
    assert parts[0] == b"P5", f"不是 P5 格式的 PGM: {path}"
    w, h = map(int, parts[1].split())
    maxval = int(parts[2])
    data = np.frombuffer(parts[3], dtype=np.uint8, count=w * h).reshape(h, w)
    return data, w, h


class OccupancyGridPublisher(Node):
    def __init__(self, yaml_path):
        super().__init__("occupancy_grid_publisher")

        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub = self.create_publisher(OccupancyGrid, "/map", qos)

        # 读 YAML + PGM
        with open(yaml_path) as f:
            cfg = yaml.safe_load(f)
        pgm_path = os.path.join(os.path.dirname(os.path.abspath(yaml_path)),
                                cfg["image"])
        img, w, h = load_pgm(pgm_path)

        # 像素值 -> 占据值：黑(0)=障碍100，白(254)=自由0，灰(205)=未知-1
        occ = np.full(img.shape, -1, dtype=np.int8)
        occ[img == 0] = 100
        occ[img == 254] = 0

        resolution = float(cfg["resolution"])
        ox, oy = float(cfg["origin"][0]), float(cfg["origin"][1])

        self.msg = OccupancyGrid()
        self.msg.header.frame_id = "map"
        self.msg.info.map_load_time = self.get_clock().now().to_msg()
        self.msg.info.resolution = resolution
        self.msg.info.width = w
        self.msg.info.height = h
        self.msg.info.origin = Pose()
        self.msg.info.origin.position.x = ox
        self.msg.info.origin.position.y = oy
        self.msg.info.origin.position.z = 0.0
        self.msg.info.origin.orientation.w = 1.0
        # OccupancyGrid.data 行优先，data[0] = 左上角（与 PGM 顶行一致）
        self.msg.data = occ.flatten().tolist()

        self.get_logger().info(
            f"地图加载完成: {w}x{h} 格, 分辨率 {resolution}m, "
            f"origin=({ox}, {oy})")

        # 稍等一下再发一次并保持运行（latched，后订阅者也能收到）
        self.timer = self.create_timer(1.0, self.publish_once)

    def publish_once(self):
        self.msg.header.stamp = self.get_clock().now().to_msg()
        self.pub.publish(self.msg)
        self.get_logger().info("已发布 OccupancyGrid 到 /map")
        self.destroy_timer(self.timer)  # 发一次即可，继续 spin


def main():
    rclpy.init()
    yaml_path = sys.argv[1] if len(sys.argv) > 1 else (
        os.path.expanduser(
            "~/livox_ws/catkin_point_lio_unilidar/src/point_lio_ros2/PCD/map/map.yaml"))
    node = OccupancyGridPublisher(yaml_path)
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
