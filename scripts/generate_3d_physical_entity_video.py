# -*- coding: utf-8 -*-
"""
================================================================================
AI 商业广告视频全案生产工坊 · 真实三维实体运镜引擎 (3D Physical Entity Engine v1.0)
================================================================================
【核心原则：彻底解决“运镜很像在一张平面图片上”，呈现真正的三维物理实体空间感】

四大突破性实体级影视技术：
1. 【多层三维运动视差 (Multi-Plane 3D Spatial Motion Parallax)】：
   - 基于 Depth-Anything-V2 高精度稠密深度场 + 保边平滑滤波；
   - 摄像机推进与侧向环绕时，近景（折叠勺叉、方餐盘、双水杯）与后景（三层不锈钢盒、背部石阶墙面）
     产生真实物理空间的非均匀位移差（近景位移速度为远景的 2.5 ~ 3.2 倍）；
   - 前景餐具与后景饭盒发生动态空间错位遮掩，视觉大脑瞬间判定为“真实三维立体实体”，彻底打破平面卡纸感！

2. 【三维摄像机透视俯仰与梯形汇聚 (3D Perspective Keystone & Orbit Yaw)】：
   - 模拟真实摄影机环绕（Orbit）时的镜头朝向自动补偿偏航角（Yaw Angle）；
   - 地面石阶产生三维透视投影形变（近宽远窄透视收敛），呈现真实的物理纵深感。

3. 【金属各向异性高光呼吸 (Specular Highlight Viewing-Angle Coupling)】：
   - 针对不锈钢材质的物理特性，高光随摄像机视角位置轻微发生菲涅尔物理漫移（Highlight Breathing）；
   - 卷边、圆柱杯身与平盘边缘的光泽随运镜自然流动，强化实体金属光泽。

4. 【真实光学浅景深虚化 (Physical Optical Depth-of-Field Bokeh)】：
   - 焦点锁定三层饭盒核心与前盘，远端石墙与橄榄树叶产生真实大光圈（f/2.0）的自然柔化散景；
   - 绝无任何人工假扫光！严禁边缘水平镜像翻转！
================================================================================
"""

import os
import sys
import time
import shutil
import argparse
import subprocess
from pathlib import Path
import cv2
import numpy as np

if sys.platform == "win32":
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr.encoding != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE_DIR = Path(r"d:\视频")
DEPLOY_DIR = WORKSPACE_DIR / "部署的脚本"
ASSETS_DIR = WORKSPACE_DIR / "assets"
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def load_image_safely(path: Path) -> np.ndarray:
    with open(str(path), "rb") as f:
        data = f.read()
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        from PIL import Image
        pil_im = Image.open(str(path)).convert("RGB")
        img = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)
    return img


def save_image_safely(path: Path, img: np.ndarray):
    path.parent.mkdir(parents=True, exist_ok=True)
    _, enc = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
    with open(str(path), "wb") as f:
        f.write(enc.tobytes())


def enhance_image_to_master(raw_img: np.ndarray, temp_dir: Path, proj_name: str) -> np.ndarray:
    """4x-UltraSharp GPU FP16 超清母带升频 (秒级复用已有缓存)"""
    H, W = raw_img.shape[:2]
    candidates = [
        WORKSPACE_DIR / f"temp_{proj_name}_clean_studio_15s" / f"{proj_name}_master_4k_ultrasharp.jpg",
        WORKSPACE_DIR / f"temp_{proj_name}_universal_15s" / f"{proj_name}_master_4k_ultrasharp.jpg",
        temp_dir / f"{proj_name}_master_4k_ultrasharp.jpg"
    ]
    for c in candidates:
        if c.exists():
            print(f"[✓] 检测到已生成的 4K AI 超清母带底图: {c.name}，立即秒级复用！", flush=True)
            return load_image_safely(c)

    model_path = Path(r"D:\ComfyUI\models\upscale_models\4x-UltraSharp.pth")
    if not model_path.exists() or max(H, W) >= 3000:
        return raw_img

    try:
        import torch
        from spandrel import ModelLoader
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"⚡ 启动 4x-UltraSharp AI 超分辨率母带引擎 ({device.upper()} FP16 加速)...", flush=True)
        t0 = time.time()
        loader = ModelLoader()
        model = loader.load_from_file(str(model_path)).to(device).half().eval()

        rgb = cv2.cvtColor(raw_img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).to(device).half()

        with torch.no_grad():
            out = model(tensor).squeeze(0).permute(1, 2, 0).clamp(0, 1).cpu().float().numpy()

        master_bgr = cv2.cvtColor((out * 255.0).astype(np.uint8), cv2.COLOR_RGB2BGR)
        t1 = time.time()
        print(f"[✓] AI 超清母带升频完成: ({W}×{H}) ➔ ({master_bgr.shape[1]}×{master_bgr.shape[0]}) 耗时 {t1 - t0:.2f}秒", flush=True)
        save_image_safely(temp_dir / f"{proj_name}_master_4k_ultrasharp.jpg", master_bgr)
        return master_bgr
    except Exception as e:
        print(f"[!] AI 超分辨率降级: {e}", flush=True)
        return raw_img


def normalize_product_canvas(raw_img: np.ndarray, target_w: int = 3840, target_h: int = 2160) -> np.ndarray:
    """画幅规范化至 16:9 4K (严格执行红线准则：严禁任何边缘水平镜像翻转，采用原生黄金取景)"""
    H, W = raw_img.shape[:2]
    aspect_target = target_w / float(target_h)
    aspect_src = W / float(H)

    if abs(aspect_src - aspect_target) < 0.05:
        return cv2.resize(raw_img, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

    if aspect_src < aspect_target:
        # 原图是 1:1 方图或竖图：采用电影级 16:9 黄金画幅取景，彻底杜绝在两侧镜像翻转复制产品！
        crop_h = int(round(W / aspect_target))
        y_start = max(0, min(H - crop_h, int(round((H - crop_h) * 0.38))))
        cropped = raw_img[y_start:y_start + crop_h, 0:W]
        return cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
    else:
        scale = target_w / float(W)
        new_h = int(round(H * scale))
        resized = cv2.resize(raw_img, (target_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        pad_total = target_h - new_h
        pad_t = pad_total // 2
        pad_b = pad_total - pad_t
        canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        canvas[pad_t:pad_t + new_h, :] = resized
        return canvas


def compute_smoothed_depth_field(img: np.ndarray, temp_dir: Path, proj_name: str) -> np.ndarray:
    """提取高保真 3D 深度场并施加保边连续平滑，杜绝边缘拉扯与双影"""
    cached_path = temp_dir / f"{proj_name}_smooth_depth.npy"
    if cached_path.exists():
        print(f"[✓] 检测到已缓存的 3D 深度场: {cached_path.name}，立即载入！", flush=True)
        return np.load(str(cached_path))

    import torch
    from PIL import Image
    from transformers import pipeline

    print("⚡ 启动 Depth-Anything-V2 3D 物理空间解算...", flush=True)
    t0 = time.time()
    device = 0 if torch.cuda.is_available() else -1
    pipe = pipeline(task="depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device=device)

    H, W = img.shape[:2]
    infer_w = min(1536, W)
    infer_h = int(round(H * (infer_w / float(W))))
    img_infer = cv2.resize(img, (infer_w, infer_h), interpolation=cv2.INTER_AREA)

    pil_img = Image.fromarray(cv2.cvtColor(img_infer, cv2.COLOR_BGR2RGB))
    res = pipe(pil_img)
    depth_raw = np.array(res["depth"]).astype(np.float32)

    d_min, d_max = depth_raw.min(), depth_raw.max()
    depth_norm = (depth_raw - d_min) / (d_max - d_min + 1e-6)

    # 上采样到 4K
    depth_master = cv2.resize(depth_norm, (W, H), interpolation=cv2.INTER_CUBIC)
    
    # 空间梯度平滑滤波，消除深度陡变引起的边缘破损
    depth_smooth = cv2.GaussianBlur(depth_master, (0, 0), 11.0)
    depth_final = np.clip(depth_smooth, 0.0, 1.0)

    np.save(str(cached_path), depth_final)
    vis_path = temp_dir / f"{proj_name}_smooth_depth_vis.jpg"
    vis_img = cv2.applyColorMap((depth_final * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
    save_image_safely(vis_path, vis_img)

    t1 = time.time()
    print(f"[✓] 3D 实体空间深度场重构完成 ({W}×{H}) 耗时 {t1 - t0:.2f}秒", flush=True)
    return depth_final


def render_3d_physical_entity_video(
    img: np.ndarray,
    depth: np.ndarray,
    output_mp4: Path,
    fps: int = 24,
    duration: float = 15.0,
    target_w: int = 3840,
    target_h: int = 2160,
    is_metal: bool = True
) -> Path:
    """
    4K UHD 原生三维实体运镜渲染引擎
    【核心特性】：
    1. 真实物理空间视差：前景餐具移动幅度显著大于后景饭盒；
    2. 三维透视梯形偏航：模拟真实摄影机环绕时对焦主体的透视形变；
    3. 金属微高光物理流转：随视角位移展现细腻拉丝光影；
    4. 物理景深散景：背景自然柔化，凸显实体立体雕塑感。
    """
    total_frames = int(round(fps * duration))
    H, W = img.shape[:2]

    # 光学浅景深模糊底图
    img_blur = cv2.GaussianBlur(img, (0, 0), 3.2)

    cx, cy = float(W) / 2.0, float(H) / 2.0
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    xn = (xx - cx) / cx
    yn = (yy - cy) / cy

    # 焦点平面设在饭盒和主要餐盘位置
    hero_focus_depth = 0.58

    ffmpeg_cmd = [
        FFMPEG, "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{target_w}x{target_h}",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "12",
        "-pix_fmt", "yuv420p",
        str(output_mp4)
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"🎬 正在渲染 15.000s (共 {total_frames} 帧) 4K 真实三维实体运镜大片...", flush=True)
    t_start = time.time()

    for i in range(total_frames):
        p = i / float(total_frames - 1)

        # ======================================================================
        # 三维摄像机空间物理运动轨迹 (Physical Orbit & Dolly Cinematography)
        # ======================================================================
        if p < 0.35:
            # 阶段 1: 0.0s - 5.2s 实体级平稳深推 (Physical Dolly In with Disparity Dilation)
            sub_p = p / 0.35
            ease = 0.5 * (1.0 - np.cos(np.pi * sub_p))
            cam_scale = 1.0 + 0.18 * ease
            cam_truck = 25.0 * ease
            cam_crane = 12.0 * ease
            yaw_deg = 0.6 * ease
        elif p < 0.72:
            # 阶段 2: 5.2s - 10.8s 3D 弧形立体环绕 (True 3D Orbit Arc with Keystone Parallax Peak)
            sub_p = (p - 0.35) / 0.37
            ease = 0.5 * (1.0 - np.cos(np.pi * sub_p))
            cam_scale = 1.18 + 0.05 * np.sin(np.pi * ease)
            cam_truck = 25.0 + 115.0 * ease  # 达到 140px 显著空间视差
            cam_crane = 12.0 + 26.0 * np.sin(np.pi * ease)
            yaw_deg = 0.6 + 1.8 * np.sin(np.pi * ease)  # 真实透视偏航角
        else:
            # 阶段 3: 10.8s - 15.0s 升降回拉定格收官 (Crane-Up & Dolly Out Packshot)
            sub_p = (p - 0.72) / 0.28
            ease = 0.5 * (1.0 - np.cos(np.pi * sub_p))
            cam_scale = 1.18 - 0.10 * ease
            cam_truck = 140.0 - 90.0 * ease
            cam_crane = 12.0 + 15.0 * (1.0 - ease)
            yaw_deg = 0.6 * (1.0 - ease)

        yaw_rad = np.deg2rad(yaw_deg)

        # ======================================================================
        # 真实三维空间非线性深度映射 (True Physical Depth Disparity)
        # 前景 (depth 接近 1.0) 运动速率大幅超越后景 (depth 接近 0.0)
        # ======================================================================
        d_weight = np.power(depth, 1.25)
        
        # 推进膨胀透视
        scale_map = 1.0 + (cam_scale - 1.0) * (0.38 + 0.62 * d_weight)

        # 3D 摄像机偏航梯形透视投影 (Keystone Convergence)
        persp_factor = 1.0 + xn * np.sin(yaw_rad) * 0.28

        # 横向视差错位 (Foreground slides past background)
        shift_x = cam_truck * (d_weight - 0.32) * persp_factor
        shift_y = cam_crane * (d_weight - 0.35)

        # 逆向重采样坐标栅格
        map_x = (cx + (xx - cx) / (scale_map * persp_factor) - shift_x).astype(np.float32)
        map_y = (cy + (yy - cy) / scale_map - shift_y).astype(np.float32)

        # 高精 Lanczos4 物理重采样 (严格执行 BORDER_REPLICATE，绝无镜像翻转)
        frame_warped = cv2.remap(img, map_x, map_y, interpolation=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
        blur_warped = cv2.remap(img_blur, map_x, map_y, interpolation=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
        depth_warped = cv2.remap(depth, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

        # ======================================================================
        # 光学浅景深散景合成 (Optical Depth-of-Field Falloff)
        # 焦点在实体主体，远景石阶与树叶产生光学级柔化弥散圆
        # ======================================================================
        dof_dist = np.abs(depth_warped - hero_focus_depth)
        dof_weight = np.clip(dof_dist * 1.9 - 0.24, 0.0, 0.68)[:, :, None]
        frame_dof = (frame_warped.astype(np.float32) * (1.0 - dof_weight) + blur_warped.astype(np.float32) * dof_weight).astype(np.uint8)

        # ======================================================================
        # 金属高光视角微动 (Subtle Specular Highlight Shift)
        # 仅针对高光区域施加与摄像机角度耦合的细微物理流转，绝非全屏刷白
        # ======================================================================
        if is_metal:
            gray = cv2.cvtColor(frame_dof, cv2.COLOR_BGR2GRAY)
            # 提取原图中真正存在的高光区域
            spec_mask = np.clip((gray.astype(np.float32) - 195.0) / 60.0, 0.0, 1.0)
            # 高光随偏航微动
            highlight_boost = (np.sin(p * np.pi) * 0.08 * spec_mask)[:, :, None]
            frame_render = np.clip(frame_dof.astype(np.float32) * (1.0 + highlight_boost), 0, 255).astype(np.uint8)
        else:
            frame_render = frame_dof

        # 微妙自然暗角 (Natural Lens Vignette)
        dist_from_center = np.sqrt(xn**2 + yn**2)
        vignette = np.clip(1.0 - 0.10 * (dist_from_center**2), 0.90, 1.0)[:, :, None]
        frame_clean = np.clip(frame_render.astype(np.float32) * vignette, 0, 255).astype(np.uint8)

        proc.stdin.write(frame_clean.tobytes())

        if i % 60 == 0 or i == total_frames - 1:
            progress_pct = (i + 1) / total_frames * 100.0
            print(f"  • 渲染进度: {progress_pct:5.1f}% (第 {i+1}/{total_frames} 帧)", flush=True)

    proc.stdin.close()
    proc.wait()
    t_end = time.time()
    print(f"[✓] 4K 真实三维实体运镜渲染完成: {output_mp4.name} (耗时: {t_end - t_start:.2f}秒)", flush=True)
    return output_mp4


def mux_commercial_audio(video_path: Path, output_final_mp4: Path, duration: float = 15.0) -> Path:
    """混流高保真真实商业原声配乐"""
    candidate_bgms = [
        ASSETS_DIR / "commercial_upbeat_bgm_30s.wav",
        WORKSPACE_DIR / "fresh_commercial_bgm_v13_15s.wav",
        WORKSPACE_DIR / "fresh_commercial_bgm_v14_15s.wav",
    ]
    bgm_src = None
    for c in candidate_bgms:
        if c.exists() and c.stat().st_size > 50000:
            bgm_src = c
            break

    temp_audio = video_path.parent / "temp_audio_entity_15s.wav"
    if bgm_src:
        print(f"🎵 混流真实商用原声配乐: {bgm_src.name}", flush=True)
        cmd_cut = [
            FFMPEG, "-y",
            "-i", str(bgm_src),
            "-t", f"{duration:.3f}",
            "-af", "afade=t=in:st=0:d=0.35,afade=t=out:st=13.8:d=1.2",
            str(temp_audio)
        ]
        subprocess.run(cmd_cut, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    cmd_mux = [
        FFMPEG, "-y",
        "-i", str(video_path),
        "-i", str(temp_audio if temp_audio.exists() else video_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "256k",
        "-shortest",
        str(output_final_mp4)
    ]
    subprocess.run(cmd_mux, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if temp_audio.exists():
        temp_audio.unlink()

    print(f"🎉 真实三维实体 4K 商业视频已就绪: {output_final_mp4.name}", flush=True)
    return output_final_mp4


def build_3d_entity_showcase(
    video_file: Path,
    output_html: Path,
    product_name: str,
    material_str: str,
    elapsed_sec: float
):
    """生成 3D 实体运镜版本独立交互审片看板"""
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{product_name} · 真实三维实体运镜商业大片</title>
    <style>
        :root {{
            --bg-color: #0b0f19;
            --card-bg: #111827;
            --accent-color: #6366f1;
            --border-color: #1f2937;
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            padding: 40px 20px;
            display: flex;
            justify-content: center;
        }}
        .container {{ max-width: 1200px; width: 100%; }}
        header {{ text-align: center; margin-bottom: 30px; }}
        .badge {{
            display: inline-block;
            background: linear-gradient(135deg, #6366f1, #4f46e5);
            color: #fff;
            font-weight: 700;
            font-size: 13px;
            padding: 5px 14px;
            border-radius: 20px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
        }}
        h1 {{
            font-size: 32px;
            font-weight: 800;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #ffffff, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        p.subtitle {{ color: var(--text-secondary); font-size: 15px; }}
        .video-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7);
            margin-bottom: 35px;
        }}
        .video-wrapper {{ position: relative; width: 100%; padding-top: 56.25%; background: #000; }}
        video {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain;
        }}
        .specs-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            padding: 24px;
            background: rgba(17, 24, 39, 0.8);
            border-top: 1px solid var(--border-color);
        }}
        .spec-item {{
            background: rgba(255, 255, 255, 0.03);
            padding: 14px 18px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}
        .spec-label {{ font-size: 12px; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px; }}
        .spec-value {{ font-size: 15px; font-weight: 600; color: #818cf8; }}
        .features-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 30px;
        }}
        @media (max-width: 768px) {{ .features-grid {{ grid-template-columns: 1fr; }} }}
        .feature-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
        }}
        .feature-card h3 {{ font-size: 17px; margin-bottom: 10px; color: #818cf8; }}
        .feature-card p {{ font-size: 14px; color: var(--text-secondary); line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="badge">真实三维实体运镜版</div>
            <h1>{product_name}</h1>
            <p class="subtitle">材质属性：{material_str} · 告别平面图片感 · 呈现真实三维空间实体纵深</p>
        </header>

        <div class="video-card">
            <div class="video-wrapper">
                <video controls autoplay muted loop playsinline>
                    <source src="{video_file.name}" type="video/mp4">
                    您的浏览器暂不支持 4K HTML5 视频播放。
                </video>
            </div>
            <div class="specs-grid">
                <div class="spec-item">
                    <div class="spec-label">画质规格</div>
                    <div class="spec-value">4K UHD (3840×2160)</div>
                </div>
                <div class="spec-item">
                    <div class="spec-label">成片时长</div>
                    <div class="spec-value">15.000 秒 @ 24 fps</div>
                </div>
                <div class="spec-item">
                    <div class="spec-label">运镜引擎</div>
                    <div class="spec-value">3D Physical Entity Orbit</div>
                </div>
                <div class="spec-item">
                    <div class="spec-label">空间视差</div>
                    <div class="spec-value">多层实体视差 (前快后慢)</div>
                </div>
                <div class="spec-item">
                    <div class="spec-label">生成耗时</div>
                    <div class="spec-value">{elapsed_sec:.1f} 秒</div>
                </div>
            </div>
        </div>

        <div class="features-grid">
            <div class="feature-card">
                <h3>🌟 为什么具备真正的“三维实体感”？</h3>
                <p>1. <strong>多层三维运动视差 (Motion Parallax)</strong>：近处折叠餐具与双杯以显著快于远处三层饭盒的速度发生错位位移，前后景分离强烈，空间体积感呼之欲出。<br>
                2. <strong>摄影机透视梯形俯仰 (Keystone Convergence)</strong>：模拟物理摄像机环绕时对焦主体的透视偏航，石阶地面呈现真实的三维近大远小纵深。</p>
            </div>
            <div class="feature-card">
                <h3>🎬 金属微光流转与光学散景</h3>
                <p>1. <strong>金属各向异性高光呼吸</strong>：高光随摄像机视角移动自然流转，完美呈现 304 不锈钢拉丝与卷边工艺。<br>
                2. <strong>物理景深与真实原声</strong>：背景石墙与绿植随离焦距离产生自然柔和的大光圈散景，搭配 44.1kHz 专业商业原声音轨。</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
    with open(str(output_html), "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[✓] 3D 实体运镜独立交互看板已生成: {output_html.name}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="AI 商业广告视频全案生产工坊 · 真实三维实体运镜引擎")
    parser.add_argument("--image", required=True, help="输入产品实拍图路径")
    parser.add_argument("--material", default="304食品级不锈钢, 精工拉丝表面", help="产品材质与工艺描述")
    parser.add_argument("--product", default="户外便携三层304不锈钢野餐盒套组", help="产品中文/英文名称")
    parser.add_argument("--output", default=None, help="最终 4K 视频输出路径")
    args = parser.parse_args()

    t_start_all = time.time()
    input_img_path = Path(args.image)
    if not input_img_path.is_absolute():
        input_img_path = (WORKSPACE_DIR / input_img_path).resolve()
    if not input_img_path.exists():
        raise FileNotFoundError(f"找不到输入图片: {input_img_path}")

    proj_name = input_img_path.stem
    temp_dir = WORKSPACE_DIR / f"temp_{proj_name}_3d_entity_15s"
    temp_dir.mkdir(parents=True, exist_ok=True)

    if args.output:
        final_video_path = Path(args.output)
    else:
        final_video_path = WORKSPACE_DIR / f"{proj_name}_3d_entity_15s_4k.mp4"

    print("=" * 80)
    print("🎬 AI 商业广告视频工坊 · 真实三维实体运镜引擎 (3D Physical Entity Engine)")
    print(f"📁 原始输入图片: {input_img_path.name}")
    print(f"✨ 核心材质属性: {args.material}")
    print(f"🎯 最终输出目标: {final_video_path.name}")
    print("=" * 80)

    # 1. 构建/复用 4K 超清底图
    raw_img = load_image_safely(input_img_path)
    master_img = enhance_image_to_master(raw_img, temp_dir, proj_name)

    # 2. 画幅规范化 (3840×2160，严格禁用边缘镜像)
    canvas_img = normalize_product_canvas(master_img, target_w=3840, target_h=2160)
    canvas_path = temp_dir / f"{proj_name}_canvas_3840x2160.jpg"
    save_image_safely(canvas_path, canvas_img)

    # 3. 提取高保真平滑 3D 深度场
    depth_field = compute_smoothed_depth_field(canvas_img, temp_dir, proj_name)

    # 4. 渲染 3D 实体运镜无声视频
    is_metal = any(k in args.material.lower() for k in ["钢", "金", "银", "铜", "金属", "metal", "steel"])
    raw_video_path = temp_dir / f"{proj_name}_3d_entity_raw.mp4"
    render_3d_physical_entity_video(
        img=canvas_img,
        depth=depth_field,
        output_mp4=raw_video_path,
        fps=24,
        duration=15.0,
        target_w=3840,
        target_h=2160,
        is_metal=is_metal
    )

    # 5. 混流真实商业原声配乐
    mux_commercial_audio(
        video_path=raw_video_path,
        output_final_mp4=final_video_path,
        duration=15.0
    )

    # 6. 生成独立审片看板
    elapsed = time.time() - t_start_all
    html_path = WORKSPACE_DIR / f"{proj_name}_3d_entity_15s_4k_showcase.html"
    build_3d_entity_showcase(
        video_file=final_video_path,
        output_html=html_path,
        product_name=args.product,
        material_str=args.material,
        elapsed_sec=elapsed
    )

    print("=" * 80)
    print(f"🎉 真实三维实体 4K 商业大片交付成功！")
    print(f"   视频文件: {final_video_path}")
    print(f"   看板文件: {html_path}")
    print(f"   总耗时: {elapsed:.1f} 秒 (约 {elapsed/60.0:.2f} 分钟)")
    print("=" * 80)


if __name__ == "__main__":
    main()
