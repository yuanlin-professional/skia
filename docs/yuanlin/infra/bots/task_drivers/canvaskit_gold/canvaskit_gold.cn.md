# canvaskit_gold - CanvasKit Gold 图像测试任务驱动

> 源文件: `infra/bots/task_drivers/canvaskit_gold/canvaskit_gold.go`

## 概述

`canvaskit_gold` 构建并运行 CanvasKit 测试,将产生的图像(GM 测试)上传到 Skia Gold 图像比较服务。它使用 Bazel 构建和运行测试,提取测试输出的 ZIP 包中的 PNG 图像,然后通过 `goldctl` 工具上传到 Gold 进行视觉回归检测。

## 架构位置

属于 CanvasKit 的图像质量验证子系统,连接 Bazel 构建系统和 Gold 视觉回归检测服务。

## 主要类与结构体

- **`goldctlConfig`**: goldctl 配置(路径、commit、CL 信息、corpus、keys)

## 公共 API 函数

- **`main()`**: 解析标志(含 Bazel 和 Gold 相关)、运行测试、上传到 Gold
- **`bazelTest()`**: 执行 bazelisk test 命令(含 RBE 支持)
- **`uploadDataToGold()`**: 协调解压、goldctl 初始化、图像添加和最终化
- **`setupGoldctl()`**: goldctl auth 和 imgtest init
- **`addAllGoldImages()`**: 遍历 PNG 文件,调用 goldctl imgtest add
- **`finalizeGoldctl()`**: 调用 goldctl imgtest finalize 触发数据摄取

## 内部实现细节

- 使用 RBE (Remote Build Execution) 加速构建,设置 100 个并行任务
- 从 bazel-testlogs 路径提取 test.outputs/outputs.zip
- 文件名格式: `testname.optional_config.png`
- 支持 CL/patchset 的 tryjob 模式

## 依赖关系

- Bazelisk - Bazel 构建
- goldctl - Gold 命令行工具
- `go.skia.org/skia/infra/bots/task_drivers/common` - Bazel 公共工具

## 设计模式与设计决策

- **ZIP 提取**: 测试输出打包为 ZIP,解压后处理,避免依赖测试输出目录结构
- **文件名解析**: 通过 `.` 分隔符从文件名提取测试名和可选配置
- **RBE 并行**: 100 个远程执行任务加速测试

## 性能考量

- RBE 远程执行显著加速构建和测试
- Bazel 缓存在磁盘空间不足时清理
- 图像逐个上传到 Gold

## 相关文件

- `infra/bots/task_drivers/common/bazel_utils.go` - Bazel 工具函数
- `infra/bots/task_drivers/common/bazel_clean_step.go` - 缓存清理
