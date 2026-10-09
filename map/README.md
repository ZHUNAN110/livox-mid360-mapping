# 二维占据格栅地图（map）

Livox Mid-360 点云 → **2D 占据格栅地图** 的最终产物与使用说明。

## 目录文件

| 文件 | 说明 |
|------|------|
| `map.pgm` | 最终 2D 占据格栅图（1043×846 格，0.1m/格，即 104.3m × 84.6m） |
| `map.yaml` | 地图配置：分辨率、原点、阈值（供 map_server / 发布节点读取） |
| `map_preview.png` / `map_preview.jpg` | 地图预览图（黑=墙/障碍，白=可通行） |
| `map_clear.png` | 放大 3 倍的彩色预览图，直观查看用 |
| `scans_height.pcd` | Z 轴直通滤波后的中间点云（可删，仅存档） |
| 其余 `preview_*.png`、`map_small.png`、`map_check.png` | 调试过程图，可删 |

上级目录 `../`（`PCD/`）里是点云中间产物：`scans.pcd`（原始）→ `scans_filtered_bin.pcd`（SOR 清洗）→ `scans_voxel*.pcd`（体素降采样）。

## 已完成的内容

1. **安装** livox_ros_driver2 + Point-LIO（Mid-360 专用版 fork）
2. **建图并保存点云** 为 `.pcd`
3. **清洗点云**：统计离群点去除（SOR），450 万点 → 405 万点
4. **体素降采样**：0.1 / 0.2 / 0.3 m 三档可选
5. **生成 2D 占据格栅图**：`map.pgm` + `map.yaml`
6. **优化**：未知区填为可通行、墙体加粗、去除孤立噪声
7. **发布节点**：`occupancy_grid_publisher.py` 把地图发成 `/map` 话题（OccupancyGrid）


最终地图统计：障碍 175240 格、可通行 707138 格、未知 0 格。

## 运行方法

### 1. 发布地图（OccupancyGrid → `/map`）

```bash
source /opt/ros/humble/setup.bash
python3 /home/zhunan/livox_ws/scripts/occupancy_grid_publisher.py \
  /home/zhunan/livox_ws/catkin_point_lio_unilidar/src/point_lio_ros2/PCD/map/map.yaml
```

发布采用 `TRANSIENT_LOCAL`（latched），后订阅者也能收到完整地图。

### 2. RViz 查看

```bash
source /opt/ros/humble/setup.bash
rviz2 -d /home/zhunan/livox_ws/scripts/map_view.rviz
```

（配置文件已设好 Fixed Frame=`map`、俯视图、`/map` 话题。）

### 3. 官方 map_server 方式（可选）

```bash
sudo apt install ros-humble-nav2-map-server
ros2 run nav2_map_server map_server --ros-args \
  -p yaml_filename:=/home/zhunan/livox_ws/catkin_point_lio_unilidar/src/point_lio_ros2/PCD/map/map.yaml
```

### 4. 重新生成地图（从点云）

```bash
python3 /home/zhunan/livox_ws/scripts/make_2d_map.py \
  /home/zhunan/livox_ws/catkin_point_lio_unilidar/src/point_lio_ros2/PCD/scans_filtered_bin.pcd \
  /home/zhunan/livox_ws/catkin_point_lio_unilidar/src/point_lio_ros2/PCD/map
```

## 地图保存方式

- **点云地图**：建图时由 Point-LIO 的 `config/mid360.yaml` 里 `pcd_save` 段保存为 `PCD/scans.pcd`。注意 `interval: -1` 表示每次运行**覆盖**保存同名文件。
- **2D 地图**：标准 ROS 格式，两张文件配套使用——
  - `map.pgm`：灰度图（P5 格式），`0`=黑/障碍，`254`=白/可通行；
  - `map.yaml`：`resolution`（分辨率）、`origin`（左下角世界坐标）、`occupied_thresh` / `free_thresh`（0.65 / 0.196）。

## 关键参数（`make_2d_map.py` 顶部）

| 参数 | 值 | 含义 |
|------|-----|------|
| `RES` | 0.1 | 栅格分辨率（m） |
| `Z_LO / Z_HI` | -2.5 / 13.0 | 裁掉下层/天井与高层杂点 |
| `OBS_LO / OBS_HI` | 1.0 / 8.0 | 障碍高度带（避开地面弥散与天花板） |
| `THR` | 2 | 每格最少点数，判为障碍 |
| `MIN_COMP` | 5 | 去掉 <5 格的孤立噪声 |
| `DILATE` | 1 | 墙体膨胀次数（加粗/闭合断点） |

## 已知问题

- **Mid-360 向下视野仅 7°**：扫描路径附近地板扫不到，原本会产生大量"未知"区，本版本已通过"未知→可通行"填白处理。
- **RViz2（Humble）显示 shader bug**：`/map` 格栅图在某些显卡驱动下会因 `GLSL link` 失败而显示成黑屏/空白（与地图数据无关）。此时直接看 `map_preview.png`，或升级 ROS2（Iron/Jazzy 已修复）。
