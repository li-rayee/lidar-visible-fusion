# -*- coding: utf-8 -*-
"""
三分屏可视化渲染 —— 对应报告 3.4 / 3.5 节。
单帧输出 1920×720：左 视频帧 | 右上 俯视图(XY) | 右下 侧视图(XZ)，
附方向箭头(X 前进 / Y 左) 与高度 turbo 伪彩。
"""
from __future__ import annotations
import numpy as np
from PIL import Image, ImageDraw

CANVAS_W, CANVAS_H = 1920, 720
VID_W, VID_H = 854, 720
LR_W, LR_H = 1066, 360
PAD = 12

Z_FLOOR = 0.05          # 地面滤除阈值
Z_MIN, Z_MAX = 0.0, 1.6  # 高度着色范围(m)


def _turbo(x: np.ndarray) -> np.ndarray:
    """Google Turbo 多项式近似，返回 (...,3) RGB，值∈[0,1]。"""
    x = np.clip(x, 0.0, 1.0)
    r = 0.13572138 + x * (4.61539260 + x * (-42.66032258 + x * (132.13108234 + x * (-152.94239396 + x * 59.28637943))))
    g = 0.09140261 + x * (2.19418839 + x * (4.84296658 + x * (-14.18503333 + x * (4.27729857 + x * 2.82956604))))
    b = 0.10667330 + x * (12.64194608 + x * (-60.58204836 + x * (110.36276771 + x * (-89.90310912 + x * 27.34824973))))
    return np.stack([r, g, b], axis=-1)


def _render_xy(pts: np.ndarray) -> np.ndarray:
    """俯视图(XY 平面)：+X 前进→图上，+Y 左→图左。"""
    arr = np.zeros((LR_H, LR_W, 3), np.uint8)
    if pts.shape[0] == 0:
        return arr
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    mask = z > Z_FLOOR
    x, y, z = x[mask], y[mask], z[mask]
    if x.size == 0:
        return arr
    # 坐标范围自适应
    VX = (x.min(), x.max())
    VY = (y.min(), y.max())
    if VX[1] - VX[0] < 1e-3:
        VX = (VX[0] - 1, VX[0] + 1)
    if VY[1] - VY[0] < 1e-3:
        VY = (VY[0] - 1, VY[0] + 1)
    z_norm = np.clip((z - Z_MIN) / (Z_MAX - Z_MIN), 0, 1)
    colors = (_turbo(z_norm) * 255).astype(np.uint8)
    px = ((VY[1] - y) / (VY[1] - VY[0]) * LR_W).astype(np.int32)
    py = ((VX[1] - x) / (VX[1] - VX[0]) * LR_H).astype(np.int32)
    valid = (px >= 0) & (px < LR_W) & (py >= 0) & (py < LR_H)
    arr[py[valid], px[valid]] = colors[valid]
    return arr


def _render_xz(pts: np.ndarray) -> np.ndarray:
    """侧视图(XZ 平面)：+X 横轴、+Z 纵轴。"""
    arr = np.zeros((LR_H, LR_W, 3), np.uint8)
    if pts.shape[0] == 0:
        return arr
    x, z = pts[:, 0], pts[:, 2]
    x = x[z > Z_FLOOR]
    z = z[z > Z_FLOOR]
    if x.size == 0:
        return arr
    VX = (x.min(), x.max())
    if VX[1] - VX[0] < 1e-3:
        VX = (VX[0] - 1, VX[0] + 1)
    z_norm = np.clip((z - Z_MIN) / (Z_MAX - Z_MIN), 0, 1)
    colors = (_turbo(z_norm) * 255).astype(np.uint8)
    px = ((x - VX[0]) / (VX[1] - VX[0]) * LR_W).astype(np.int32)
    pz = (LR_H - z_norm * LR_H).astype(np.int32)
    valid = (px >= 0) & (px < LR_W) & (pz >= 0) & (pz < LR_H)
    arr[pz[valid], px[valid]] = colors[valid]
    # 地面参考线
    gz = int(LR_H - (0.06 - Z_MIN) / (Z_MAX - Z_MIN) * LR_H)
    arr[gz, :] = (90, 90, 90)
    return arr


def _draw_arrows(canvas: Image.Image):
    """右下角红/绿双箭头标注 X(前进)/Y(左)。"""
    d = ImageDraw.Draw(canvas)
    ox, oy = CANVAS_W - 120, CANVAS_H - 70
    # X 前进（红，向上）
    d.line([(ox, oy), (ox, oy - 40)], fill=(220, 40, 40), width=4)
    d.polygon([(ox, oy - 48), (ox - 6, oy - 38), (ox + 6, oy - 38)], fill=(220, 40, 40))
    d.text((ox + 6, oy - 52), "X 前进", fill=(220, 40, 40))
    # Y 左（绿，向左）
    d.line([(ox, oy), (ox - 40, oy)], fill=(40, 180, 60), width=4)
    d.polygon([(ox - 48, oy), (ox - 38, oy - 6), (ox - 38, oy + 6)], fill=(40, 180, 60))
    d.text((ox - 92, oy - 12), "Y 左", fill=(40, 180, 60))


def render_frame(video_frame: np.ndarray, pts: np.ndarray,
                 frame_info: str = "") -> np.ndarray:
    """合成三分屏，返回 np.uint8 (CANVAS_H, CANVAS_W, 3)。"""
    canvas = Image.new('RGB', (CANVAS_W, CANVAS_H), (20, 20, 20))
    # 1. 左侧视频帧
    vid_img = Image.fromarray(video_frame).resize((VID_W, VID_H))
    canvas.paste(vid_img, (PAD, PAD))
    # 2. 右上俯视图
    xy = Image.fromarray(_render_xy(pts))
    canvas.paste(xy, (VID_W + 2 * PAD, PAD))
    # 3. 右下侧视图
    xz = Image.fromarray(_render_xz(pts))
    canvas.paste(xz, (VID_W + 2 * PAD, PAD + LR_H + PAD))
    # 标注
    _draw_arrows(canvas)
    d = ImageDraw.Draw(canvas)
    d.text((PAD, 2), "可见光相机", fill=(230, 230, 230))
    d.text((VID_W + 2 * PAD, PAD - 2), "LiDAR 俯视(XY) 前进朝上", fill=(230, 230, 230))
    d.text((VID_W + 2 * PAD, PAD + LR_H + PAD - 2), "LiDAR 侧视(XZ)", fill=(230, 230, 230))
    if frame_info:
        d.text((PAD, CANVAS_H - 22), frame_info, fill=(230, 230, 230))
    return np.array(canvas)
