# Skia 性能基准测试 Recipe (perf)

> 源文件: `infra/bots/recipes/perf.py`

## 概述

此 recipe 实现了 Skia 的 Swarming 性能基准测试（nanobench）流水线。它负责在各种硬件平台上运行 `nanobench` 工具来测量 Skia 图形操作的性能指标，并将结果上传到性能数据存储中。nanobench 是 Skia 的核心性能基准测试工具，用于测量绘图操作、编解码器等的速度。

## 架构位置

该 recipe 位于 Skia CI/CD 基础设施的 recipe 层，属于性能测试类 recipe。它是 Skia 持续性能监控体系的关键组成部分：

- **触发方式**: 由 Skia 任务调度器通过 Swarming 触发
- **上游**: 编译 recipe 产生的构建产物（nanobench 二进制）
- **下游**: `upload_nano_results` recipe 负责上传结果到 perf.skia.org
- **数据流**: nanobench 二进制 -> 性能 JSON 数据 -> GCS 存储 -> perf.skia.org

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `DEPS` | 列表 | 声明 recipe 的模块依赖，包括 flavor、env、run 等 |
| `TEST_BUILDERS` | 列表 | 定义用于 recipe 测试的构建器名称 |

## 公共 API 函数

### `perf_steps(api)`

核心性能测试步骤函数，执行以下流程：
1. 根据属性配置安装所需资源（SKP、图像、SVG、文本追踪等）
2. 如需上传，清理设备上的性能数据目录
3. 从 `nanobench_flags` 和 `nanobench_properties` 属性中解析命令行参数
4. 替换 Swarming 相关的占位符变量（`${SWARMING_BOT_ID}`、`${SWARMING_TASK_ID}`）
5. 配置资源路径（图像、SKP、SVG、文本追踪等）
6. 如需上传，配置输出 JSON 文件路径（含 revision 和时间戳）
7. 运行 nanobench
8. 将结果从设备复制到 Swarming 输出目录

### `RunSteps(api)`

Recipe 入口函数，初始化环境后调用 `perf_steps`，并在 `finally` 块中确保清理步骤执行。

### `GenTests(api)`

生成测试用例，覆盖 Android 和 Windows 两个平台，以及上传/不上传、CPU/GPU 等不同配置。

## 内部实现细节

- **属性驱动配置**: 所有测试参数（标志、属性、资源需求）均通过 recipe 属性传入，使得同一 recipe 可以服务多种构建配置
- **Swarming 变量替换**: 通过遍历属性字典，将 `${SWARMING_BOT_ID}` 和 `${SWARMING_TASK_ID}` 替换为实际值
- **字典排序**: 遍历 `props` 时使用 `sorted(props.keys())` 确保步骤顺序一致，便于结果比较和调试
- **时间戳生成**: 使用 UTC 时间的 Unix 时间戳作为输出文件名的一部分，确保唯一性
- **abort_on_failure=False**: nanobench 运行失败不立即中止，允许后续清理步骤执行
- **资源条件安装**: 通过布尔属性（images、skps、svgs 等）控制哪些资源需要安装到设备

## 依赖关系

- **env** -- 环境变量管理模块
- **flavor** -- 设备风格抽象层，处理不同平台（Android、iOS、桌面等）的差异
- **run** -- 步骤执行和失败检查模块
- **vars** -- 构建变量管理模块（builder 名称、swarming ID 等）
- **recipe_engine/file** -- 文件操作
- **recipe_engine/json** -- JSON 处理
- **recipe_engine/path** -- 路径操作
- **recipe_engine/platform** -- 平台检测
- **recipe_engine/properties** -- 构建属性
- **recipe_engine/raw_io** -- 原始 I/O 输出捕获
- **recipe_engine/step** -- 步骤执行
- **recipe_engine/time** -- 时间操作

## 设计模式与设计决策

- **Flavor 抽象**: 使用 `api.flavor` 抽象层隐藏不同设备类型（Android、桌面、iOS）的文件系统和命令执行差异
- **属性驱动**: 通过外部属性而非硬编码来配置测试参数，实现了一份 recipe 代码服务数百种不同的性能测试配置
- **try/finally 清理**: 确保即使测试失败也能执行设备清理步骤，防止资源泄露
- **上传条件控制**: 通过 `do_upload` 属性控制是否上传结果，Debug 构建通常不上传

## 性能考量

- 资源安装是主要的时间开销之一，通过条件安装（仅安装需要的资源类型）减少不必要的传输
- `create_clean_device_dir` 确保每次运行从干净状态开始，避免旧数据干扰结果
- nanobench 本身的运行时间取决于硬件和测试配置，recipe 不对其施加超时控制（由 Swarming 层管理）

## 相关文件

- `infra/bots/recipes/upload_nano_results.py` -- 性能结果上传 recipe
- `infra/bots/recipe_modules/flavor/` -- 设备风格抽象模块
- `infra/bots/recipe_modules/run/` -- 步骤执行模块
- `infra/bots/recipe_modules/vars/` -- 构建变量模块
- `tools/nanobench.cpp` -- nanobench 工具的源代码
