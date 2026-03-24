# ChromeTracingTracer - Chrome Tracing JSON 追踪器

> 源文件:
> - [tools/trace/ChromeTracingTracer.h](../../../tools/trace/ChromeTracingTracer.h)
> - [tools/trace/ChromeTracingTracer.cpp](../../../tools/trace/ChromeTracingTracer.cpp)

## 概述

ChromeTracingTracer 是 SkEventTracer 的实现，将追踪事件记录为 JSON 格式，可在 chrome://tracing 中查看。它使用块分配内存策略高效地存储事件数据，在程序退出时统一序列化为 JSON 文件。

## 架构位置

位于 `tools/trace/` 目录下，是追踪子系统的核心实现之一。通过 EventTracingPriv 的初始化机制安装，用于性能分析和调试。

## 主要类与结构体

### `ChromeTracingTracer`
继承 `SkEventTracer`，管理事件记录和 JSON 序列化。

### `TraceEvent`（内部）
定义事件的固定数据部分：phase、numArgs、size、name、ID、时钟信息、线程 ID。字段按对齐优化排列。

### `TraceEventArg`（内部）
事件参数：argType、argName、argValue。

### `TraceEventBlock`
事件存储块，包含 `BlockPtr`（字节数组）和块内事件计数。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `ChromeTracingTracer(filename)` | 构造，指定输出文件名 |
| `addTraceEvent(...)` | 记录追踪事件 |
| `updateTraceEventDuration(...)` | 更新事件持续时间 |
| `getCategoryGroupEnabled/Name()` | 分类管理（委托给 SkEventTracingCategories） |

## 内部实现细节

- **块分配策略**：使用 512KB 大小的内存块存储事件，块满时创建新块并将旧块移入 `fBlocks` 数组。
- **事件布局**：`{TraceEvent}{TraceEventArg...}{内联字符串}`，每个事件按 8 字节对齐。
- **COPY_STRING 处理**：需要复制的字符串存储在事件末尾的字符串表中，argValue 记录偏移量。
- **时间戳**：使用 `std::chrono::steady_clock` 纳秒精度，序列化时转换为微秒并减去偏移量。
- **线程 ID 映射**：将平台线程 ID 映射为连续短 ID 以简化 JSON 输出。
- **JSON 序列化**：在 `onExit()` 中遍历所有块中的事件，使用 `SkJSONWriter` 以 kFast 模式输出。
- **对象快照**：跟踪对象创建/删除阶段，在快照事件中自动插入 `base_type` 字段。

## 依赖关系

- **Skia 核心**：SkEventTracer、SkString、SkStream
- **内部工具**：SkJSONWriter、SkOSPath、SkTraceEvent
- **同步**：SkSpinlock
- **标准库**：chrono

## 设计模式与设计决策

- **块分配器**：避免频繁的小内存分配，用大块预分配减少锁竞争和碎片。
- **延迟序列化**：运行时仅记录二进制数据，退出时才进行 JSON 序列化。
- **自旋锁**：使用 `SkSpinlock` 而非互斥锁，因为事件追加操作非常快。

## 性能考量

- 块大小 512KB 在内存使用和分配频率间取得平衡。
- 自旋锁最小化了多线程追踪的争用开销。
- JSON 序列化仅在退出时执行一次，不影响运行时性能。
- 时间戳使用相对偏移减少 JSON 数字长度。

## 相关文件

- `tools/trace/EventTracingPriv.h` - 追踪初始化
- `src/utils/SkJSONWriter.h` - JSON 写入工具
- `src/core/SkTraceEvent.h` - 追踪事件宏
