# livox-mid360-mapping

基于 **Livox Mid-360 激光雷达 + Point-LIO** 的 2D 占据格栅地图（Occupancy Grid Map）建图工程。

环境：Ubuntu 22.04 + ROS2 Humble

## 目录结构

| 目录 | 说明 |
|------|------|
| `src/livox_ros_driver2` | Livox ROS2 驱动源码（Mid-360） |
| `map/` | 2D 占据格栅图产物 `map.pgm` + `map.yaml`，及详细说明 `map/README.md` |
| `scripts/` | 点云 → 2D 地图的处理与发布脚本 |

## 快速开始

完整流程（建图 → 清洗点云 → 降采样 → 生成 2D 地图 → 发布）见 [`map/README.md`](map/README.md)。

- **查看 / 发布地图**：`scripts/occupancy_grid_publisher.py` 把 `map.pgm`+`map.yaml` 发布为 ROS `/map` 话题（`nav_msgs/OccupancyGrid`）
- **重新生成地图**：`scripts/make_2d_map.py` 从 `.pcd` 点云生成 2D 格栅图
- **RViz 查看**：`scripts/map_view.rviz`（已配好俯视图 + `/map` 话题）

```bash
source /opt/ros/humble/setup.bash
python3 scripts/occupancy_grid_publisher.py map/map.yaml   # 发布 /map
rviz2 -d scripts/map_view.rviz                              # 可视化
```

## 最终地图

`map/map.pgm`：1043×846 格，分辨率 0.1 m（约 104.3 m × 84.6 m），障碍 175240 格、可通行 707138 格、未知 0 格。
