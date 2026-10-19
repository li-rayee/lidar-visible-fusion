# 数据集说明：GO2W 可见光–LiDAR 协同感知

## 采集平台

- 载体：Unitree GO2W 四足机器人
- 激光雷达：40 线（Unitree xt16），最大测距 200 m，点频约 1.152 Mpts/s
- 可见光相机：前置，1280×720，约 14.3 fps
- 录制格式：ROS2 Bag，底层用 SQLite3 存 topic / timestamp / CDR 二进制消息
- 场景与时间：2026-06-10 校园巡检

## 传感器话题

每个 Bag 至少包含三路话题：

| Topic | 内容 |
|---|---|
| `/frontvideostream` | 前置相机视频帧 |
| `/utlidar/cloud` | 激光雷达点云（`sensor_msgs/PointCloud2`，每点 32 字节：x/y/z/intensity/ring/time） |
| `/utlidar/imu` | 惯性测量单元数据 |

## ROS2 Bag 明细

三个 Bag 的 topic 消息计数与时长如下（原始计数，来自 `dataset_catalog.json`）：

| Bag | 状态 | 时长(s) | /frontvideostream | /utlidar/cloud | /utlidar/imu | 裁剪后 PCD 帧 |
|---|---|---|---|---|---|---|
| go2w_sync_raw_20260610_094554 | valid | 18.94 | 544 | 291 | 4745 | 291 |
| go2w_sync_raw_20260610_102458 | valid | 188.21 | 5378 | 2859 | 46965 | 2857 |
| go2w_sync_raw_20260610_104013 | excluded（缺 cloud/imu） | — | 1608 | 0 | 0 | 0 |

要点：

- 两个 valid Bag 提供点云 + 视频 + IMU 三方数据，进入融合流水线；第三个只录到视频，没有点云与 IMU，不参与融合。
- 雷达侧相机原始为 MJPEG AVI，离线另转 H.264/YUV420P 的 `_playable.mp4` 兼容版本统一播放。
- 点云到视频帧的对应关系记录在每包 `pointcloud_video_mapping.csv`，供帧级对齐使用。
- 机器狗 IMU 仅前两次 session 有有效数据，后续 session 源端录制为空。

## 与流水线输出帧数的关系

`README.md` 实验结果表里的帧数，是本仓库流水线在裁剪后 Bag 上实际处理的帧（受裁剪窗口与帧选择影响），与上面原始 topic 计数不同，属正常差异。流水线按 ±13 帧滑动窗口累积，把单帧约 2000–4000 点增密到约 6 万点。

## 数据使用说明

原始 Bag 体积较大，仓库不随附完整数据，仅以本说明与 `dataset_catalog.json` 记录其结构。运行 `src/demo.py` 用合成数据即可完整验证解析、同步、累积、渲染全流程。
