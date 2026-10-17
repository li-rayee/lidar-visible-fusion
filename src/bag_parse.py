# -*- coding: utf-8 -*-
"""
ROS2 Bag 点云解析 —— 从 sensor_msgs/PointCloud2 的 CDR 负载中按 point_step 批量提取
x / y / z / intensity 四个字段，保存为 float32 .bin。

对应报告 3.1 节。真实场景直接读 .db3（SQLite3）；这里给出与报告一致的解析核心，
并提供 make_synthetic_frame() 供无原始数据时演示。
"""
from __future__ import annotations
import os
import struct
import numpy as np


def parse_pointcloud2(msg_data: bytes, point_step: int,
                      x_off: int, y_off: int, z_off: int, inten_off: int):
    """按步长从 PointCloud2.data 提取 (x, y, z, intensity)。

    Args:
        msg_data:   CDR 二进制负载（bytes）
        point_step: 单点字节数（本项目 32）
        x_off/y_off/z_off/inten_off: 各字段在单点内的字节偏移
    Returns:
        np.ndarray, shape (N, 4), dtype float32
    """
    pts_data = np.frombuffer(msg_data, dtype=np.uint8)
    xyz_int = []
    for i in range(0, len(pts_data) - point_step, point_step):
        x = struct.unpack_from('<f', pts_data, i + x_off)[0]
        y = struct.unpack_from('<f', pts_data, i + y_off)[0]
        z = struct.unpack_from('<f', pts_data, i + z_off)[0]
        inten = struct.unpack_from('<f', pts_data, i + inten_off)[0]
        if not (np.isnan(x) or np.isinf(x)):
            xyz_int.append([x, y, z, inten])
    return np.array(xyz_int, dtype=np.float32)


def save_bin(arr: np.ndarray, out_path: str) -> None:
    """保存为 float32 二进制（与报告一致：arr.tofile）"""
    arr.tofile(out_path)


# ----------------------------------------------------------------------------
# 以下为「无原始数据」时的合成帧生成器，仅用于演示流水线。
# 场景：地面(z≈0) + 正前方行人(竖向点簇) + 两侧建筑立面(高 z 点)
# ----------------------------------------------------------------------------
def make_synthetic_frame(rng: np.random.Generator, t: float):
    """返回 (timestamp, xyz_int_array, video_frame_rgb)。"""
    pts = []
    # 地面：XZ 平面附近薄层
    n_ground = 1500
    gx = rng.uniform(-6, 6, n_ground)
    gy = rng.uniform(-4, 4, n_ground)
    gz = rng.uniform(0.0, 0.06, n_ground)
    pts.append(np.stack([gx, gy, gz, np.full(n_ground, 0.3)], axis=1))

    # 正前方行人：+X 方向约 3m 处的竖向圆柱点簇
    n_person = 400
    px = rng.normal(3.0, 0.12, n_person)
    py = rng.normal(0.0, 0.18, n_person)
    pz = rng.uniform(0.05, 1.0, n_person)        # 人体下肢~1m
    pts.append(np.stack([px, py, pz, np.full(n_person, 0.8)], axis=1))

    # 两侧建筑立面：|Y| 较大处的高 z 竖直墙面
    n_wall = 900
    wx = rng.uniform(-5, 5, n_wall)
    wy = rng.choice([-3.8, 3.8], n_wall) + rng.normal(0, 0.1, n_wall)
    wz = rng.uniform(0.0, 1.5, n_wall)
    pts.append(np.stack([wx, wy, wz, np.full(n_wall, 0.5)], axis=1))

    cloud = np.vstack(pts).astype(np.float32)

    # 合成视频帧（示意）：上深灰天空、下浅灰地面、中部画一个行人方块
    frame = np.full((720, 1280, 3), 210, np.uint8)
    frame[:300, :] = 120          # 天空
    frame[620:, :] = 235          # 近地
    # 行人（位于画面中心偏下）
    cv2_like_rect(frame, x0=600, y0=380, x1=700, y1=600, color=(40, 40, 60))
    return t, cloud, frame


def cv2_like_rect(img: np.ndarray, x0, y0, x1, y1, color):
    img[y0:y1, x0:x1] = color
