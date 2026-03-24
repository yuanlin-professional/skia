# Lottie 电影胶片截图工具

> 源文件: `tools/lottiecap/lottiecap.js`

## 概述

此文件是一个命令行 Node.js 应用程序，使用 Puppeteer 控制 Chrome 浏览器来将 Lottie 动画文件渲染为 5x5 电影胶片（filmstrip）格式的 1000x1000 PNG 图片。该工具主要用于 Skia Gold 测试系统，通过对比不同版本的电影胶片截图来检测 Lottie 渲染的回归问题。支持 SVG 和 Canvas 两种 lottie-web 渲染后端。

## 架构位置

- 所属模块：`tools/lottiecap/`（Lottie 截图捕获工具）
- 角色：CI/CD 流水线中的 Lottie 渲染截图工具
- 上游输入：Lottie JSON 动画文件
- 下游输出：PNG 电影胶片图片 / Gold 测试服务器

## 主要类与结构体

此文件为过程式 Node.js 脚本，无类定义。

### 命令行选项
| 选项 | 类型 | 描述 |
|------|------|------|
| `input` | file | Lottie JSON 文件（必需） |
| `output` | file | 输出 PNG 文件（默认 filmstrip.png） |
| `renderer` | mode | 渲染后端：svg 或 canvas（默认 svg） |
| `port` | number | 本地服务器端口（默认 8081） |
| `lottie_player` | string | lottie.min.js 路径 |
| `post_to` | string | Gold Ingestion 的 POST URL |
| `in_docker` | boolean | 是否在 Docker 中运行 |
| `skip_automation` | boolean | 跳过自动截图（调试用） |

## 公共 API 函数

### `wait(ms)`
异步等待指定毫秒数的工具函数。

### `driveBrowser()`（异步）
主驱动函数：
1. 启动 Puppeteer Chrome 实例（headless 模式）
2. 导航到本地服务器上的驱动页面
3. 等待 25 个动画帧（tiles）绘制完成
4. 截取 1000x1000 区域的 PNG 截图
5. 可选将截图以 base64 格式 POST 到 Gold 服务器

## 内部实现细节

### Express Web 服务器
- `/`：返回 `driver.html`（电影胶片绘制页面）
- `/lottie.js`：返回 lottie-web 播放器库
- `/lottie.json`：返回输入的 Lottie JSON 数据

### 渲染后端选择
通过 URL hash 传递渲染模式（`#svg` 或 `#canvas`）给 driver.html 页面。

### 电影胶片生成
- driver.html 将 Lottie 动画的 25 个均匀分布的帧渲染为 5x5 网格
- 每个 tile 200x200 像素，总计 1000x1000 像素
- 使用 `window._tileCount` 变量跟踪已完成的 tile 数量

### Docker 支持
在 Docker 环境中使用系统安装的 Chrome（`/usr/bin/google-chrome-stable`）和 `--no-sandbox` 参数。

### Gold 集成
- 当指定 `post_to` URL 时，将截图以 base64 编码 POST 到 Gold Ingestion 端点
- JSON payload 包含 `data`（base64 图片）和 `test_name`（文件名）

## 依赖关系

- **puppeteer**：Chrome 浏览器自动化
- **express**：本地 Web 服务器
- **fs**：文件系统
- **command-line-args** / **command-line-usage**：命令行解析
- **node-fetch**：HTTP 请求（Gold 上报）
- 外部资源：`driver.html`（同目录下的 HTML 驱动页面）
- **lottie-web**：Lottie 动画播放器库

## 设计模式与设计决策

- **服务器+浏览器架构**：与 CanvasKit 性能测试使用相同的本地服务器模式
- **电影胶片格式**：5x5 网格在单张图片中捕获 25 个关键帧，便于视觉对比
- **渲染无关**：通过 URL hash 切换渲染后端，相同的截图流程适用于 SVG 和 Canvas
- **超时容错**：多处设置 20 秒超时，对于超大或有错误的 JSON 文件优雅退出

## 性能考量

- 20 秒页面加载超时和 20 秒帧绘制超时提供了合理的时间窗口
- 截图使用 PNG 格式，无损但文件较大
- base64 编码增加约 33% 的数据量，但简化了 HTTP 传输
- headless 模式避免了 GUI 渲染开销

## 相关文件

- `tools/lottiecap/driver.html` - 电影胶片绘制的 HTML 页面
- `tools/lottie-web-perf/lottie-web-perf.js` - Lottie 性能测试工具
- `modules/canvaskit/` - CanvasKit 中的 Skottie（Skia 原生 Lottie 播放器）
