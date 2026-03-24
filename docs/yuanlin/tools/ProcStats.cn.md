# ProcStats - 进程统计信息

> 源文件:
> - [tools/ProcStats.h](../../tools/ProcStats.h)
> - [tools/ProcStats.cpp](../../tools/ProcStats.cpp)

## 概述

ProcStats 提供跨平台的进程内存使用统计功能，支持查询当前和最大驻留集大小（RSS）。支持 macOS/iOS、Linux/Android、Windows 和 Fuchsia 平台，不支持的平台返回 -1。主要用于 DM 和 nanobench 等工具程序的内存监控。

## 架构位置

位于 `tools/` 目录下，属于底层系统工具组件。通过 `sk_tools` 命名空间组织，被测试运行器和基准测试工具调用以报告内存使用情况。

## 主要类与结构体

本模块不包含类定义，仅提供 `sk_tools` 命名空间下的全局函数。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `getCurrResidentSetSizeBytes()` | 获取当前 RSS（字节），不支持返回 -1 |
| `getMaxResidentSetSizeBytes()` | 获取最大 RSS（字节），不支持返回 -1 |
| `getCurrResidentSetSizeMB()` | 获取当前 RSS（MB），封装字节版本 |
| `getMaxResidentSetSizeMB()` | 获取最大 RSS（MB），封装字节版本 |

## 内部实现细节

### 最大 RSS 实现
- **macOS/iOS**：`getrusage(RUSAGE_SELF)` 的 `ru_maxrss`，Darwin 直接返回字节
- **Linux/Android**：`getrusage` 的 `ru_maxrss`，Linux 返回 KB 需要 *1024
- **Windows**：`GetProcessMemoryInfo` 的 `PeakWorkingSetSize`
- **Fuchsia**：`zx_object_get_info` 获取 `ZX_INFO_TASK_STATS`，计算私有 + 共享内存

### 当前 RSS 实现
- **macOS/iOS**：`task_info(MACH_TASK_BASIC_INFO)` 获取 `resident_size`
- **Linux/Android**：读取 `/proc/self/statm` 的第二个字段（rss pages）乘以页大小
- **Windows**：`GetProcessMemoryInfo` 的 `WorkingSetSize`

### MB 转换
字节版本结果 < 0 时直接返回 -1，否则进行 /1024/1024 转换。

## 依赖关系

- **平台 API**：
  - macOS/iOS: `<mach/mach.h>`、`<sys/resource.h>`
  - Linux: `<unistd.h>`、`/proc/self/statm`
  - Windows: `<windows.h>`、`<psapi.h>`
  - Fuchsia: `<zircon/syscalls.h>`
- **Skia**：SkTypes（平台检测宏）

## 设计模式与设计决策

- **条件编译**：每个函数针对不同平台有独立的 `#if` 块实现。
- **优雅降级**：不支持的平台统一返回 -1，调用者可据此判断。
- **字节/MB 双层 API**：底层使用字节精度，上层提供 MB 便利方法。

## 性能考量

- 所有调用都是系统调用或文件读取，频繁调用可能有开销。
- Linux 版本的当前 RSS 需要打开和读取 /proc 文件。
- 适合周期性采样而非热路径中的持续调用。

## 相关文件

- `dm/DM.cpp` - 内存使用报告
- `bench/nanobench.cpp` - 基准测试中的内存监控
