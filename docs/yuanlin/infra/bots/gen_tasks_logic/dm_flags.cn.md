# DM Flags - DM 测试标志生成

> 源文件: `infra/bots/gen_tasks_logic/dm_flags.go`

## 概述

`dm_flags.go` 是 Skia CI 系统中最大的标志生成文件之一（约 1800 行），负责为 DM（Skia 的主测试工具）生成命令行标志。它根据任务的硬件/软件配置确定渲染配置、跳过规则、GPU 线程设置、颜色空间选择等众多参数。

## 架构位置

位于 `infra/bots/gen_tasks_logic/` 包中，被 `dm()` 任务生成方法调用。是 Skia 测试基础设施中最复杂的配置文件之一。

## 主要类与结构体

无独立结构体。`dmFlags` 和 `keyParams` 函数定义在包级别。

## 公共 API 函数

- **`keyParams(parts map[string]string) []string`**: 生成 Gold 结果的键参数
- **`(b *TaskBuilder) dmFlags(internalHardwareLabel string)`**: 生成 DM 命令行标志

## 内部实现细节

1. **配置选择**:
   - SwiftShader: `vk`/`vkdmsaa`/`grvk`（Graphite）
   - CPU 模式: `8888`, BonusConfigs (`r8`, `565`, `pic-8888`, `serialize-8888`), PDF
   - GPU 模式: `gl`/`gles` + `dft` + MSAA + dMSAA 变体
   - Vulkan/Metal/ANGLE/Graphite 各有专门的配置逻辑
2. **辅助函数**（闭包）:
   - `hasConfig`: 检查配置是否存在
   - `filter`/`remove`/`removeContains`: 配置列表操作
   - `suffix`: 批量添加后缀
   - `skip(config, src, srcOptions, name)`: 添加跳过规则
3. **跳过规则系统**: 使用四元组 (config, src, srcOptions, name) 定义跳过条件
   - `_` 作为通配符匹配所有值
   - `~` 前缀表示否定匹配
4. **硬件特定跳过**: 针对 Intel、NVIDIA、Adreno、Mali、Apple GPU 等的已知问题
5. **GPU 线程控制**: 32 位系统限制 4 线程，低内存设备使用主线程
6. **颜色空间配置**: sRGB、narrow、wide gamut 等变体
7. **随机测试**: `--randomProcessorTest` 用于 GPU 浮点优化测试

## 依赖关系

- `go.skia.org/infra/task_scheduler/go/specs`: 占位符常量
- `github.com/golang/glog`: 日志
- 标准库: `fmt`, `sort`, `strconv`, `strings`

## 设计模式与设计决策

- 大量条件分支实现精细化的配置控制
- 跳过规则关联 bug ID 便于追踪和清理
- 闭包封装配置操作逻辑，减少重复代码
- `keyParams` 排除 `role` 和 `test_filter`，因为这些不影响测试结果

## 性能考量

- 跳过规则减少不必要的测试执行时间
- `--threads` 限制防止低内存设备 OOM
- `--dontReduceOpsTaskSplitting` 针对特定硬件优化 GPU 任务调度

## 相关文件

- `infra/bots/gen_tasks_logic/nano_flags.go`: 类似的 Nanobench 标志生成
- `infra/bots/gen_tasks_logic/task_builder.go`: TaskBuilder 定义
- `dm/`: DM 测试工具源码
