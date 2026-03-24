# SkDebugfTracer - 调试日志追踪器

> 源文件:
> - [tools/trace/SkDebugfTracer.h](../../../tools/trace/SkDebugfTracer.h)
> - [tools/trace/SkDebugfTracer.cpp](../../../tools/trace/SkDebugfTracer.cpp)

## 概述

SkDebugfTracer 是 SkEventTracer 的简单实现，使用 `SkDebugf` 将追踪事件输出到调试日志。它以人类可读的缩进格式显示事件层级，适合快速调试和理解 Skia 内部执行流程。

## 架构位置

位于 `tools/trace/` 目录下，是最简单的追踪器实现。通过 `--trace debugf` 命令行参数激活。

## 主要类与结构体

### `SkDebugfTracer`
继承 `SkEventTracer`，使用 SkDebugf 输出事件。
- `fIndent` - 当前缩进字符串
- `fCnt` - 事件计数器
- `fCategories` - 分类管理器

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `addTraceEvent(...)` | 格式化并输出追踪事件 |
| `updateTraceEventDuration(...)` | 输出事件结束（减少缩进） |
| `newTracingSection(name)` | 输出新追踪段落分隔符 |

## 内部实现细节

- **缩进管理**：`TRACE_EVENT_PHASE_COMPLETE` 事件开启时增加缩进空格，`updateTraceEventDuration` 时减少。
- **参数格式化**：支持 bool、uint、int、double、pointer、string 类型，字符串参数截断到 20 字符。
- **输出格式**：`[缩进深度]缩进 <分类> 事件名 参数 #计数 {`（开始）和 `[缩进深度]缩进 } 事件名`（结束）。
- **字符串截断**：字符串值超过 20 字符或遇到换行符时截断并追加 `"..."`。

## 依赖关系

- **Skia 核心**：SkEventTracer、SkString
- **工具**：EventTracingPriv（分类管理）
- **内部**：SkTraceEvent（追踪事件常量）

## 设计模式与设计决策

- **最小化实现**：仅关注可读性输出，不追求性能或持久化。
- **缩进可视化**：通过空格缩进直观展示事件嵌套层级。
- **返回值 0**：Handle 始终返回 0，因为调试输出不需要后续引用。

## 性能考量

- 每个事件都直接调用 SkDebugf，在高频追踪场景下会产生大量 I/O。
- 字符串格式化有一定开销，但作为调试工具这是可接受的。
- 不适合生产环境的性能分析。

## 相关文件

- `tools/trace/EventTracingPriv.h` - 追踪初始化
- `tools/trace/ChromeTracingTracer.h` - 更高级的 JSON 追踪器
