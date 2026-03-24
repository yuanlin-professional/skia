# run-wasm-gm-tests - WASM GM 和单元测试运行器

> 源文件: `tools/run-wasm-gm-tests/run-wasm-gm-tests.js`

## 概述

run-wasm-gm-tests.js 是一个 Node.js 命令行应用，使用 Puppeteer 驱动 Chrome 浏览器来运行 Skia 的 WASM 版 GM 测试和单元测试。它启动本地 Web 服务器提供 WASM 模块和测试资源，在浏览器中执行测试后收集渲染结果（PNG 图像和 JSON 元数据），并与已知哈希对比以检测回归。

## 架构位置

位于 `tools/run-wasm-gm-tests/` 目录，属于 Skia 持续集成和正确性验证工具集。与 Gold（图像对比系统）集成。

## 主要类与结构体

无类定义。程序由配置、服务器和浏览器驱动逻辑组成。

## 公共 API 函数

### 命令行选项
| 选项 | 说明 |
|------|------|
| `--js_file` | wasm_gm_tests.js 路径 |
| `--wasm_file` | wasm_gm_tests.wasm 路径 |
| `--known_hashes` | 已知哈希文件（不需重新写入的结果）|
| `--output` | 输出 JSON 和图像的目录 |
| `--resources` | 测试图像资源目录 |
| `--use_gpu` | GPU 模式 |
| `--timeout` | 超时秒数（默认 60）|
| `--batch_size` | 批处理大小（默认 50）|

## 内部实现细节

- Express 服务器提供 WASM 模块、HTML 页面和资源文件
- 浏览器通过 POST 请求将测试结果（PNG 数据）发回服务器
- 服务器在接收到图像后与 known_hashes 对比，仅写入新的/变更的结果
- 支持 SIMD 和 GPU 模式的 Chrome 启动参数配置
- 批处理设计避免单次执行过多测试导致页面主线程阻塞

## 依赖关系

- `puppeteer`, `express`, `body-parser` - Web 自动化和服务器
- `command-line-args`, `command-line-usage` - 命令行解析
- `fs`, `path` - 文件系统操作

## 设计模式与设计决策

- **客户端-服务器协作**: WASM 测试在浏览器中运行，结果通过 HTTP POST 回传
- **增量输出**: 已知哈希跳过写入，减少 Gold 系统的处理负载
- **批处理**: 将测试分批执行，在批次间释放浏览器主线程

## 性能考量

- batch_size 默认为 50，平衡执行效率和浏览器响应性
- 超时机制防止测试挂起

## 相关文件

- `modules/canvaskit/` - CanvasKit WASM 模块
- `tools/skottie-wasm-perf/skottie-wasm-perf.js` - 类似的 WASM 性能工具
