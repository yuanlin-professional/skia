# Skia Lottie-Web 性能测试工具

## 概述

`tools/lottie-web-perf` 是用于测量 lottie-web（Airbnb 的开源 Lottie 动画播放器）渲染性能的自动化工具。它使用 Puppeteer 控制 Chrome 浏览器，加载 Lottie JSON 动画文件，通过 lottie-web 库进行渲染，并收集帧率和渲染时间指标。该工具主要用于与 Skottie（Skia 的 Lottie 引擎）进行性能对比。

## 目录结构

```
tools/lottie-web-perf/
├── .gitignore                       # 忽略 node_modules
├── package.json                     # Node.js 依赖配置
├── package-lock.json                # 依赖锁定文件
├── lottie-web-perf.js               # Puppeteer 驱动脚本（主入口）
├── lottie-web-perf.html             # SVG 后端性能测试页面
└── lottie-web-canvas-perf.html      # Canvas 后端性能测试页面
```

## 核心组件

### lottie-web-perf.js

Node.js 命令行应用，驱动浏览器执行性能测试：

**命令行参数：**

| 参数 | 说明 |
|------|------|
| `--input` | Lottie JSON 文件路径 |
| `--output` | 性能结果输出文件（默认 perf.json） |
| `--use_gpu` | 使用 GPU 模式（非无头模式） |
| `--port` | 本地服务器端口（默认 8081） |
| `--lottie_player` | lottie.min.js 文件路径 |
| `--backend` | lottie-web 后端选择（canvas 或 svg） |

### 测试页面

#### lottie-web-perf.html（SVG 后端）

使用 lottie-web 的 SVG 渲染器进行性能测试：

- 通过 `lottie.loadAnimation()` 加载动画
- 使用 SVG 渲染模式
- 逐帧推进并测量渲染时间

#### lottie-web-canvas-perf.html（Canvas 后端）

使用 lottie-web 的 Canvas 渲染器进行性能测试：

- 使用 HTML5 Canvas 2D 渲染模式
- 与 SVG 后端形成对比

## 使用方法

### 安装依赖

```bash
cd tools/lottie-web-perf
npm install
```

### 运行 SVG 后端测试

```bash
node lottie-web-perf.js \
  --input /path/to/animation.json \
  --backend svg \
  --output perf_svg.json
```

### 运行 Canvas 后端测试

```bash
node lottie-web-perf.js \
  --input /path/to/animation.json \
  --backend canvas \
  --output perf_canvas.json
```

### 使用 GPU 模式

```bash
node lottie-web-perf.js \
  --input /path/to/animation.json \
  --use_gpu \
  --output perf.json
```

## 工作流程

```
1. 启动 Express HTTP 服务器
2. 提供 Lottie JSON 和 lottie-web 播放器文件
3. Puppeteer 启动 Chrome 浏览器
4. 加载对应的测试页面（SVG 或 Canvas）
5. 执行多轮动画渲染循环
6. 收集每帧渲染时间数据
7. 计算统计指标
8. 将结果写入 JSON 文件
```

## 输出格式

性能结果以 Skia Perf 兼容的 JSON 格式输出：

```json
{
  "key": {
    "test": "animation_name",
    "config": "lottie-web-svg"
  },
  "results": {
    "frame_avg_us": 1234,
    "frame_max_us": 5678,
    "frame_min_us": 890
  }
}
```

## 依赖项

- **Node.js**: v8.9 或更高版本
- **puppeteer**: 浏览器自动化
- **express**: 本地 HTTP 服务器
- **command-line-args**: 命令行参数解析
- **node-fetch**: HTTP 请求
- **lottie-web**: Lottie 动画播放器（通过 npm 安装）

## 与其他模块的关系

- **tools/skottie-wasm-perf/**: 测试 Skottie WASM 性能（用于对比）
- **tools/lottiecap/**: Lottie 渲染截图工具
- **modules/skottie/**: Skia 原生 Lottie 引擎
- **tools/perf-canvaskit-puppeteer/**: 更通用的 CanvasKit 性能测试
- **perf.skia.org**: 性能数据上传和可视化平台
