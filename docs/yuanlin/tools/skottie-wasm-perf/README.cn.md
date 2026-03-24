# Skia Skottie WASM 性能测试工具

## 概述

`tools/skottie-wasm-perf` 是用于测量 Skottie（Skia 的 Lottie 动画引擎）在 WebAssembly 环境下渲染性能的工具。它使用 Puppeteer 控制 Chrome 浏览器，加载 CanvasKit WASM 模块，回放 Lottie JSON 动画文件，并收集帧率和渲染时间等性能指标。测试结果以 Skia Perf 兼容的 JSON 格式输出。

## 目录结构

```
tools/skottie-wasm-perf/
├── .gitignore                   # 忽略 node_modules
├── Makefile                     # 构建和运行命令
├── package.json                 # Node.js 依赖配置
├── package-lock.json            # 依赖锁定文件
├── skottie-wasm-perf.html       # 浏览器端性能测试页面
├── skottie-wasm-perf.js         # Puppeteer 驱动脚本（主入口）
└── parse_perf_csvs.py           # CSV 性能数据解析脚本
```

## 核心组件

### skottie-wasm-perf.js

Node.js 命令行应用，使用 Puppeteer 驱动浏览器执行性能测试：

**命令行参数：**

| 参数 | 说明 |
|------|------|
| `--canvaskit_js` | canvaskit.js 文件路径 |
| `--canvaskit_wasm` | canvaskit.wasm 文件路径 |
| `--input` | 要测试的 Lottie JSON 文件 |
| `--output` | 性能结果输出文件（默认 perf.json） |
| `--use_gpu` | 是否使用 GPU 模式（非无头模式） |
| `--port` | 本地服务器端口（默认 8081） |

**工作流程：**

1. 启动 Express 本地 HTTP 服务器
2. 提供 CanvasKit JS/WASM 文件和 Lottie JSON 文件
3. 使用 Puppeteer 启动 Chrome（可选 GPU 模式）
4. 加载 `skottie-wasm-perf.html` 测试页面
5. 等待浏览器完成动画渲染性能测试
6. 收集性能数据并写入 JSON 文件

### skottie-wasm-perf.html

浏览器端测试页面，负责：

- 初始化 CanvasKit WASM 模块
- 加载并解析 Lottie JSON 动画
- 使用 Skottie API 进行多帧渲染循环
- 收集每帧的渲染时间数据
- 计算统计指标（平均值、中位数、百分位数等）

### parse_perf_csvs.py

后处理脚本，用于：

- 解析多个 CSV 格式的性能测试结果
- 汇总和比较不同运行的性能数据
- 生成适合上传到 Perf 系统的格式

## 使用方法

### 安装依赖

```bash
cd tools/skottie-wasm-perf
npm install
```

### 运行测试

```bash
# 使用 Makefile
make

# 或直接使用 Node.js
node skottie-wasm-perf.js \
  --canvaskit_js ../../out/canvaskit_wasm/canvaskit.js \
  --canvaskit_wasm ../../out/canvaskit_wasm/canvaskit.wasm \
  --input /path/to/animation.json \
  --output perf.json
```

### GPU 模式

```bash
node skottie-wasm-perf.js \
  --use_gpu \
  --canvaskit_js path/to/canvaskit.js \
  --canvaskit_wasm path/to/canvaskit.wasm \
  --input animation.json
```

## 性能指标

测试收集的主要指标：

- **帧渲染时间**: 每帧的 seek + draw + flush 时间
- **平均帧时间**: 所有帧的平均渲染耗时
- **百分位数**: P90、P95、P99 帧时间
- **总动画时间**: 完成一轮动画回放的总耗时

## 依赖项

- **Node.js**: v8.9 或更高版本
- **puppeteer**: 浏览器自动化控制
- **express**: 本地 HTTP 服务器
- **command-line-args**: 命令行参数解析
- **node-fetch**: HTTP 请求

## CI 集成

在 Skia CI 中，该工具作为性能测试任务运行，结果上传到 perf.skia.org 用于持续性能监控和回归检测。

## 与其他模块的关系

- **modules/canvaskit/**: 提供 CanvasKit WASM 构建
- **modules/skottie/**: Skottie 动画引擎核心实现
- **tools/lottie-web-perf/**: 类似工具，但测试 lottie-web 库的性能
- **tools/perf-canvaskit-puppeteer/**: 更通用的 CanvasKit 性能测试框架
