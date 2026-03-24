# EventTracingPriv - 事件追踪初始化与分类管理

> 源文件:
> - [tools/trace/EventTracingPriv.h](../../../tools/trace/EventTracingPriv.h)
> - [tools/trace/EventTracingPriv.cpp](../../../tools/trace/EventTracingPriv.cpp)

## 概述

EventTracingPriv 负责根据命令行参数初始化 Skia 的事件追踪系统，并提供追踪分类（category）的管理功能。它是连接命令行配置与具体追踪器实现（debugf、chrome、atrace、perfetto）的桥梁。

## 架构位置

位于 `tools/trace/` 目录下，是追踪基础设施的入口点。它依赖 `SkEventTracer` 接口并根据配置创建具体的追踪器实现。被 DM、nanobench 等工具在启动时调用。

## 主要类与结构体

### `SkEventTracingCategories`
管理追踪分类的注册和查询。
- `fCategories[kMaxCategories]` - 固定大小的分类数组（最多 256 个）
- 每个 `CategoryState` 包含 `fEnabled` 标志和 `fName` 指针
- 使用 `SkMutex` 保护线程安全

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `initializeEventTracingForTools(mode)` | 根据模式字符串创建并安装 SkEventTracer |
| `getCategoryGroupEnabled(name)` | 获取分类启用标志指针 |
| `getCategoryGroupName(flag)` | 通过启用标志反查分类名称 |

## 内部实现细节

- **追踪器选择**：根据 `--trace` 参数选择：`"debugf"` -> SkDebugfTracer、`"atrace"` -> SkATrace、`"perfetto"` -> SkPerfettoTrace、其他字符串 -> ChromeTracingTracer（作为文件名）。
- **分类过滤**：`getCategoryGroupEnabled` 使用 `--traceMatch` 参数和 `CommandLineFlags::ShouldSkip` 过滤分类。
- **前缀忽略**：自动跳过 `"disabled-by-default-"` 前缀。
- **CategoryState 布局**：`fEnabled` 位于结构体偏移 0 处（通过 `static_assert` 验证），允许直接将 `CategoryState*` 转换为 `uint8_t*`。
- **Perfetto 互斥**：`SK_USE_PERFETTO` 和 `SK_ANDROID_FRAMEWORK_USE_PERFETTO` 互斥检查。

## 依赖关系

- **追踪器实现**：ChromeTracingTracer、SkDebugfTracer、SkPerfettoTrace、SkATrace
- **Skia 核心**：SkEventTracer 接口
- **工具**：CommandLineFlags（命令行参数）
- **同步**：SkMutex

## 设计模式与设计决策

- **工厂函数模式**：`initializeEventTracingForTools` 根据字符串参数创建不同类型的追踪器。
- **简化的线程安全**：分类查找使用单次加锁（不同于 Chrome 的两阶段查找），因为追踪宏每个调用点只查询一次。
- **全局单例安装**：通过 `SkEventTracer::SetInstance` 设置全局追踪器。

## 性能考量

- 分类查找使用线性搜索加互斥锁，但由于追踪宏缓存结果，每个追踪点仅调用一次。
- 最多 256 个分类的硬限制在实际使用中足够。

## 相关文件

- `tools/trace/ChromeTracingTracer.h` - Chrome 追踪格式输出
- `tools/trace/SkDebugfTracer.h` - 调试日志输出
- `tools/trace/SkPerfettoTrace.h` - Perfetto 追踪
- `include/utils/SkEventTracer.h` - 追踪器接口
