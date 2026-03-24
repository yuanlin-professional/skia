# Skia DM 测试 Recipe (test)

> 源文件: `infra/bots/recipes/test.py`

## 概述

此 recipe 是 Skia 的核心测试驱动 recipe，负责在各种硬件平台和配置下运行 DM（Skia 的图形测试驱动程序）。DM 执行 Skia 的渲染正确性测试，生成图像输出并与 Gold（Skia 的视觉回归测试平台）中的基准图像进行比对。此 recipe 支持 Android、Windows、Linux 等多种平台，以及 GPU（Vulkan、OpenGL）和 CPU 多种渲染后端。

## 架构位置

该 recipe 位于 Skia CI 测试流水线的核心位置：

- **上游**: 编译 recipe 产生的 DM 二进制文件和相关资源
- **下游**: `upload_dm_results.py` 上传结果到 GCS，Gold 服务进行视觉比对
- **覆盖范围**: 是 Skia CI 中运行实例最多的 recipe 之一，覆盖数百种构建配置
- **数据流**: DM 二进制 + 测试资源 -> DM 执行 -> 图像/JSON 输出 -> Gold 上传

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `DEPS` | 列表 | 依赖模块列表，包含 flavor、gold_upload、env 等 |
| `DM_JSON` | 常量 | DM JSON 输出文件名: `dm.json` |
| `TEST_BUILDERS` | 列表 | 用于 recipe 测试的构建器名称列表 |

## 公共 API 函数

### `test_steps(api)`

核心测试执行函数，流程如下：

1. **安装资源**: 根据属性配置安装图像、Lottie 文件、SKP、SVG 等测试资源
2. **准备输出目录**: 创建主机端和设备端的 DM 输出目录
3. **获取已知哈希列表**: 从 Gold 下载 `uninteresting_hashes.txt`，包含已知的测试输出哈希，DM 可以跳过这些测试以节省时间
4. **构建 DM 参数**: 从 `dm_flags` 和 `dm_properties` 属性解析命令行参数，替换 Swarming 变量
5. **配置资源路径**: 设置图像、SKP、SVG、Lottie、字体等资源的设备路径
6. **运行 DM**: 以 `abort_on_failure=False` 执行，允许部分测试失败
7. **上传结果**: 将设备端结果复制到主机端，通过 Gold 上传（Windows 除外）

### `RunSteps(api)`

Recipe 入口，初始化环境，执行 `test_steps`，确保清理步骤执行。

### `GenTests(api)`

生成 4 个测试用例，覆盖：
- Android Vulkan GPU 测试
- Lottie 动画测试
- Windows GPU 测试
- Fontations 字体渲染测试

## 内部实现细节

- **Gold 哈希优化**: 通过 `uninteresting_hashes.txt` 跳过已知结果的测试，显著减少运行时间。该文件从 `gold_hashes_url` 下载
- **哈希文件传输**: 先下载到主机临时目录，再通过 `copy_file_to_device` 传输到设备
- **Swarming 变量替换**: 将 `${SWARMING_BOT_ID}` 和 `${SWARMING_TASK_ID}` 占位符替换为实际值
- **SVG 子目录**: SVG 资源在 `svg_dir` 的 `svg` 子目录中（参见 skbug.com/40042605）
- **Fontations 字体路径**: 当构建器配置包含 `Fontations` 时，额外配置 `--fontTestDataPath`
- **Windows Gold 上传限制**: Windows 平台跳过 Gold 上传（参见 chromium bug 1192611）
- **属性排序**: 使用 `sorted(props.keys())` 确保步骤顺序一致

## 依赖关系

- **env** -- 环境变量管理
- **flavor** -- 设备抽象层（Android、iOS、桌面等）
- **gold_upload** -- Gold 测试结果上传
- **run** -- 步骤执行和失败检查
- **vars** -- 构建变量管理
- **recipe_engine/context** -- 执行上下文
- **recipe_engine/file** -- 文件操作
- **recipe_engine/path** -- 路径操作
- **recipe_engine/platform** -- 平台检测
- **recipe_engine/properties** -- 构建属性
- **recipe_engine/raw_io** -- 原始 I/O
- **recipe_engine/step** -- 步骤执行

## 设计模式与设计决策

- **属性驱动测试配置**: 所有 DM 标志和属性通过外部传入，一份 recipe 代码服务数百种测试配置
- **Gold 哈希跳过**: 这是关键的优化策略 -- 通过跳过已知输出的测试，将运行时间从小时级别降到分钟级别
- **哈希文件获取是强制性的**: `abort_on_failure=True` 和 `fail_build_on_failure=True` 确保 Gold 服务不可用时及早发现
- **Flavor 抽象**: 通过 flavor 模块统一处理不同设备类型的文件传输和命令执行
- **try/finally 清理**: 确保设备清理步骤始终执行
- **平台特殊处理**: Windows 跳过 Gold 上传是已知问题的临时解决方案

## 性能考量

- **哈希跳过**: 最重要的性能优化，通过 `--uninterestingHashesFile` 让 DM 跳过已有结果的测试
- **资源条件安装**: 仅安装所需的资源类型（images/skps/svgs/lotties），减少设备传输时间
- **设备目录清理**: `create_clean_device_dir` 和 `create_clean_host_dir` 确保干净的测试环境
- **abort_on_failure=False**: 允许部分测试失败但继续运行，最大化单次执行的测试覆盖率

## 相关文件

- `infra/bots/recipes/upload_dm_results.py` -- DM 结果上传 recipe
- `infra/bots/recipe_modules/flavor/` -- 设备抽象模块
- `infra/bots/recipe_modules/gold_upload/` -- Gold 上传模块
- `infra/bots/recipe_modules/gold_upload/resources/get_uninteresting_hashes.py` -- 哈希下载脚本
- `dm/` -- DM 测试驱动程序源代码
- `tools/flags/` -- DM 命令行标志定义
