# AI Commercial Video Pipeline Architecture Spec (Universal Pro 4.0)

本文档定义了 Universal Pro 4.0 商业广告视频流水线的底层工程架构、数学运镜模型、光学清晰度量化算法与声学配乐合成体系。

---

## 1. 空间运镜与仿射变换数学模型 (Affine Cinebot Kinetics)

### 1.1 亚像素无损平滑插值 (Sub-Pixel Lanczos-4 Warping)
视频中每一个物理刚体运镜帧均直接映射自 4096×4096 极清母带底图。摄影机视口中心坐标 $(cx, cy)$ 与视口宽度 $bw$ 随时间 $t \in [0, T]$ 经过余弦缓动函数 (Cosine Ease-In-Out) 插值：

$$p(t) = \frac{t}{T}, \quad \text{ease}(p) = \frac{1 - \cos(\pi \cdot p)}{2}$$

当前帧视口参数为：
$$cx(t) = cx_0 + (cx_1 - cx_0) \cdot \text{ease}(p)$$
$$cy(t) = cy_0 + (cy_1 - cy_0) \cdot \text{ease}(p)$$
$$bw(t) = bw_0 + (bw_1 - bw_0) \cdot \text{ease}(p)$$
$$bh(t) = \frac{bw(t)}{\text{Aspect}}, \quad \text{Aspect} = \frac{3840}{2160} = \frac{16}{9}$$

构建源坐标三角定位点：
$$S = \begin{bmatrix} cx - \frac{bw}{2} & cy - \frac{bh}{2} \\ cx + \frac{bw}{2} & cy - \frac{bh}{2} \\ cx - \frac{bw}{2} & cy + \frac{bh}{2} \end{bmatrix}, \quad D = \begin{bmatrix} 0 & 0 \\ 3840 & 0 \\ 0 & 2160 \end{bmatrix}$$

通过三点对应计算仿射变换矩阵 $M = \text{cv2.getAffineTransform}(S, D)$，执行单步高阶插值：
$$\text{Frame}_{4\text{K}} = \text{cv2.warpAffine}(\text{Master}_{4\text{K}}, M, (3840, 2160), \text{flags}=\text{INTER\_LANCZOS4})$$

---

## 2. 图像清晰度与锐度量化理论 (Laplacian Variance Metric)

工业级画质验收采用连续拉普拉斯算子（Laplacian Operator）的方差度量法。对于灰度化图像 $I(x, y)$：

$$\nabla^2 I = \frac{\partial^2 I}{\partial x^2} + \frac{\partial^2 I}{\partial y^2}$$

在离散图像处理中使用标准卷积核：
$$K_{\text{Lap}} = \begin{bmatrix} 0 & 1 & 0 \\ 1 & -4 & 1 \\ 0 & 1 & 0 \end{bmatrix}$$

图像边缘与纹理锐度得分 $S_{\text{sharp}}$ 定义为二阶导数响应的总体方差：
$$S_{\text{sharp}} = \text{Var}(\nabla^2 I) = \frac{1}{N} \sum_{x, y} \left( (\nabla^2 I)(x, y) - \mu_{\nabla} \right)^2$$

- **低清模糊帧**：高频导数响应衰减，$\text{Var} < 10.0$；
- **4K 极清母带帧**：边缘结构对比锐利，$\text{Var}$ 跃升至 $500 \sim 800+$。

---

## 3. 内存流管道直写架构 (Direct Stdin Pipe)

为消除磁盘 I/O 损耗与二次压缩失真，视频帧通过操作系统的进程管道以 BGR24 裸数据流格式直写 FFmpeg：

```python
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-s", "3840x2160",
    "-pix_fmt", "bgr24",
    "-r", "24",
    "-i", "-",
    "-c:v", "libx264",
    "-preset", "fast",
    "-crf", "12",
    "-pix_fmt", "yuv420p",
    str(output_mp4_path)
]
proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
# 每一帧渲染后直接写入管道:
proc.stdin.write(frame.tobytes())
```

---

## 4. 自适应配乐声学工程 (Algorithmic BGM Synthesis)

系统内置数学合成器直接在内存中生成 $44.1\,\text{kHz}$ 双声道无损 WAV 商业配乐，根据材质语义自动调校音色矩阵：

### 4.1 温暖生活类 (硅胶 / 母婴 / 餐厨 / 塑料)
- **调性节奏**：$118\,\text{BPM}$ 四四拍，十六分音符交错琶音；
- **主奏乐器**：木琴（Marimba）物理声学衰减正弦波；
- **和弦垫乐**：四组温润大七和弦平滑声学交叉淡入淡出（Pad Chords）。

### 4.2 现代精密类 (金属 / 五金 / 钟表 / 电子)
- **调性节奏**：现代工业律动，高频微距晶莹八音盒；
- **主奏乐器**：高纯度基频正弦钟声叠加高次谐波（$1.002f, 2.0f$）；
- **动态衰减**：指数级陡峭衰减 $\exp(-12.0 \cdot t)$，传递冷冽精确的工业精密质感。
