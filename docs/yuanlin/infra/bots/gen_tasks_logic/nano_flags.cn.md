# Nano Flags - Nanobench 性能测试标志生成

> 源文件: `infra/bots/gen_tasks_logic/nano_flags.go`

## 概述

`nano_flags.go` 负责为 Skia 的 Nanobench 性能测试工具生成命令行标志。它根据任务的硬件配置（GPU 型号、操作系统、架构等）和软件配置（Vulkan、Metal、ANGLE、Graphite 等后端）自动确定合适的渲染配置、MSAA 采样数和测试过滤规则。

## 架构位置

位于 `infra/bots/gen_tasks_logic/` 包中，被 `perf()` 任务生成函数调用。是性能测试配置的核心决策逻辑。

## 主要类与结构体

无独立结构体定义，方法挂在 `TaskBuilder` 上。

## 公共 API 函数

- **`(b *TaskBuilder) nanobenchFlags(doUpload bool)`**: 生成 Nanobench 命令行标志

## 内部实现细节

1. **配置选择逻辑**:
   - CPU 模式: `8888` + `nonrendering`，BonusConfigs 变体添加 `f16`/`srgb-rgba` 等
   - GPU 模式: 根据平台选择 `gl`/`gles` 前缀
   - MSAA 采样数: 移动端 4x，桌面端 8x，Intel GPU 禁用，iOS 禁用
   - Vulkan: `vk`/`vkmsaa8`/`vkdmsaa` 配置
   - Metal: `mtl`/`mtlmsaa4/8`/`mtlreducedshaders` 配置
   - ANGLE: `angle_d3d11_es2/3` + MSAA 变体
   - Graphite + Dawn: `grdawn_d3d11/d3d12/mtl/vk/gl/gles`
   - Graphite + Native: `grmtl`/`grvk`
   - SwiftShader: 软件 Vulkan 配置
2. **内部采样数** (`--internalSamples`): 移动端和 Graphite 使用 4，其他 8
3. **测试过滤** (`match`): 跳过已知有问题的测试用例
   - Android: 跳过 blurroundrect, patch_grid 等
   - iOS: 跳过 keymobi, path_hairline 等
   - 特定 GPU 型号的已知问题
4. **性能调优**: ASAN/Debug 使用 1 次循环/采样，keepAlive 防止超时
5. **结果上传**: 根据 `doUpload` 配置 JSON 输出和属性标记

## 依赖关系

- `go.skia.org/infra/task_scheduler/go/specs`: 占位符常量
- 同包: `TaskBuilder`, `Parts`

## 设计模式与设计决策

- 声明式配置: 通过条件匹配构建标志列表
- 硬件感知: 针对特定 GPU 型号和 OS 版本的精细化配置
- Bug 追踪: 每个跳过规则都关联 skbug.com 或 b/ 链接
- `dontReduceOpsTaskSplitting` 针对特定硬件优化

## 性能考量

此文件生成的标志直接影响性能测试的执行效率和结果准确性。

## 相关文件

- `infra/bots/gen_tasks_logic/dm_flags.go`: 类似的 DM 测试标志生成
- `infra/bots/gen_tasks_logic/task_builder.go`: TaskBuilder 定义
- `tools/perf/`: Nanobench 源码
