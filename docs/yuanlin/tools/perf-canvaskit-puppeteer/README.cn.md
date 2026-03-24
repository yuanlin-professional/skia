# Skia CanvasKit Puppeteer 性能测试工具

## 概述

`tools/perf-canvaskit-puppeteer` 是使用 Puppeteer 和 Chrome 浏览器测量 CanvasKit（Skia 的 WebAssembly 构建）性能的综合测试框架。该模块提供了多种性能测试场景，包括 Canvas 绘图操作基准测试、Skottie 动画帧性能测试和 SKP 回放性能测试。测试结果上传到 perf.skia.org 用于持续性能监控。

## 目录结构

```
tools/perf-canvaskit-puppeteer/
├── README.md                           # 英文使用文档
├── Makefile                            # 构建和运行命令
├── package.json                        # Node.js 依赖配置
├── package-lock.json                   # 依赖锁定文件
├── benchmark.js                        # 基准测试框架核心
├── perf-canvaskit-with-puppeteer.js    # Puppeteer 驱动脚本
├── canvas_perf.html                    # Canvas 绘图性能测试页面
├── canvas_perf.js                      # Canvas 绘图性能测试代码（约 25KB）
├── skottie-frames.html                 # Skottie 帧性能测试页面
├── render-skp.html                     # SKP 渲染测试页面
├── path-transform.html                 # 路径变换性能测试页面
├── skp_data_prep.js                    # SKP 数据预处理脚本
├── perf_all_skps.sh                    # 批量 SKP 性能测试脚本
├── canvas_perf_assets/                 # Canvas 测试资源
│   ├── Roboto-Regular.ttf              # 测试字体
│   ├── Roboto-Regular.woff             # WOFF 字体
│   ├── Roboto-Regular.woff2            # WOFF2 字体
│   ├── test_1500x959.jpg              # 测试图片（大尺寸）
│   ├── test_512x512.png               # 测试图片（中尺寸）
│   └── test_64x64.png                 # 测试图片（小尺寸）
└── path_translate_assets/
    └── car.svg                         # 路径变换测试 SVG
```

## 测试类型

### 1. Canvas 绘图性能测试

**文件:** `canvas_perf.html` + `canvas_perf.js`

测试 CanvasKit 各种 Canvas 绘图操作的性能：

- 基本形状绘制（矩形、椭圆、路径等）
- 文本渲染
- 图像绘制和变换
- 渐变和着色器
- 滤镜和混合模式

```bash
make perf_js
```

**测量指标：**

| 指标 | 说明 |
|------|------|
| `without_flush_ms` | 仅 test() 函数的执行时间 |
| `with_flush_ms` | test() + flush() 的执行时间 |
| `total_frame_ms` | 帧到帧的总时间（包含 GPU 工作） |

### 2. Skottie 帧性能测试

**文件:** `skottie-frames.html` + `benchmark.js`

测试 Skottie 动画渲染 600 帧的性能：

- 模拟实际动画播放场景
- 按时间线顺序循环渲染帧
- 收集逐帧渲染时间

```bash
make frames
```

**CI 指标示例：** `https://perf.skia.org/e/?queries=test%3Dlego_loader`

### 3. SKP 渲染性能测试

**文件:** `render-skp.html` + `benchmark.js`

重复渲染 SKP 文件并测量性能：

```bash
make skp
```

**CI 指标示例：** `https://perf.skia.org/e/?queries=binary%3DCanvasKit%26test%3Ddesk_chalkboard.skp`

## benchmark.js 框架

通用基准测试框架，提供：

- 多帧测量和数据采集
- 预热（warmup）阶段处理
- 统计指标计算（平均、中位数、百分位数、标准差）
- 与 Puppeteer 驱动脚本的数据通信

## 使用方法

### 初始化

```bash
cd tools/perf-canvaskit-puppeteer
npm ci

# 在 modules/canvaskit 中构建 CanvasKit
cd ../../modules/canvaskit
make release
```

### 下载测试资源

```bash
sk asset download lottie-samples ~/Downloads/lottie-samples
sk asset download skps ~/Downloads/skps
```

### 运行 Canvas 性能测试

```bash
make perf_js
```

### 仅运行部分测试

修改 `canvas_perf.js`，将 `tests.push` 改为 `onlytests.push`，然后运行 `make perf_js`。

### 批量 SKP 测试

```bash
bash perf_all_skps.sh
```

## CI 集成

在 Skia CI 中，测试结果上传到 Perf：

- Canvas 操作: `https://perf.skia.org/e/?queries=test%3Dcanvas_drawOval`
- Skottie 帧: `https://perf.skia.org/e/?queries=test%3Dlego_loader`
- SKP 回放: `https://perf.skia.org/e/?queries=binary%3DCanvasKit%26test%3Ddesk_chalkboard.skp`

## 与其他模块的关系

- **modules/canvaskit/**: 提供 CanvasKit WASM 构建
- **tools/skottie-wasm-perf/**: 专注于 Skottie WASM 性能
- **tools/lottie-web-perf/**: lottie-web 性能对比基准
- **bench/**: nanobench 提供原生 C++ 基准测试
- **perf.skia.org**: 性能数据可视化和回归检测
