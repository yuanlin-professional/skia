# Skottie-WASM 与 Lottie-Web 性能测试 Recipe (perf_skottiewasm_lottieweb)

> 源文件: `infra/bots/recipes/perf_skottiewasm_lottieweb.py`

## 概述

此 recipe 运行 Skottie-WASM 和 Lottie-Web 的渲染性能测试，通过 Chrome 浏览器中的追踪（tracing）机制测量 Lottie 动画的帧渲染时间。它支持三种渲染器：Skottie WASM（Skia 的 WebAssembly Lottie 实现）、Lottie-Web SVG 后端和 Lottie-Web Canvas 后端。测试在 Node.js + Puppeteer 环境中运行，结果输出到 perf.skia.org。

## 架构位置

此 recipe 是 Skia CI 性能监控体系中 Web 端 Lottie 动画性能测试的核心：

- **数据流**: Lottie JSON 文件 -> Puppeteer + Chrome -> 追踪 JSON -> parse_lottieweb_trace.py -> 性能 JSON -> perf.skia.org
- **对比维度**: Skottie WASM vs Lottie-Web (SVG) vs Lottie-Web (Canvas)
- **执行环境**: 本机 Node.js + Puppeteer（非 Docker）

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `DEPS` | 列表 | 依赖模块列表 |
| `LOTTIE_WEB_EXCLUDE` | 列表 | Lottie-Web SVG 后端排除的文件列表 |
| `SKOTTIE_WASM_EXCLUDE` | 列表 | Skottie WASM 排除的文件列表 |
| `LOTTIE_WEB_CANVAS_EXCLUDE` | 列表 | Lottie-Web Canvas 后端排除的文件列表 |

### 排除列表说明

排除列表包含在特定渲染器中已知存在问题的 Lottie 文件：
- **静态场景**: 无实际动画的文件（mask1.json、stacking.json 等），追踪数据不足
- **不支持的特性**: 依赖 expressions 等 Skottie 不支持的特性
- **超时文件**: 渲染时间过长的文件（beetle.json 等）
- **错误文件**: 在特定后端运行出错的文件

## 公共 API 函数

### `RunSteps(api)`

Recipe 入口，根据构建器名称选择渲染模式：

1. **SkottieWASM 模式**:
   - 使用 `skottie-wasm-perf.js` Node.js 应用
   - 传入 `canvaskit.js` 和 `canvaskit.wasm` 路径
   - 应用 `SKOTTIE_WASM_EXCLUDE` 排除列表

2. **LottieWeb 模式**:
   - 使用 `lottie-web-perf.js` Node.js 应用
   - 根据 `Canvas` 标记选择 canvas 或 svg 后端
   - 应用对应的排除列表

3. **GPU 支持**: 如构建器为 GPU 类型，添加 `--use_gpu` 参数

4. **npm 安装**: 在性能应用目录中运行 `npm install`

5. **逐文件测试**: 遍历每个 Lottie 文件，运行性能应用并解析追踪输出（带重试机制）

6. **构建输出 JSON**: 组合所有文件的性能数据，提取构建器名称中的配置键值

### `parse_trace(trace_json, lottie_filename, api, renderer)`

解析追踪 JSON，计算帧渲染时间指标（最大/最小/平均值，单位微秒）。委托给外部脚本 `parse_lottieweb_trace.py`。

### `GenTests(api)`

生成 8 个测试用例，覆盖 Skottie WASM (CPU/GPU/trybot)、Lottie-Web SVG (normal/trybot)、Lottie-Web Canvas (normal/trybot)、以及未识别构建器的异常情况。

## 内部实现细节

- **构建器名称路由**: 通过检查构建器名称中的 `SkottieWASM` 或 `LottieWeb` 子串来确定渲染模式
- **Canvas 后端检测**: 在 LottieWeb 模式下，进一步检查 `Canvas` 子串确定使用 canvas 还是 svg 后端
- **排除列表分层**: Canvas 排除列表继承 SVG 排除列表并添加额外条目，反映 Canvas 后端的兼容性更差
- **文件过滤**: 跳过非 `.json` 文件（如 `LICENSE`），以及排除列表中的文件
- **重试机制**: `api.run.with_retry` 以 3 次重试运行性能命令，应对偶发的 Chrome 崩溃（参见 skbug.com/40040508）
- **构建器名称正则解析**: 与 `perf_skottietrace.py` 相同的正则表达式从构建器名称提取 os、compiler、model 等键值
- **infra_step=True**: 性能应用运行标记为基础设施步骤

## 依赖关系

- **flavor** -- 设备抽象层（用于获取 host_dirs）
- **checkout** -- 代码检出
- **env** -- 环境变量管理
- **infra** -- 基础设施资源（`parse_lottieweb_trace.py`）
- **run** -- 步骤执行（含重试）
- **vars** -- 构建变量
- **recipe_engine/context** -- 执行上下文（cwd、env、env_prefixes）
- **recipe_engine/file** -- 文件操作（listdir、write_text）
- **recipe_engine/json** -- JSON 处理
- **recipe_engine/path** -- 路径操作
- **recipe_engine/properties** -- 构建属性
- **recipe_engine/step** -- 步骤执行
- **recipe_engine/time** -- 时间操作

## 设计模式与设计决策

- **多渲染器统一框架**: 用一个 recipe 覆盖三种渲染器（Skottie WASM、Lottie-Web SVG、Lottie-Web Canvas），通过构建器名称路由选择
- **排除列表管理**: 将已知问题的文件硬编码在排除列表中，并附带详细注释说明排除原因，便于维护
- **外部追踪解析**: 将追踪解析逻辑委托给独立的 Python 脚本，便于单独测试
- **Node.js 生态**: 使用 Node.js + Puppeteer 运行浏览器自动化测试，是 Web 端测试的标准方案
- **DISPLAY 环境变量**: 设置 `DISPLAY=:0` 支持 Linux 上的 GUI 渲染
- **Trybot 支持**: 自动检测 trybot 并附加代码审查元数据

## 性能考量

- **npm install 开销**: 每次运行都执行 `npm install`，但 node_modules 缓存可以减少重复下载
- **逐文件运行**: 每个 Lottie 文件单独启动 Puppeteer + Chrome，有显著的进程启动开销
- **重试开销**: 最多 3 次重试在最坏情况下将单个文件的测试时间增加 3 倍
- **排除列表优化**: 跳过已知问题文件避免浪费时间在注定失败或数据不足的测试上
- **浮点精度截断**: 将结果限制在 2 位小数，减少因浮点精度差异导致的虚假性能变化

## 相关文件

- `tools/skottie-wasm-perf/skottie-wasm-perf.js` -- Skottie WASM 性能测试 Node.js 应用
- `tools/lottie-web-perf/lottie-web-perf.js` -- Lottie-Web 性能测试 Node.js 应用
- `infra/bots/recipe_modules/infra/resources/parse_lottieweb_trace.py` -- 追踪解析脚本
- `infra/bots/recipes/perf_skottietrace.py` -- Skottie 原生追踪性能测试（非 WASM）
- `modules/canvaskit/` -- CanvasKit（Skia WASM）源代码
