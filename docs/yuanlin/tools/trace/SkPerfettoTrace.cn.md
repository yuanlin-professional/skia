# SkPerfettoTrace - Perfetto 追踪集成

> 源文件:
> - [tools/trace/SkPerfettoTrace.h](../../../tools/trace/SkPerfettoTrace.h)
> - [tools/trace/SkPerfettoTrace.cpp](../../../tools/trace/SkPerfettoTrace.cpp)

## 概述

SkPerfettoTrace 是 SkEventTracer 的 Perfetto 追踪实现，将 Skia 的事件追踪数据桥接到 Perfetto 追踪系统。支持进程内追踪后端，可生成 `.perfetto-trace` 格式文件。支持短追踪（结束时一次性写入）和长追踪（流式持续写入）两种模式。仅在 `SK_USE_PERFETTO` 编译标志启用时可用。

## 架构位置

位于 `tools/trace/` 目录下，是追踪子系统中最现代的实现。通过 `--trace perfetto` 参数激活，支持 Linux、Android 和 Mac 平台。

## 主要类与结构体

### `SkPerfettoTrace`
继承 `SkEventTracer`，管理 Perfetto 追踪会话。
- `tracingSession` - Perfetto 追踪会话
- `fd` - 长追踪模式的文件描述符
- `fOutputPath` / `fOutputFileExtension` / `fCurrentSessionFullOutputPath` - 输出路径组件

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `SkPerfettoTrace()` | 构造并启动追踪会话 |
| `addTraceEvent(...)` | 将 Skia 事件转换为 Perfetto 事件 |
| `updateTraceEventDuration(...)` | 结束作用域事件 |
| `newTracingSection(name)` | 关闭当前会话并以新名称重新开始 |

## 内部实现细节

- **进程内后端**：使用 `perfetto::kInProcessBackend`，不依赖系统 Perfetto 守护进程。
- **双模式追踪**：
  - 短追踪（默认）：数据暂存内存，结束时 `ReadTraceBlocking()` 一次性写出
  - 长追踪（`--longPerfettoTrace`）：启用 `write_into_file` 流式写入，增大共享内存缓冲区（2MB）
- **参数类型分发**：`triggerTraceEvent` 提供 0/1/2 参数的重载，根据 `TRACE_VALUE_TYPE_*` 枚举分发到对应的 Perfetto 宏调用。
- **二参数模板**：使用 `begin_event_with_second_arg` 模板函数处理第二个参数的类型组合。
- **动态分类**：使用 `perfetto::DynamicCategory` 支持运行时分类名称。
- **INSTANT 事件**：立即开始并结束。

## 依赖关系

- **Perfetto SDK**：perfetto.h、TracingSession、TrackEvent
- **Skia 核心**：SkEventTracer
- **工具**：EventTracingPriv、CommandLineFlags
- **系统**：fcntl（文件操作）、fstream

## 设计模式与设计决策

- **适配器模式**：将 Skia 的 SkEventTracer 接口适配到 Perfetto 的 TrackEvent API。
- **与 Android Framework 互斥**：`SK_USE_PERFETTO` 和 `SK_ANDROID_FRAMEWORK_USE_PERFETTO` 不能同时使用。
- **会话管理**：`newTracingSection` 支持按基准测试分割追踪文件。
- **不可复制**：明确删除拷贝构造和赋值。

## 性能考量

- 长追踪模式增大共享内存（2MB）减少丢包，设置 5 秒写入周期和 10 秒刷新周期。
- 中央缓冲区默认 32MB。
- 短追踪优化：结束时一次性转储比流式写入更高效。
- Perfetto 的进程内后端比系统后端开销更低。

## 相关文件

- `tools/trace/EventTracingPriv.h` - 追踪初始化
- `src/core/SkTraceEvent.h` - 追踪事件宏定义
- Perfetto SDK 文档
