# 可见光与 LiDAR 协同感知可视化系统

> GO2W 四足机器人 · ROS2 多传感器离线协同感知流水线
> 李瑞宇

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square)](https://www.python.org)
[![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white)](https://numpy.org)
[![Pillow](https://img.shields.io/badge/Pillow-Imaging-4B8BBE?style=flat-square)](https://python-pillow.org)

这个项目盯的是 GO2W 四足机器人上的 40 线激光雷达和前置可见光相机，做了一套全离线的多传感器协同感知流水线：从 ROS2 Bag 原始数据出发，解析、时间同步、点云增密、坐标归一化加着色、三分屏可视化，最后合成 H.264 视频。成片用左视频、右俯视加侧视的布局，让点云和光学视频在空间语义层面互相印证。

完整技术报告在 [`docs/technical_report.pdf`](docs/technical_report.pdf)。

## 项目背景

具身智能起来之后，四足机器人在非结构化环境下的感知能力成了研究热点。激光雷达给高精度三维测距（这个项目 40 线，最大 200m，点频约 1.152 Mpts/s），可见光相机补丰富的语义纹理（1280×720，约 14.3 fps）。两者互补融合，也就是协同感知，是机器人精确理解环境的关键路径。实验平台是 GO2W 四足机器人，采集于 2026-06-10 校园巡检场景，共两段有效 ROS2 Bag（`bag_094554` 约 19 秒、`bag_102458` 约 187 秒）。

核心需求有四条。数据解析：从 ROS2 Bag 准确抠出点云帧（`sensor_msgs/PointCloud2`）和视频帧，处理好各自时间戳。时间同步：两路采样频率不同（LiDAR 约 5Hz、相机约 14fps），得建帧级跨传感器时间对齐。场景重建：单帧只有约 2000 到 4000 点，得有增密方案才分得清场景结构。可视化输出：把点云和视频相互印证这件事直观地呈现出来。

技术上有几道坎。相机标定缺失，没有内外参，精确重投影做不到，但空间拓扑层面的协同感知不受影响。时间戳异步，两时钟存在系统偏移和抖动，我用最小绝对差来构建帧级对齐。点云稀疏，远端密度骤降，就设计了滑动窗口累积方案。

## 系统架构

全离线批处理架构，Python 3.13 开发，核心依赖 NumPy、Pillow、imageio。CPU 串行，单帧渲染约 0.1 秒。

整条流水线五步。数据解析模块从 ROS2 Bag 解出 PointCloud2（struct.unpack）和视频帧（imageio）。时间同步模块给每个 LiDAR 帧配最近的视频帧（bisect，复杂度 O(N·logM)），结果写进 meta.json。点云处理模块做滑动窗口多帧累积（±13 帧到约 6 万点），再地面滤除、坐标归一化、按高度或 turbo 着色。可视化渲染模块把三分屏 Canvas（视频加俯视 XY 加侧视 XZ）画出来，标好方向。最后视频合成模块用 imageio-ffmpeg 压成 H.264 的 MP4。

| 模块 | 主要功能 | 核心技术 |
|---|---|---|
| 数据解析 | ROS2 Bag 读取、PointCloud2 解包、视频帧提取 | `struct.unpack`、`ffmpeg/imageio` |
| 时间同步 | 构建 LiDAR 帧与视频帧最近邻时间戳映射 | 最小绝对差匹配、`JSON` meta 存储 |
| 点云处理 | 多帧累积、地面滤除、坐标归一化、高度/强度着色 | NumPy 向量化、滑动窗口 |
| 可视化渲染 | 三分屏 Canvas 合成、方向标注 | `Pillow PIL`、`ImageDraw` |
| 视频合成 | 帧序列转 H.264 MP4 编码 | `imageio-ffmpeg` |

## 关键技术

### ROS2 Bag 点云解析
ROS2 Bag 用 SQLite3 存消息（topic、timestamp、CDR 二进制）。`PointCloud2` 的 `data` 按字段描述符依次存 x、y、z、intensity、ring、time（每点 32 字节），用 `struct.unpack_from` 按 `point_step` 批量抠出 x、y、z、intensity，存成 float32 的 .bin。

### 时间戳同步（最近邻）
给每个 LiDAR 帧找时间上最近的视频帧。视频帧时间戳排了有序列表，用 `bisect.bisect_left` 二分查找，再左右比一下取绝对差最小的，复杂度 O(N·logM)（N 不到 300、M 不到 3000，离线完全够用）。

### 多帧点云累积
低速巡检时单帧才 2000 到 4000 点。以当前帧为中心前后各扩 ±13 帧（共 27 帧）拼起来，随机子采样把总量压在 6 万点以内，理论上拿到约 6 万点的稠密表示（`bag_094554` 里 95.9% 的帧都达到满值）。

### 坐标归一化与着色
去地面（z 小于 0.05m），把 z 线性映射到 [0,1] 过 turbo LUT 转成高度伪彩（暖色是高处障碍）。俯视图（XY 平面）里 +X 前进对应图上、+Y 左对应图左，和相机视野严格对应。侧视图（XZ 平面）展示纵断面和障碍物高度分布。

### 三分屏渲染
单帧出 1920×720 的 PNG：左边 854×720 视频帧，右上 1066×360 俯视图，右下 1066×360 侧视图，右下角用红绿双箭头标 X/Y 方向。

## 实验结果

### 数据集
| 数据包 | 时长(s) | LiDAR帧 | 视频帧 | LiDAR帧率(Hz) | 视频帧率(fps) |
|---|---|---|---|---|---|
| 20260610_094554 | 18.81 | 97 | 245 | 5.16 | 14.3 |
| 20260610_102458 | 187.13 | 143 | 2661 | 0.76 | 14.2 |

### 时间同步质量（|Δt|）
| 数据包 | 均值(ms) | 中位(ms) | 最大(ms) | <5ms 占比 |
|---|---|---|---|---|
| 20260610_094554 | 15.67 | 0.00 | 46.96 | 23.7% |
| 20260610_102458 | 16.77 | 16.50 | 41.03 | 21.0% |

中位误差 0 到 17ms，远小于单帧间隔（约 65ms@15.3Hz），低速同步的需求满足。

### 点云密度（累积前后）
| 数据包 | 满帧比例 | 点数均值 | 点数最小 | Z 轴范围(m) |
|---|---|---|---|---|
| 20260610_094554 | 95.9% (93/97) | 59,251 | 23,993 | 0.057 ~ 1.047 |
| 20260610_102458 | 28.0% (40/143) | 59,164 | 13,926 | 0.058 ~ 1.541 |

单帧约 2800 点，累积后约 6 万点，密度提升约 21 倍。

### 可视化结论
道路两侧边界在俯视图呈对称点云；正前方有人时 +X 前端出现局部密集区；侧视图里地面点连成连续条带（z 约 0.06m），障碍物在地面线上方竖向突出，和视频高度信息互相印证。

## 数据集与采集

真实数据来自 GO2W 平台 2026-06-10 的 ROS2 Bag 录制，载体、传感器、topic 与帧数细节见 [`DATASET.md`](DATASET.md)，采集平台上 LiDAR 与相机的启动方式见 [`docs/data-collection.md`](docs/data-collection.md)。原始 Bag 的 topic 计数与裁剪后帧数已整理进 [`dataset_catalog.json`](dataset_catalog.json)。

## 跑仓库里的演示

仓库带了一个合成数据演示（`src/demo.py`），不用 137MB 原始视频也能跑通整条流水线，生成一张三分屏示例图：

```bash
pip install -r requirements.txt
python src/demo.py            # 生成 example_tri_screen.png
```

演示用 NumPy 合成地面、正前方行人、两侧建筑立面的点云和一张示意视频帧，依次过同步、累积、渲染，输出同构的三分屏 PNG。

真实处理脚本要读 ROS2 Bag 和 imageio-ffmpeg，核心逻辑和技术报告一致，见 `src/` 下的 `bag_parse.py`、`sync.py`、`accumulate.py`、`render.py`。

## 结论与展望

从 ROS2 原始数据到高质量同步可视化视频的全流程离线系统，已经完整跑通。改进方向有四条：拿到相机标定（内参 K、外参 R,T），把点云精确投回像素平面；引入运动估计（IMU 或里程计），累积时加坐标变换消掉拖影；做在线实时处理版本；把可视化数据拿去训跨模态感知网络，抬升自主导航能力。

## 目录结构

```
lidar-visible-fusion/
├── README.md                      # 本文件
├── requirements.txt
├── DATASET.md                     # 数据集说明（GO2W 平台、ROS2 Bag topic 与帧数）
├── dataset_catalog.json           # 原始 Bag topic 计数与裁剪后帧数
├── src/
│   ├── bag_parse.py               # ROS2 Bag 点云解析（PointCloud2 struct 解包）
│   ├── sync.py                    # 时间戳最近邻同步（bisect, O(N·logM)）
│   ├── accumulate.py              # 多帧滑动窗口累积（±13 → ≤6万点）
│   ├── render.py                  # 三分屏 Canvas 渲染（turbo 着色 + 方向标注）
│   └── demo.py                    # 合成数据端到端演示 → example_tri_screen.png
├── docs/
│   ├── technical_report.pdf       # 技术报告
│   └── data-collection.md         # 采集平台 LiDAR/相机启动与录制说明
└── example_tri_screen.png         # 演示生成的三分屏示例
```
