# CanvasKit Puppeteer 性能测试驱动程序

> 源文件: `tools/perf-canvaskit-puppeteer/perf-canvaskit-with-puppeteer.js`

## 概述

此文件是 CanvasKit 性能测试的主驱动程序，使用 Puppeteer 控制 Chrome 浏览器在无头模式下自动执行 CanvasKit 基准测试。它启动一个本地 Express Web 服务器来托管测试页面和资源，然后通过 Puppeteer 驱动浏览器加载测试页面、等待测试完成并收集性能数据（JSON 格式或 Chrome tracing 数据）。

## 架构位置

此文件是 CanvasKit 性能测试流水线的入口点和编排器。

- 所属模块：`tools/perf-canvaskit-puppeteer/`
- 角色：命令行应用程序，协调 Web 服务器和浏览器自动化
- 上游依赖：命令行参数和 CanvasKit 构建产物
- 下游产物：性能数据 JSON 文件或 Chrome tracing 文件

## 主要类与结构体

此文件为过程式脚本，无类定义。核心组件：

### 命令行选项（`opts` 数组）
| 选项 | 类型 | 描述 |
|------|------|------|
| `bench_html` | file | 包含基准测试的 HTML 文件 |
| `canvaskit_js` | file | canvaskit.js 路径（必需） |
| `canvaskit_wasm` | file | canvaskit.wasm 路径（必需） |
| `input_lottie` | file | Lottie JSON 文件 |
| `input_skp` | file | SKP 文件 |
| `assets` | file | 测试资源目录 |
| `output` | file | 输出性能文件（默认 perf.json） |
| `chromium_executable_path` | file | Chromium 可执行文件路径 |
| `merge_output_as` | string | 合并到已有输出文件的属性名 |
| `use_gpu` | boolean | 是否使用 GPU 模式 |
| `use_tracing` | string | Chrome tracing 类别 |
| `enable_simd` | boolean | 启用 WASM SIMD |
| `port` | number | 服务器端口（默认 8081） |
| `query_params` | string[] | 传递给测试页面的查询参数 |
| `timeout` | number | 测试超时秒数（默认 60） |

## 公共 API 函数

### `driveBrowser()`（异步）
主要的浏览器驱动函数，执行完整的测试流程：
1. 启动 Puppeteer Chrome 实例
2. 配置浏览器参数（沙箱、帧率限制、GPU 等）
3. 导航到测试页面 URL
4. 等待基准测试就绪信号（`window._perfReady`）
5. 可选启动 Chrome tracing
6. 点击开始按钮触发测试
7. 等待测试完成（`window._perfDone`）
8. 收集性能数据或停止 tracing
9. 将结果写入输出文件

## 内部实现细节

### Express Web 服务器
- 根路径 `/` 返回基准测试 HTML 页面
- `/static/benchmark.js` 和 `/static/canvas_perf.js` 返回测试脚本
- `/static/canvaskit.js` 和 `/static/canvaskit.wasm` 返回 CanvasKit 构建产物
- `/static/lottie.json` 和 `/static/test.skp` 返回可选的测试输入
- `/static/assets/` 静态目录用于字体和图片等资源
- WASM 文件设置正确的 MIME 类型（`application/wasm`）以启用流式编译

### Puppeteer 浏览器配置
- `--no-sandbox`：Docker 环境兼容
- `--disable-frame-rate-limit` + `--disable-gpu-vsync`：解除帧率限制
- `--enable-features=WebAssemblySimd`：SIMD 支持（可选）
- GPU 模式下额外启用 GPU 光栅化和忽略 GPU 黑名单

### 测试同步机制
- `window._perfReady`：测试页面就绪信号
- `window._perfDone`：测试完成信号
- `window._error`：错误信号
- `window._perfData`：性能数据

### 输出合并
当指定 `merge_output_as` 选项时，将新结果合并到已有的 JSON 输出文件中，而非覆盖。

## 依赖关系

- **puppeteer**：Chrome 浏览器自动化
- **express**：本地 Web 服务器
- **fs**：文件系统操作
- **command-line-args** / **command-line-usage**：命令行参数解析
- `benchmark.js`：基准测试框架（通过 Web 服务器提供）
- `canvas_perf.js`：性能测试定义（通过 Web 服务器提供）

## 设计模式与设计决策

- **服务器+浏览器架构**：使用本地 Web 服务器而非 file:// 协议，确保 WASM 能正确加载（流式编译需要正确的 MIME 类型）
- **信号同步模式**：通过浏览器 window 全局变量在 Node.js 和浏览器之间同步状态
- **双模式输出**：支持 JSON 性能数据和 Chrome tracing 两种输出格式
- **URL 哈希切换**：使用 URL hash（`#cpu` / `#gpu`）在同一 HTML 页面中切换 CPU 和 GPU 模式
- **帧率解锁**：通过 Chrome 参数禁用帧率限制和 VSync，确保性能测量不受显示器刷新率约束

## 性能考量

- 分离了 warmup 阶段（由基准测试页面处理）和实际测量阶段
- Chrome tracing 模式允许收集底层渲染管道（blink、cc、gpu）的详细性能数据
- GPU 模式支持测试 WebGL 后端的 CanvasKit 性能
- WASM SIMD 支持允许测量向量化指令对性能的影响
- 视口固定为 1000x1000 像素以确保一致性

## 相关文件

- `tools/perf-canvaskit-puppeteer/canvas_perf.js` - 性能测试定义
- `tools/perf-canvaskit-puppeteer/benchmark.js` - 基准测试框架
- `tools/perf-canvaskit-puppeteer/skp_data_prep.js` - SKP 数据分析工具

### 错误处理策略

程序在多个关键节点进行错误检查：
- 必需参数缺失时打印帮助信息并退出
- 浏览器启动失败时记录错误并退出
- 页面加载超时时关闭浏览器并退出
- 页面报告错误（`window._error`）时退出
- 所有退出路径都通过 `process.exit()` 确保 Express 服务器停止

### 运行模式

程序支持三种主要运行模式：
1. **CPU 基准测试**：headless 模式，通过 `#cpu` hash 使用 CanvasKit 软件渲染
2. **GPU 基准测试**：非 headless 模式（`use_gpu`），通过 `#gpu` hash 使用 WebGL 渲染
3. **Tracing 模式**：使用 Chrome DevTools Protocol 收集底层渲染管线数据

### 安全注意事项

- `--no-sandbox` 参数仅在受控 CI 环境中使用
- 本地 Web 服务器仅在 localhost 上监听
- WASM 文件通过正确的 MIME 类型提供，防止 CORS 问题

### 典型命令行用法

```
node perf-canvaskit-with-puppeteer.js \
  --bench_html canvas_perf.html \
  --canvaskit_js path/to/canvaskit.js \
  --canvaskit_wasm path/to/canvaskit.wasm \
  --assets path/to/test/assets \
  --output perf_results.json
```
