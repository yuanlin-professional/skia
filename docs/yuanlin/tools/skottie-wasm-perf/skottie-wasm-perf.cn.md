# skottie-wasm-perf - Skottie WASM 性能测试驱动

> 源文件: `tools/skottie-wasm-perf/skottie-wasm-perf.js`

## 概述

skottie-wasm-perf.js 是一个基于 Node.js 的命令行应用程序，用于在浏览器中运行 Skottie（Lottie 动画渲染器）的 WASM 版本性能测试。它使用 Puppeteer 驱动 Chrome 浏览器，加载 CanvasKit WASM 模块和 Lottie JSON 动画文件，执行渲染并捕获性能追踪数据。

## 架构位置

位于 `tools/skottie-wasm-perf/` 目录，属于 Skia 性能基准测试工具集。该工具通过 Express 本地 Web 服务器提供资源文件，再用 Puppeteer 自动化浏览器完成测试。

## 主要类与结构体

无类定义。程序由配置解析、Web 服务器设置和浏览器驱动三部分组成。

## 公共 API 函数

### 命令行选项
| 选项 | 说明 |
|------|------|
| `--canvaskit_js` | CanvasKit JS 文件路径 |
| `--canvaskit_wasm` | CanvasKit WASM 文件路径 |
| `--input` | Lottie JSON 文件路径 |
| `--output` | 输出 perf.json 路径（默认 perf.json）|
| `--use_gpu` | 启用 GPU 非无头模式 |
| `--port` | 端口号（默认 8081）|

### `driveBrowser()`
异步函数，启动 Puppeteer 控制的 Chrome 实例，加载测试页面，等待 Skottie 动画完成或报错，收集 Chrome Tracing 数据。

## 内部实现细节

- 使用 Express 创建本地 HTTP 服务器，提供四个端点：HTML 页面、canvaskit.wasm、canvaskit.js、lottie.json
- 通过 URL hash（`#cpu` 或 `#gpu`）控制渲染模式
- 使用 Chrome Tracing API 收集 "blink"、"cc"、"gpu" 分类的性能数据
- 等待页面全局变量 `window._skottieDone` 变为 `true`，超时为 90 秒
- GPU 模式下添加 `--ignore-gpu-blocklist` 和 `--enable-gpu-rasterization` 参数

## 依赖关系

- `puppeteer` - 浏览器自动化
- `express` - HTTP 服务器
- `fs` - 文件读取
- `command-line-args` / `command-line-usage` - 命令行解析
- `node-fetch` - HTTP 客户端

## 设计模式与设计决策

- **本地服务器模式**: 通过本地 HTTP 服务器提供文件，模拟真实 Web 环境
- **Tracing 采集**: 利用 Chrome 内置的 Tracing 机制获取精确的 GPU/渲染性能数据
- **错误传播**: 页面中的错误通过 `window._error` 全局变量传递到 Node.js 进程

## 性能考量

- 视口大小固定为 1000x1000，确保一致的渲染工作负载
- 使用 `networkidle0` 等待策略确保所有资源加载完成

## 相关文件

- `tools/skottie-wasm-perf/parse_perf_csvs.py` - 性能数据对比工具
- `tools/skottie-wasm-perf/skottie-wasm-perf.html` - 测试 HTML 页面
