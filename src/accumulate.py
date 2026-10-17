# -*- coding: utf-8 -*-
"""
多帧点云累积 —— 滑动窗口把稀疏单帧增密为稠密场景表示。
对应报告 3.3 节：以当前帧为中心向前后各扩展 ±K 帧（本项目 K=13，共 27 帧），
拼接后随机子采样限制总量 ≤ 60000 点。
"""
from __future__ import annotations
import os
import numpy as np

ACC_WINDOW = 13          # 前后各 13 帧
MAX_POINTS = 60000       # 累积上限


def load_accumulated(frames: list[dict], center_idx: int, bin_dir: str) -> np.ndarray:
    """滑动窗口累积点云，最多 MAX_POINTS 点。frames[i]['file'] 为 .bin 文件名。"""
    pts_list = []
    lo = max(0, center_idx - ACC_WINDOW)
    hi = min(len(frames) - 1, center_idx + ACC_WINDOW)
    for i in range(lo, hi + 1):
        bin_path = os.path.join(bin_dir, frames[i]["file"])
        data = np.fromfile(bin_path, dtype=np.float32).reshape(-1, 4)
        pts_list.append(data)
    if not pts_list:
        return np.zeros((0, 4), np.float32)
    pts = np.concatenate(pts_list, axis=0)
    if len(pts) > MAX_POINTS:                      # 随机子采样限制总量
        idx = np.random.choice(len(pts), MAX_POINTS, replace=False)
        pts = pts[idx]
    return pts


def accumulate_from_arrays(clouds: list[np.ndarray], center_idx: int,
                           window: int = ACC_WINDOW) -> np.ndarray:
    """直接对内存中的点云数组列表做累积（演示用，无需 .bin 文件）。"""
    lo = max(0, center_idx - window)
    hi = min(len(clouds) - 1, center_idx + window)
    pts = np.concatenate(clouds[lo:hi + 1], axis=0)
    if len(pts) > MAX_POINTS:
        idx = np.random.choice(len(pts), MAX_POINTS, replace=False)
        pts = pts[idx]
    return pts
