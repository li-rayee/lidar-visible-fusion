# -*- coding: utf-8 -*-
"""
端到端演示：用合成数据跑通「同步 → 累积 → 三分屏渲染」流水线，
生成 example_tri_screen.png（无需 137MB 原始视频）。

运行：  python src/demo.py
依赖：  pip install -r requirements.txt
"""
from __future__ import annotations
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bag_parse as bp
import sync as sy
import accumulate as ac
import render as rd

N_FRAMES = 60
LIDAR_HZ = 5.0
VIDEO_FPS = 14.3
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "example_tri_screen.png")


def main():
    rng = np.random.default_rng(20260610)
    t0 = 0.0
    # 生成合成 LiDAR 帧（带时间戳）与视频帧
    lidar_frames, video_frames, video_ts = [], [], []
    for i in range(N_FRAMES):
        t = t0 + i / LIDAR_HZ
        _t, cloud, frame = bp.make_synthetic_frame(rng, t)
        lidar_frames.append((t, cloud))
        video_frames.append(frame)
    for j in range(int(N_FRAMES * VIDEO_FPS / LIDAR_HZ) + 4):
        video_ts.append(t0 + j / VIDEO_FPS)

    # 1) 时间同步：构建 LiDAR 帧 → 最近视频帧 映射
    meta = sy.build_mapping([(t, f"f{i:03d}.bin") for i, (t, _) in enumerate(lidar_frames)],
                            video_ts)
    deltas = [f["delta"] for f in meta["frames"]]
    print(f"[sync] 帧数={len(meta['frames'])} | 中位|Δt|={np.median(deltas):.2f}ms "
          f"| 均值={np.mean(deltas):.2f}ms")

    # 2) 多帧累积：取中段一帧做稠密重建
    clouds = [c for _, c in lidar_frames]
    center = N_FRAMES // 2
    acc = ac.accumulate_from_arrays(clouds, center)
    print(f"[accumulate] 单帧≈{len(clouds[center])}点 → 累积后≈{len(acc)}点 "
          f"(窗口±{ac.ACC_WINDOW})")

    # 3) 三分屏渲染
    canvas = rd.render_frame(video_frames[center], acc,
                             frame_info=f"frame #{center:03d} | 累积 {len(acc)} 点")
    from PIL import Image
    Image.fromarray(canvas).save(OUT)
    print(f"[render] 已保存三分屏示例 -> {OUT}  ({canvas.shape[1]}x{canvas.shape[0]})")


if __name__ == "__main__":
    main()
