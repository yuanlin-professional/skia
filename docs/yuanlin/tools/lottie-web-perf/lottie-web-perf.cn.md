# Lottie-Web 性能测试工具

> 源文件: `tools/lottie-web-perf/lottie-web-perf.js`

## 概述

此文件是一个命令行 Node.js 应用程序，使用 Puppeteer 控制 Chrome 浏览器来测量 lottie-web 播放 Lottie 动画的性能。它通过 Chrome Tracing 机制收集 blink、cc 和 gpu 等底层渲染类别的性能数据，并将 tracing 结果导出为 JSON 文件。支持 SVG 和 Canvas 两种 lottie-web 渲染后端，以及 GPU 加速模式。

## 架构位置

- 所属模块：`tools/lottie-web-perf/`（Lottie-Web 性能基准测试）
- 角色：CI/CD 流水线中的 Lottie 动画性能测量工具
- 输出格式：Chrome Tracing JSON 文件
- 与 Skia Perf 系统集成

## 主要类与结构体

此文件为过程式 Node.js 脚本。

### 命令行选项
| 选项 | 类型 | 描述 |
|------|------|------|
| `input` | file | Lottie JSON 文件（必需） |
| `output` | file | 性能输出文件（默认 perf.json） |
| `use_gpu` | boolean | 是否使用 GPU 模式 |
| `port` | number | 本地服务器端口（默认 8081） |
| `lottie_player` | string | lottie.min.js 路径 |
| `backend` | string | 渲染后端：canvas 或 svg（必需） |

## 公共 API 函数

### `wait(ms)`
异步等待工具函数。

### `driveBrowser()`（异步）
主驱动函数：
1. 根据后端选择加载对应的 HTML 驱动页面
2. 启动 Chrome Tracing（blink、cc、gpu 类别）
3. 导航到测试页面（通过 URL hash 传递总帧数）
4. 等待 `window._lottieWebDone` 信号表示动画播放完成
5. 停止 tracing 并保存结果

## 内部实现细节

### 帧数提取
从 Lottie JSON 中提取总帧数：`totalFrames = op - ip`（出点减入点），通过 URL hash 传递给驱动页面。

### HTML 驱动页面选择
- SVG 后端：使用 `lottie-web-perf.html`
- Canvas 后端：使用 `lottie-web-canvas-perf.html`

### Express Web 服务器
- `/`：返回对应后端的 HTML 驱动页面
- `/res/lottie.js`：lottie-web 播放器
- `/res/lottie.json`：Lottie 动画数据

### Chrome Tracing
- 收集类别：`blink`（渲染引擎）、`cc`（合成器）、`gpu`（GPU 命令）
- 输出为 Chrome Tracing 格式的 JSON 文件，可在 `chrome://tracing` 中查看
- 与 lottiecap.js 不同，此工具不截图而是收集底层性能 trace

### GPU 模式
启用 GPU 模式时：
- 使用非 headless 模式运行 Chrome
- 添加 `--ignore-gpu-blacklist/blocklist` 和 `--enable-gpu-rasterization` 参数
- 视口固定为 1000x1000 像素

### 超时处理
- 页面加载超时：60 秒
- 动画播放超时：60 秒
- 超时时关闭浏览器并以错误码退出

## 依赖关系

- **puppeteer**：Chrome 浏览器自动化
- **express**：本地 Web 服务器
- **fs**：文件系统
- **command-line-args** / **command-line-usage**：命令行解析
- **node-fetch**：HTTP 请求
- 外部资源：`lottie-web-perf.html`、`lottie-web-canvas-perf.html`
- **lottie-web**：Lottie 播放器库

## 设计模式与设计决策

- **Chrome Tracing 集成**：使用 Puppeteer 的 tracing API 收集底层性能数据，比 JavaScript 层面的计时更精确
- **双后端支持**：通过不同的 HTML 页面支持 SVG 和 Canvas 后端，便于对比两种渲染模式的性能
- **帧数感知**：从 Lottie JSON 提取帧数信息，确保测量完整的动画播放周期
- **与 lottiecap 互补**：lottiecap 关注视觉正确性（截图对比），此工具关注性能数据

## 性能考量

- Chrome Tracing 本身有轻微的性能开销，但对于帧级别的测量影响可忽略
- GPU 模式下的性能数据更接近真实用户体验
- 60 秒超时对大多数 Lottie 动画足够，但超复杂的动画可能需要调整
- tracing 数据文件可能很大，取决于动画帧数和复杂度

## 相关文件

- `tools/lottie-web-perf/lottie-web-perf.html` - SVG 后端驱动页面
- `tools/lottie-web-perf/lottie-web-canvas-perf.html` - Canvas 后端驱动页面
- `tools/lottiecap/lottiecap.js` - Lottie 截图工具（视觉正确性）
- `tools/perf-canvaskit-puppeteer/` - CanvasKit 性能测试（类似架构）
