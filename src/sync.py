# -*- coding: utf-8 -*-
"""
时间戳同步 —— 为每个 LiDAR 帧找时间上最近的视频帧。
对应报告 3.2 节：视频帧时间戳存有序列表，用 bisect 二分 + 左右比较取绝对差最小者，
复杂度由 O(N·M) 降到 O(N·logM)。同步结果写 meta.json。
"""
from __future__ import annotations
import bisect
import json


def find_nearest_vfi(t_lidar: float, video_ts_list: list[float]):
    """返回 (最近视频帧索引, |Δt| ms)。"""
    idx = bisect.bisect_left(video_ts_list, t_lidar)
    best_idx, best_delta = 0, float('inf')
    for candidate in (max(0, idx - 1), min(idx, len(video_ts_list) - 1)):
        delta = abs(video_ts_list[candidate] - t_lidar) * 1000.0  # -> ms
        if delta < best_delta:
            best_delta, best_idx = delta, candidate
    return best_idx, best_delta


def build_mapping(lidar_frames: list[tuple[float, str]],
                  video_timestamps: list[float]) -> dict:
    """构建 LiDAR 帧 → 视频帧 的映射，序列化到 meta.json 结构。"""
    video_timestamps = sorted(video_timestamps)   # 必须有序
    meta = {"frames": []}
    for lidar_ts, bin_path in lidar_frames:
        vfi, delta = find_nearest_vfi(lidar_ts, video_timestamps)
        meta["frames"].append({
            "file": bin_path, "t": lidar_ts, "vfi": vfi, "delta": delta
        })
    return meta


def save_meta(meta: dict, path: str = "meta.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 小自测
    vts = sorted([0.0, 0.07, 0.14, 0.21, 0.28])
    print(find_nearest_vfi(0.15, vts))   # -> (3, 6.0) 或相邻
