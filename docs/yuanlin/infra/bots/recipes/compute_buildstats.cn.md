# 构建产物统计分析 Recipe (compute_buildstats)

> 源文件: `infra/bots/recipes/compute_buildstats.py`

## 概述

此 recipe 分析编译产物的各项指标，包括文件大小、代码段分布等信息。它专门处理三种类型的文件：`libskia.so`（Skia 共享库）、`skottie_tool`（Skottie 工具）和 `dm`（测试驱动程序）。对于 `libskia.so`，使用 `bloaty`（二进制分析工具）进行详细的段分析并生成性能 JSON；对于其他二进制文件，生成代码大小的 HTML 树状图。分析结果上传到 perf.skia.org 用于监控二进制大小的变化趋势。

## 架构位置

该 recipe 位于 Skia CI 构建分析流水线中：

- **触发**: 在编译完成后由 BuildStats 任务触发
- **上游**: 编译 recipe 产生的二进制文件
- **下游**: `upload_buildstats_results.py` 上传分析结果到 GCS -> perf.skia.org
- **工具依赖**: bloaty（二进制大小分析器）、Docker（用于 treemap 生成）

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `DEPS` | 列表 | 依赖模块列表 |
| `MAGIC_SEPERATOR` | 常量 | 输出分段分隔符: `#$%^&*` |
| `TOTAL_SIZE_BYTES_KEY` | 常量 | JSON 中的总大小键名: `total_size_bytes` |
| `sample_cpp` | 字符串 | 测试用的模拟分析输出 |

## 公共 API 函数

### `RunSteps(api)`

Recipe 入口，依次搜索并分析三种二进制文件：
1. `libskia.so` -- 调用 `analyze_cpp_lib` 进行 bloaty 分析
2. `skottie_tool` -- 调用 `make_treemap` 生成树状图
3. `dm` -- 调用 `make_treemap` 生成树状图

### `keys_and_props(api)`

构建性能 JSON 所需的键值对和属性字符串。
- **keys**: 从构建器配置中提取所有非 `role` 的键值对
- **props**: 包含 gitHash、swarming IDs，以及 trybot 的 issue/patchset

### `analyze_cpp_lib(api, checkout_root, out_dir, files)`

使用 bloaty 分析 C++ 共享库，流程：
1. 调用 `buildstats_cpp.py` 脚本执行分析
2. 解析使用 `MAGIC_SEPERATOR` 分段的输出
3. 将性能 JSON 添加到步骤日志中
4. 提取 `total_size_bytes` 作为步骤输出属性

### `make_treemap(api, checkout_root, out_dir, files)`

为二进制文件生成 HTML 代码大小树状图：
1. 设置 Docker 配置环境变量
2. 调用 `make_treemap.py` 脚本（内部使用 Docker）
3. 输出为 zip 格式的 HTML 文件

### `GenTests(api)`

生成两个测试用例：普通 CI 构建和 trybot 构建。

## 内部实现细节

- **MAGIC_SEPARATOR 协议**: `buildstats_cpp.py` 脚本使用 `#$%^&*` 作为输出分段分隔符，sections[0] 为空/无用，sections[1] 为文本报告，sections[2] 为性能 JSON
- **ast.literal_eval**: 使用 `ast.literal_eval` 而非 `json.loads` 解析 JSON 字符串，这是一个安全但非标准的选择
- **output property**: 通过 `result.presentation.properties` 将二进制大小作为构建步骤的输出属性，可在 Buildbucket UI 中直接查看
- **Docker treemap**: 树状图生成依赖 Docker 环境（通过 `DOCKER_CONFIG` 环境变量），可能使用专门的分析容器
- **glob 搜索**: 对每种二进制文件使用 `glob_paths` 搜索，允许文件不存在的情况

## 依赖关系

- **checkout** -- 代码检出（用于获取分析脚本）
- **env** -- 环境变量管理
- **run** -- 步骤执行
- **vars** -- 构建变量
- **recipe_engine/context** -- 执行上下文
- **recipe_engine/file** -- 文件操作（glob_paths、ensure_directory）
- **recipe_engine/path** -- 路径操作
- **recipe_engine/properties** -- 构建属性
- **recipe_engine/raw_io** -- 原始输出捕获（stdout）
- **recipe_engine/step** -- 步骤执行

## 设计模式与设计决策

- **多文件类型分析**: 一个 recipe 处理多种二进制文件类型，每种类型使用专门的分析策略
- **外部脚本委托**: 具体分析逻辑委托给 `buildstats_cpp.py` 和 `make_treemap.py`，保持 recipe 简洁
- **分段输出协议**: 使用特殊分隔符在标准输出中传递多种数据，简单但有效
- **输出属性**: 利用 recipe 引擎的 presentation properties 机制，使二进制大小可以在 UI 和下游任务中直接访问
- **Trybot 支持**: 自动为 trybot 构建附加代码审查元数据，支持在 CQ 中监控二进制大小变化

## 性能考量

- bloaty 分析大型共享库（如 `libskia.so`）可能需要数十秒
- Docker 启动和树状图生成有一定开销
- 对多个二进制文件的分析是顺序执行的
- glob 搜索范围限定在构建输出目录中，效率较高

## 相关文件

- `infra/bots/buildstats/buildstats_cpp.py` -- C++ 库分析脚本
- `infra/bots/buildstats/make_treemap.py` -- 树状图生成脚本
- `infra/bots/recipes/upload_buildstats_results.py` -- 构建统计结果上传 recipe
- bloaty -- 二进制大小分析工具（通过 CIPD 安装）
