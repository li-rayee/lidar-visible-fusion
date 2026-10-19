# 数据采集：GO2W 平台 LiDAR 与相机

这份笔记记 GO2W 四足机器人上激光雷达与前置相机的启动和录制方式，供复现 2026-06-10 巡检数据集时参考。采集侧命令来自 Unitree 官方 SLAM 与导航文档，不含任何私有凭据。

## 硬件与软件

- 机器人：Unitree GO2W
- 激光雷达：Unitree xt16（40 线），经 `unitree_slam` 模块驱动
- 相机：前置可见光相机，原始流落盘为 ROS2 `/frontvideostream`
- 中间件：ROS2 + CycloneDDS

## LiDAR 启动

官方教程：<https://support.unitree.com/home/zh/developer/SLAM%20and%20Navigation_service>

在机器人端分终端拉起 SLAM、雷达驱动、键盘控制与可视化：

```bash
# 终端 1：SLAM 主程序
cd /unitree/module/unitree_slam/bin
env -i \
  HOME=/home/unitree \
  USER=unitree \
  LOGNAME=unitree \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  LD_LIBRARY_PATH=/usr/local/lib \
  CYCLONEDDS_URI=file:///unitree/module/unitree_slam/config/cyclonedds.xml \
  ./unitree_slam

# 终端 2：xt16 雷达驱动
cd /unitree/module/unitree_slam/bin
env -i \
  HOME=/home/unitree USER=unitree LOGNAME=unitree \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  LD_LIBRARY_PATH=/usr/local/lib \
  CYCLONEDDS_URI=file:///unitree/module/unitree_slam/config/cyclonedds.xml \
  ./xt16_driver

# 终端 3：键盘建图控制
cd /unitree/module/unitree_slam/bin
env -i \
  HOME=/home/unitree USER=unitree LOGNAME=unitree \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  LD_LIBRARY_PATH=/usr/local/lib \
  CYCLONEDDS_URI=file:///unitree/module/unitree_slam/config/cyclonedds.xml \
  ./keyDemo eth0

# 终端 4：可视化
ros2 run rviz2 rviz2
```

建图操作见 Unitree 服务控制台 KeyDemo 教程。

## 录制与话题

机器人运行时，点云、相机帧与 IMU 各自发布为 ROS2 话题，用 `ros2 bag record` 落盘为 SQLite3 格式的 Bag：

- `/utlidar/cloud`：每点 32 字节（x/y/z/intensity/ring/time），`PointCloud2`
- `/frontvideostream`：前置相机帧
- `/utlidar/imu`：惯性测量数据

## 离线处理衔接

本仓库 `src/` 直接读这些 Bag：先 `bag_parse.py` 解包 `PointCloud2`（按 `point_step` 用 `struct.unpack_from` 抠 x/y/z/intensity），再由 `sync.py` 用最近邻时间戳把 LiDAR 帧和视频帧对齐，最后 `accumulate.py` 累积、`render.py` 三分屏渲染。相机与雷达的时钟偏移在离线阶段用最小绝对差匹配吸收，无需采集时严格硬件同步。
