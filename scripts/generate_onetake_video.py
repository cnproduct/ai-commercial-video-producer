# -*- coding: utf-8 -*-
"""
================================================================================
AI 商业广告视频全案生产工坊 · 斯泰尼康手持一镜到底通用引擎 (Steadicam One-Take Pro)
================================================================================
核心特性：
1. 空间轨迹连续流：
   - Shot 1 (0.0s - 5.1s): 摄影师手持平稳向前推进（Dolly In），焦点由全景自然聚焦产品主体。
   - Shot 2 (5.0s - 10.1s): 顺接上段末帧，无缝向右做微弧形侧滑（Arc Orbit Glide），展现材质与细节。
   - Shot 3 (10.0s - 15.0s): 顺接上段末帧，顺势柔和减速后拉并微升（Pull-Back Finale），定格收官。
2. 物理级首尾末帧零跳跃顺接 (Sequential Last-Frame Chaining)：
   - 提取 Shot 1 真实渲染末帧 -> 注入 Shot 2 首帧
   - 提取 Shot 2 真实渲染末帧 -> 注入 Shot 3 首帧
   - 绝不跳切、绝不瞬移、空间与光影 100% 连贯！
3. 0.08s 极致微隐形顺接：彻底消除剪辑痕迹，肉眼呈现整条行云流水长镜头。
4. 4K UHD 母带标准：3840×2160 Lanczos + CAS 0.65 动态锐化 + 44.1kHz 自适应商业 BGM。
================================================================================
"""

import os
import sys
import time
import json
import random
import argparse
import shutil
import urllib.request
import urllib.error
import subprocess
import wave
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
COMFY_DIR = Path(r"D:\ComfyUI")
COMFY_URL = "http://127.0.0.1:8190"
WORKFLOW_TEMPLATE = WORKSPACE_DIR / "minimax_h3_workflow.json"

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def get_comfy_output_dir():
    candidates = [
        Path(r"D:\ComfyUI\output"),
        Path(r"D:\Ai_cache\ComfyUI_z_image\output"),
        Path(r"D:\Ai_cache\ComfyUI\output"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def free_comfy_vram():
    try:
        req = urllib.request.Request(
            f"{COMFY_URL}/free",
            data=json.dumps({"unload_models": True, "free_memory": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)
        print("[✓] ComfyUI 显存已释放重置", flush=True)
    except Exception as e:
        print(f"[!] 释放显存提醒: {e}", flush=True)


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


def prepare_16_9_init_frame(input_img_path: Path, temp_dir: Path, proj_name: str) -> Path:
    img = load_image_safely(input_img_path)
    h, w = img.shape[:2]
    aspect = w / float(h)

    out_p = temp_dir / f"{proj_name}_onetake_init_1024.jpg"
    if 1.68 <= aspect <= 1.82:
        resized = cv2.resize(img, (1024, 576), interpolation=cv2.INTER_LANCZOS4)
        save_image_safely(out_p, resized)
        print(f"[✓] 原图符合 16:9 画幅，高质量重采样至 1024×576", flush=True)
        return out_p

    target_h = int(w * 576 / 1024)
    y_start = max(0, int(h * 0.52 - target_h / 2))
    y_end = y_start + target_h
    if y_end > h:
        y_end = h
        y_start = h - target_h
    cropped = img[y_start:y_end, 0:w]
    resized = cv2.resize(cropped, (1024, 576), interpolation=cv2.INTER_LANCZOS4)
    save_image_safely(out_p, resized)
    print(f"[✓] 已采用摄影级 16:9 居中构图优化 (1024×576)", flush=True)
    return out_p


def upload_image_to_comfy(image_path: Path, name: str) -> str:
    input_dir = COMFY_DIR / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    target_path = input_dir / name
    shutil.copy2(str(image_path), str(target_path))
    print(f"[✓] 参考帧就绪并上传至 ComfyUI: {name}", flush=True)
    return name


def submit_comfy_prompt(image_name: str, prompt_text: str, filename_prefix: str, width=1024, height=576, length=125, steps=14, shift_video=8.0, seed=None):
    if seed is None:
        seed = random.randint(10000000, 9999999999)

    with open(str(WORKFLOW_TEMPLATE), "r", encoding="utf-8") as f:
        wf = json.load(f)

    wf["4"]["inputs"]["image"] = image_name
    wf["5"]["inputs"]["prompt"] = prompt_text
    wf["5"]["inputs"]["width"] = width
    wf["5"]["inputs"]["height"] = height
    wf["5"]["inputs"]["length"] = length
    wf["6"]["inputs"]["shift_video"] = shift_video
    wf["6"]["inputs"]["shift_audio"] = 3.0
    wf["8"]["inputs"]["steps"] = steps
    wf["8"]["inputs"]["seed"] = seed
    wf["11"]["inputs"]["filename_prefix"] = filename_prefix

    payload = json.dumps({"prompt": wf}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFY_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    res = urllib.request.urlopen(req, timeout=10)
    prompt_res = json.loads(res.read().decode("utf-8"))
    prompt_id = prompt_res.get("prompt_id")
    print(f"[✓] 已提交 ComfyUI 极清渲染 (ID: {prompt_id}, 前缀: {filename_prefix}, 步数: {steps})", flush=True)
    return prompt_id


def wait_for_shot(prompt_id: str, timeout: int = 1200) -> Path:
    out_dir = get_comfy_output_dir()
    start_t = time.time()
    last_tick = start_t
    print(f"⏳ 正在等待 ComfyUI 采样计算 (Prompt ID: {prompt_id})...", flush=True)

    while time.time() - start_t < timeout:
        try:
            h_res = urllib.request.urlopen(f"{COMFY_URL}/history/{prompt_id}", timeout=10)
            h_data = json.loads(h_res.read().decode("utf-8"))
            if prompt_id in h_data:
                status_info = h_data[prompt_id].get("status", {})
                if status_info.get("status_str") == "error":
                    messages = status_info.get("messages", [])
                    err_msg = ""
                    for m in messages:
                        if m[0] == "execution_error":
                            err_msg = m[1].get("exception_message", "")
                    raise RuntimeError(f"ComfyUI 执行出错: {err_msg}")

                outputs = h_data[prompt_id].get("outputs", {})
                for node_id, node_out in outputs.items():
                    if "images" in node_out:
                        for item in node_out["images"]:
                            fname = item.get("filename")
                            if fname and (fname.endswith(".mp4") or fname.endswith(".webp")):
                                p = out_dir / fname
                                if p.exists() and p.stat().st_size > 1000:
                                    elapsed = time.time() - start_t
                                    print(f"[✓] 分镜渲染完成: {p.name} (耗时: {elapsed:.1f}s, 大小: {p.stat().st_size / 1024 / 1024:.2f} MB)", flush=True)
                                    return p
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise e
        time.sleep(3)
        if time.time() - last_tick > 25:
            print(f"  ... 采样计算中，已耗时: {time.time() - start_t:.0f}s", flush=True)
            last_tick = time.time()
    raise TimeoutError(f"任务 {prompt_id} 超时")


def extract_last_frame(video_path: Path, output_image_path: Path) -> Path:
    output_image_path = Path(output_image_path)
    output_image_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG, "-y",
        "-sseof", "-0.05",
        "-i", str(video_path),
        "-update", "1",
        "-frames:v", "1",
        "-q:v", "1",
        str(output_image_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"[✓] 末帧提取完成 (物理顺接下一镜头): {output_image_path.name}", flush=True)
    return output_image_path


def generate_adaptive_commercial_bgm(output_wav_path: Path, material_desc: str, duration: float = 15.0, sample_rate: int = 44100):
    bpm = 114.0
    beat_dur = 60.0 / bpm
    total_samples = int(duration * sample_rate)

    is_organic = "麦" in material_desc or "木" in material_desc or "竹" in material_desc or "straw" in material_desc.lower()
    
    if is_organic:
        chords_seq = [
            ([174.61, 220.00, 261.63, 329.63, 392.00], 8),  # F maj9
            ([146.83, 174.61, 220.00, 261.63, 329.63], 8),  # D min9
            ([116.54, 146.83, 174.61, 220.00, 261.63], 8),  # Bb maj9
            ([130.81, 174.61, 196.00, 261.63, 293.66], 8),  # C sus4/C
        ]
    else:
        chords_seq = [
            ([261.63, 329.63, 392.00, 523.25], 8),
            ([246.94, 293.66, 392.00, 493.88], 8),
            ([220.00, 261.63, 329.63, 440.00], 8),
            ([174.61, 220.00, 261.63, 349.23], 8)
        ]

    pad_audio = np.zeros(total_samples, dtype=np.float32)
    current_sample = 0
    for freqs, beats in chords_seq:
        chord_len = int(beats * beat_dur * sample_rate)
        if current_sample + chord_len > total_samples:
            chord_len = total_samples - current_sample
        if chord_len <= 0:
            break
        t_chord = np.linspace(0, chord_len / sample_rate, chord_len, endpoint=False)
        chord_wave = np.zeros(chord_len, dtype=np.float32)
        for f in freqs:
            chord_wave += (
                np.sin(2 * np.pi * f * t_chord) * 0.48 +
                np.sin(2 * np.pi * f * 1.002 * t_chord) * 0.28 +
                np.sin(2 * np.pi * (f * 2) * t_chord) * 0.12
            ) / len(freqs)
        attack = int(0.22 * sample_rate)
        decay = int(0.36 * sample_rate)
        env = np.ones(chord_len, dtype=np.float32)
        if chord_len > attack + decay:
            env[:attack] = np.linspace(0, 1, attack)
            env[-decay:] = np.linspace(1, 0, decay)
        pad_audio[current_sample:current_sample + chord_len] += chord_wave * env * 0.52
        current_sample += chord_len

    pluck_audio = np.zeros(total_samples, dtype=np.float32)
    arp_patterns = [
        [349.23, 392.00, 440.00, 523.25, 659.25, 523.25, 440.00, 523.25],
        [293.66, 349.23, 440.00, 523.25, 659.25, 523.25, 349.23, 440.00],
        [233.08, 293.66, 349.23, 440.00, 523.25, 440.00, 349.23, 523.25],
        [261.63, 329.63, 392.00, 523.25, 587.33, 523.25, 392.00, 587.33]
    ]
    sixteenth_dur = beat_dur / 2.0
    total_sixteenths = int(duration / sixteenth_dur)
    for b in range(total_sixteenths):
        bar_idx = int((b * sixteenth_dur) / (8 * beat_dur)) % 4
        note_idx = b % 8
        f_note = arp_patterns[bar_idx][note_idx]
        start_samp = int(b * sixteenth_dur * sample_rate)
        note_len = int(0.26 * sample_rate)
        if start_samp + note_len > total_samples:
            note_len = total_samples - start_samp
        if note_len <= 0:
            break
        t_note = np.linspace(0, note_len / sample_rate, note_len, endpoint=False)
        decay_curve = np.exp(-14.0 * t_note)
        note_wave = (
            np.sin(2 * np.pi * f_note * t_note) * 0.70 +
            np.sin(2 * np.pi * f_note * 2.0 * t_note) * 0.20 +
            np.sin(2 * np.pi * f_note * 3.0 * t_note) * 0.08
        ) * decay_curve
        gain = 0.35 if (b % 2 == 0) else 0.22
        pluck_audio[start_samp:start_samp + note_len] += note_wave * gain

    perc_audio = np.zeros(total_samples, dtype=np.float32)
    for beat in range(int(duration / beat_dur)):
        b_start = int(beat * beat_dur * sample_rate)
        if beat % 2 == 0:
            k_len = int(0.18 * sample_rate)
            if b_start + k_len <= total_samples:
                t_k = np.linspace(0, k_len / sample_rate, k_len, endpoint=False)
                kick_freq = 55.0 + 60.0 * np.exp(-35.0 * t_k)
                kick_wave = np.sin(2 * np.pi * kick_freq * t_k) * np.exp(-16.0 * t_k) * 0.35
                perc_audio[b_start:b_start + k_len] += kick_wave
        else:
            s_len = int(0.09 * sample_rate)
            if b_start + s_len <= total_samples:
                t_s = np.linspace(0, s_len / sample_rate, s_len, endpoint=False)
                shaker_noise = (np.random.rand(s_len) * 2.0 - 1.0) * np.exp(-35.0 * t_s) * 0.12
                perc_audio[b_start:b_start + s_len] += shaker_noise

    mix = pad_audio * 0.48 + pluck_audio * 0.46 + perc_audio * 0.30
    fade_in_len = int(0.3 * sample_rate)
    fade_out_len = int(1.0 * sample_rate)
    mix[:fade_in_len] *= np.linspace(0, 1, fade_in_len)
    mix[-fade_out_len:] *= np.linspace(1, 0, fade_out_len)

    max_val = np.max(np.abs(mix))
    if max_val > 0:
        mix = mix / max_val * 0.88

    mix_int16 = (mix * 32767).astype(np.int16)
    stereo = np.column_stack((mix_int16, mix_int16))

    output_wav_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_wav_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(stereo.tobytes())
    print(f"[✓] 自适应商业 BGM 合成完成: {output_wav_path.name} (114 BPM, 44.1kHz 双声道)", flush=True)
    return output_wav_path


def build_onetake_prompts(material_desc: str):
    shot1_prompt = (
        f"Cinematic unbroken steadicam one-take shot of the premium product made of {material_desc}, Arri Alexa 65 look. "
        "Camera smoothly and slowly pushes forward toward the product arranged stably in a clean elegant commercial studio setting. "
        "The solid rigid object remains 100% physically stationary, strictly solid body, perfectly constant geometry, zero morphing, zero deformation. "
        "Natural soft shallow depth of field f/2.8, background softly blurred, gentle warm daylight studio lighting sweeping across the surface textures, "
        "crisp specular highlights, continuous fluid floating camera motion, 4k 24fps luxury advertising masterclass."
    )
    shot2_prompt = (
        "Continuous unbroken steadicam one-take sequence shot, seamlessly continuing the forward camera momentum without cut. "
        f"Camera smoothly arcs and glides sideways to the right across the {material_desc} product, gently panning left "
        "to showcase fine craftsmanship details, edges, and texture contours in dynamic perspective. "
        "The solid object remains 100% physically stationary, strictly shape-invariant rigid body, zero warping, zero deformation. "
        "Soft directional studio rim light dancing along the polished contours, deep depth of field, razor-sharp focus across product boundaries, "
        "fluid organic camera glide, 4k 24fps luxury advertising master."
    )
    shot3_prompt = (
        "Continuous unbroken steadicam one-take sequence shot, seamlessly continuing the fluid camera trajectory without cut. "
        f"Camera gracefully decelerates its sideways glide, smoothly pulling back and slightly craning upward to an elevated wide perspective, "
        f"revealing the entire complete {material_desc} product in balanced harmony. "
        "The product stays 100% physically still and solid, zero deformation, exact shape consistency. "
        "Warm pristine commercial studio environment, camera coming to a gentle stable breathing rest into a luxury packshot finale, "
        "24fps commercial masterpiece."
    )
    return shot1_prompt, shot2_prompt, shot3_prompt


def main():
    parser = argparse.ArgumentParser(description="AI 商业广告视频全案生产流水线 · 斯泰尼康手持一镜到底 (One-Take Pro)")
    parser.add_argument("--image", type=str, required=True, help="输入产品实拍图路径")
    parser.add_argument("--material", type=str, default="小麦秸秆环保植物纤维", help="产品材质与工艺描述")
    parser.add_argument("--output", type=str, default=None, help="最终 4K 商业视频输出路径")
    parser.add_argument("--name", type=str, default="onetake_product", help="项目/产品英文代号")

    args = parser.parse_args()

    input_img_path = Path(args.image)
    if not input_img_path.exists():
        print(f"[X] 错误: 输入图片不存在: {input_img_path}")
        sys.exit(1)

    proj_name = args.name
    temp_dir = WORKSPACE_DIR / f"temp_{proj_name}_onetake_15s"
    temp_dir.mkdir(parents=True, exist_ok=True)

    if args.output:
        final_video_path = Path(args.output)
    else:
        final_video_path = WORKSPACE_DIR / f"{proj_name}_onetake_15s_4k.mp4"

    print("=" * 80)
    print("🎬 AI 商业广告视频【斯泰尼康手持一镜到底 One-Take Pro 引擎】启动")
    print(f"📁 原始输入图片: {input_img_path.name}")
    print(f"✨ 核心材质属性: {args.material}")
    print(f"🎯 最终输出目标: {final_video_path}")
    print("=" * 80)

    # 1. 准备首帧 16:9 画幅
    init_img_path = prepare_16_9_init_frame(input_img_path, temp_dir, proj_name)

    # 2. 构建分镜提示词
    s1_prompt, s2_prompt, s3_prompt = build_onetake_prompts(args.material)

    raw_shots = []

    # Shot 1: 推进
    print("\n--- 🎬 [1/3] 正在渲染 镜头 1 (起步平稳推近 · 建立主体视觉) ---")
    free_comfy_vram()
    s1_comfy_name = f"{proj_name}_ot_s1_init.jpg"
    upload_image_to_comfy(init_img_path, s1_comfy_name)
    pid1 = submit_comfy_prompt(s1_comfy_name, s1_prompt, f"{proj_name}_ot_s1", width=1024, height=576, steps=14, shift_video=8.0)
    shot1_raw = wait_for_shot(pid1)
    raw_shots.append(shot1_raw)
    free_comfy_vram()

    s1_last_frame = temp_dir / "shot1_last_frame.jpg"
    extract_last_frame(shot1_raw, s1_last_frame)

    # Shot 2: 顺接弧形侧移
    print("\n--- 🎬 [2/3] 正在渲染 镜头 2 (顺接弧形侧移 · 顺接Shot 1末帧贴身扫视) ---")
    free_comfy_vram()
    s2_comfy_name = f"{proj_name}_ot_s2_init.jpg"
    upload_image_to_comfy(s1_last_frame, s2_comfy_name)
    pid2 = submit_comfy_prompt(s2_comfy_name, s2_prompt, f"{proj_name}_ot_s2", width=1024, height=576, steps=14, shift_video=8.0)
    shot2_raw = wait_for_shot(pid2)
    raw_shots.append(shot2_raw)
    free_comfy_vram()

    s2_last_frame = temp_dir / "shot2_last_frame.jpg"
    extract_last_frame(shot2_raw, s2_last_frame)

    # Shot 3: 顺接后拉升华
    print("\n--- 🎬 [3/3] 正在渲染 镜头 3 (顺接后拉微升 · 顺接Shot 2末帧定格收官) ---")
    free_comfy_vram()
    s3_comfy_name = f"{proj_name}_ot_s3_init.jpg"
    upload_image_to_comfy(s2_last_frame, s3_comfy_name)
    pid3 = submit_comfy_prompt(s3_comfy_name, s3_prompt, f"{proj_name}_ot_s3", width=1024, height=576, steps=14, shift_video=8.0)
    shot3_raw = wait_for_shot(pid3)
    raw_shots.append(shot3_raw)
    free_comfy_vram()

    # 缝合与母带
    print("\n⚡ [阶段 1/2] 正在执行 0.08s 极致微隐形顺接 (无缝长镜头缝合，锁定 15.000 秒)...")
    temp_native_merged = temp_dir / "temp_native_merged_15s.mp4"
    trans_dur = 0.08
    per_shot_dur = (15.0 + 2 * trans_dur) / 3.0
    offset1 = per_shot_dur - trans_dur
    offset2 = offset1 + per_shot_dur - trans_dur

    filter_merge = (
        f"[0:v]settb=AVTB,setpts=PTS-STARTPTS,scale=1024:576:flags=lanczos,setsar=1[v0];"
        f"[1:v]settb=AVTB,setpts=PTS-STARTPTS,scale=1024:576:flags=lanczos,setsar=1[v1];"
        f"[2:v]settb=AVTB,setpts=PTS-STARTPTS,scale=1024:576:flags=lanczos,setsar=1[v2];"
        f"[v0][v1]xfade=transition=fade:duration={trans_dur}:offset={offset1:.3f}[m1];"
        f"[m1][v2]xfade=transition=fade:duration={trans_dur}:offset={offset2:.3f},trim=duration=15.000,setpts=PTS-STARTPTS[outv]"
    )
    cmd_merge = [
        FFMPEG, "-y",
        "-t", f"{per_shot_dur:.3f}", "-i", str(shot1_raw),
        "-t", f"{per_shot_dur:.3f}", "-i", str(shot2_raw),
        "-t", f"{per_shot_dur:.3f}", "-i", str(shot3_raw),
        "-filter_complex", filter_merge,
        "-map", "[outv]",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "12",
        "-r", "24",
        "-pix_fmt", "yuv420p",
        str(temp_native_merged)
    ]
    subprocess.run(cmd_merge, check=True, capture_output=True)

    bgm_wav = temp_dir / "adaptive_onetake_bgm_15s.wav"
    generate_adaptive_commercial_bgm(bgm_wav, args.material, duration=15.0)

    print("\n⚡ [阶段 2/2] 正在执行 4K UHD (3840×2160) Lanczos + CAS 0.65 极清母带重构与混音...")
    final_video_path.parent.mkdir(parents=True, exist_ok=True)
    master_cmd = [
        FFMPEG, "-y",
        "-i", str(temp_native_merged),
        "-i", str(bgm_wav),
        "-filter_complex",
        (
            "[0:v]scale=3840:2160:flags=lanczos+accurate_rnd,"
            "unsharp=lx=5:ly=5:la=0.85:cx=5:cy=5:ca=0.35,"
            "cas=strength=0.65,"
            "format=yuv420p[v]"
        ),
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "12",
        "-r", "24",
        "-c:a", "aac",
        "-b:a", "320k",
        "-t", "15.000",
        str(final_video_path)
    ]
    subprocess.run(master_cmd, check=True, capture_output=True)
    print(f"\n🎉 4K UHD 斯泰尼康一镜到底极清商业母带已圆满交付: {final_video_path.name}")
    print(f"   文件路径: {final_video_path}")
    print(f"   文件大小: {final_video_path.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
