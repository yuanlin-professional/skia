# Skia Trace 追踪工具

## 概述

`tools/trace` 实现了 Skia 的事件追踪（Event Tracing）基础设施。该模块提供了多种 `SkEventTracer` 的实现，支持将 Skia 内部的性能追踪事件输出到不同的后端：Chrome Tracing JSON 格式（可在 chrome://tracing 中查看）、SkDebugf 调试输出以及 Perfetto 追踪系统。这是 Skia 性能分析和调试的重要工具。

## 目录结构

```
tools/trace/
├── BUILD.bazel                # Bazel 构建配置
├── EventTracingPriv.h         # 追踪初始化和类别管理器
├── EventTracingPriv.cpp       # 追踪初始化实现
├── ChromeTracingTracer.h      # Chrome Tracing 格式追踪器声明
├── ChromeTracingTracer.cpp    # Chrome Tracing 格式追踪器实现
├── SkDebugfTracer.h           # SkDebugf 调试输出追踪器声明
├── SkDebugfTracer.cpp         # SkDebugf 调试输出追踪器实现
├── SkPerfettoTrace.h          # Perfetto 追踪器声明
└── SkPerfettoTrace.cpp        # Perfetto 追踪器实现
```

## 核心架构

### SkEventTracer 接口

所有追踪器都实现 `SkEventTracer`（定义在 `include/utils/SkEventTracer.h`）接口：

```cpp
// 核心方法
Handle addTraceEvent(phase, categoryEnabledFlag, name, id, numArgs, ...);
void updateTraceEventDuration(categoryEnabledFlag, name, handle);
const uint8_t* getCategoryGroupEnabled(name);
const char* getCategoryGroupName(categoryEnabledFlag);
void newTracingSection(name);
```

### EventTracingPriv

追踪系统的初始化和类别管理：

```cpp
// 根据模式字符串初始化追踪器
void initializeEventTracingForTools(const char* mode = nullptr);
```

**SkEventTracingCategories 类：**
- 管理最多 256 个追踪类别
- 每个类别有一个 `enabled` 标志和名称
- 使用 SkMutex 保证线程安全
- 通过 `getCategoryGroupEnabled()` 返回指向类别启用状态的指针

### 追踪器实现

#### ChromeTracingTracer

输出 Chrome Tracing 兼容的 JSON 格式：

- 将追踪事件写入 JSON 文件，可在 `chrome://tracing` 中加载查看
- 使用内存块（默认 512KB）批量存储事件，减少分配开销
- 事件大小可变（通常约 48 字节），适应不同复杂度的追踪信息
- 通过 SkSpinlock 保证多线程并发写入安全
- 在 `onExit()` 时将所有缓冲的事件刷新到文件

```cpp
ChromeTracingTracer tracer("trace_output.json");
// 追踪事件自动收集...
// 程序退出时写入 trace_output.json
```

#### SkDebugfTracer

使用 SkDebugf 输出追踪信息到标准调试日志：

- 适合快速调试和开发阶段使用
- 输出包含缩进的层级结构，便于阅读
- 支持追踪段（tracing section）分隔
- 维护缩进计数器，跟踪嵌套深度

#### SkPerfettoTrace

集成 Google Perfetto 系统追踪框架：

- 支持系统级性能追踪
- 使用 Perfetto SDK 的追踪会话管理
- 输出到文件描述符，可与 Perfetto 工具链配合使用
- 需要编译时启用 Perfetto 支持

## 使用方法

### 通过命令行启用追踪

大多数 Skia 工具支持 `--trace` 命令行参数：

```bash
# 输出 Chrome Tracing JSON
./out/Release/dm --trace trace_output.json

# 输出到 SkDebugf
./out/Release/dm --trace debugf

# 使用 Perfetto
./out/Release/dm --trace perfetto
```

### 在代码中使用

```cpp
#include "tools/trace/EventTracingPriv.h"

// 初始化追踪（通常在 main 中调用）
initializeEventTracingForTools("trace_output.json");

// Skia 内部的 TRACE_EVENT 宏会自动收集事件
// TRACE_EVENT0("skia", "SomeFunction");
```

### 查看 Chrome Tracing 输出

1. 运行工具生成 JSON 追踪文件
2. 在 Chrome 浏览器中打开 `chrome://tracing`
3. 点击 "Load" 加载生成的 JSON 文件
4. 使用时间线视图分析性能瓶颈

## 追踪事件类型

| 阶段 (Phase) | 含义 |
|--------------|------|
| `B` | Begin（事件开始） |
| `E` | End（事件结束） |
| `X` | Complete（完整事件，包含持续时间） |
| `I` | Instant（瞬间事件） |
| `C` | Counter（计数器事件） |

## 与其他模块的关系

- **include/utils/SkEventTracer.h**: 追踪器基类接口定义
- **src/core/SkTraceEvent.h**: TRACE_EVENT 宏定义
- **bench/**: nanobench 使用追踪系统分析基准测试性能
- **tools/viewer/**: Viewer 支持实时性能追踪
- **tools/flags/**: 提供 `--trace` 命令行参数支持
