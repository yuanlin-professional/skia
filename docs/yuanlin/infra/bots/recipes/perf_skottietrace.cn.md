# Skottie 追踪性能测试 Recipe (perf_skottietrace)

> 源文件: `infra/bots/recipes/perf_skottietrace.py`

## 概述

此 recipe 使用 DM（Skia 的测试驱动程序）在 Lottie 动画文件上开启追踪（trace）功能，然后解析追踪输出以计算帧渲染时间等性能指标。解析后的数据以 JSON 格式输出，供 perf.skia.org 性能监控平台摄取。设计文档参见 `go/skottie-tracing`。

Skottie 是 Skia 对 Lottie 动画格式的高性能渲染实现，此 recipe 专门用于监测 Skottie 的 `seek` 和 `render` 操作的性能。

## 架构位置

此 recipe 是 Skia CI 性能监控体系中 Skottie 专项性能测试的核心组件：

- **数据流**: Lottie 文件 -> DM (带追踪) -> 追踪 JSON -> parse_skottie_trace.py -> 性能 JSON -> perf.skia.org
- **触发**: 由 Skia 任务调度器通过 Swarming 触发
- **支持平台**: Android (GPU/CPU)、Debian (GPU/CPU)

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `DEPS` | 列表 | 依赖模块列表 |
| `SEEK_TRACE_NAME` | 常量 | seek 追踪事件名称: `skottie::Animation::seek` |
| `RENDER_TRACE_NAME` | 常量 | render 追踪事件名称: `skottie::Animation::render` |
| `EXPECTED_DM_FRAMES` | 常量 | DM 预期渲染帧数: 25 |

## 公共 API 函数

### `perf_steps(api)`

核心测试执行函数，流程如下：
1. 创建设备上的 DM 输出目录
2. 处理 Android 平台的 CIPD 符号链接问题（复制文件以去除符号链接）
3. 遍历每个 Lottie 文件：
   - 配置 DM 命令行参数（包括追踪匹配和输出路径）
   - 根据 GPU/CPU 配置选择渲染配置（gles/8888）
   - 运行 DM
   - 读取并解析追踪输出
   - 清理追踪文件
4. 构建输出 JSON（包含 git hash、Swarming 信息、构建器键值、性能结果）
5. 对 trybot 构建附加 issue/patchset 信息
6. 从构建器名称中通过正则提取配置键值
7. 将结果 JSON 写入性能数据目录

### `get_trace_match(lottie_filename, is_android)`

为 DM 的 `--match` 参数生成正则表达式。在 Android 平台上转义标点符号以避免 adb shell 转义问题。

- **参数**: `lottie_filename` -- Lottie 文件名, `is_android` -- 是否为 Android 平台
- **返回**: 转义后的匹配正则字符串

### `parse_trace(trace_json, lottie_filename, api)`

解析追踪 JSON 输出，计算单帧时间。帧时间 = seek 时间 + render 时间（忽略第一次 seek，因为那是构造函数调用）。

- **返回字典结构**:
  - `frame_max_us`: 最大帧时间（微秒）
  - `frame_min_us`: 最小帧时间（微秒）
  - `frame_avg_us`: 平均帧时间（微秒）

### `RunSteps(api)`

Recipe 入口，初始化环境、安装资源和 Lottie 文件、执行性能测试。

### `GenTests(api)`

生成 5 个测试用例：Android GPU、Debian GPU、Debian CPU、解析错误、trybot。

## 内部实现细节

- **Android 符号链接问题**: 由于 CIPD 默认使用符号链接安装文件，而 adb push 不能正确处理符号链接，因此需要先在主机端复制一份去除符号链接的副本，再推送到设备（参见 http://b/72366966）
- **追踪匹配过滤**: 使用 `--traceMatch skottie` 限制追踪范围，防止内存溢出
- **Android 标点转义**: 在 Android 上通过 adb shell 传递命令时，标点符号需要反斜杠转义（除了含空格的情况，`subprocess.list2cmdline` 会自动加引号）
- **构建器名称解析**: 使用正则表达式从构建器名称中提取 os、compiler、model 等配置键值
- **浮点精度控制**: 使用 `"%.2f"` 格式化将浮点结果限制在 2 位精度
- **外部脚本调用**: 追踪解析委托给 `parse_skottie_trace.py` 脚本执行

## 依赖关系

- **flavor** -- 设备抽象层
- **infra** -- 基础设施工具资源（包含 `parse_skottie_trace.py`）
- **run** -- 步骤执行
- **vars** -- 构建变量
- **recipe_engine/context** -- 执行上下文管理
- **recipe_engine/file** -- 文件操作
- **recipe_engine/json** -- JSON 处理
- **recipe_engine/path** -- 路径操作
- **recipe_engine/step** -- 步骤执行
- **recipe_engine/time** -- 时间操作
- **recipe_engine/properties** -- 构建属性
- **recipe_engine/raw_io** -- 原始 I/O

## 设计模式与设计决策

- **追踪分析模式**: 利用 DM 的内建追踪机制捕获 Skottie 的 seek/render 调用时间，而非简单的端到端计时
- **逐文件处理**: 每个 Lottie 文件单独运行 DM 并解析，避免多文件追踪数据混合
- **外部脚本解耦**: 将复杂的追踪解析逻辑放在独立的 Python 脚本中，便于单独测试和维护
- **Trybot 支持**: 自动检测 trybot 构建并附加代码审查相关的元数据
- **容错设计**: `abort_on_failure=False` 允许单个文件失败而不影响其他文件的测试

## 性能考量

- **内存管理**: 使用 `--traceMatch skottie` 过滤追踪事件，防止全量追踪导致的 OOM
- **符号链接复制开销**: Android 平台上的文件复制步骤增加了额外时间，但这是必要的兼容性处理
- **逐文件运行**: 每个 Lottie 文件启动独立的 DM 进程有一定开销，但保证了追踪数据的隔离性
- **追踪文件清理**: 每个文件处理后立即删除追踪文件，防止设备存储空间不足

## 相关文件

- `infra/bots/recipe_modules/infra/resources/parse_skottie_trace.py` -- 追踪解析脚本
- `infra/bots/recipes/perf_skottiewasm_lottieweb.py` -- Skottie WASM 和 Lottie-Web 性能测试
- `infra/bots/recipe_modules/flavor/` -- 设备风格抽象模块
- `modules/skottie/` -- Skottie 模块源代码
- `dm/` -- DM 测试驱动程序源代码
