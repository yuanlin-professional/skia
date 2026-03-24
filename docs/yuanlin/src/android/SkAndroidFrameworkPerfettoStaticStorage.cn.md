# SkAndroidFrameworkPerfettoStaticStorage

> 源文件: src/android/SkAndroidFrameworkPerfettoStaticStorage.cpp

## 概述

`SkAndroidFrameworkPerfettoStaticStorage.cpp` 是一个极简的实现文件，专门用于在 Android Framework 中初始化 Perfetto 性能追踪系统的静态存储。该文件仅包含一行关键的宏调用，用于注册 Perfetto 追踪事件的全局存储。

Perfetto 是 Android 系统级的性能分析和追踪框架，此文件确保 Skia 在 Android Framework 环境中能够正确使用 Perfetto 进行性能追踪。

## 架构位置

在 Skia 的追踪系统架构中的位置：

```
Android Framework
    ↓
Skia 追踪系统
    ↓
Perfetto 追踪后端
    ↓
SkAndroidFrameworkPerfettoStaticStorage (静态存储初始化)
```

**职责**:
- 初始化 Perfetto 追踪事件的静态存储
- 仅在 Android Framework 构建中启用
- 提供全局追踪事件注册点

**条件编译**: 仅在定义 `SK_ANDROID_FRAMEWORK_USE_PERFETTO` 宏时生效。

## 主要功能

### 宏定义

**PERFETTO_TRACK_EVENT_STATIC_STORAGE()**

该宏由 Perfetto 库提供，展开后生成以下功能：
- 创建全局静态存储用于追踪事件注册
- 初始化追踪类别和事件描述符
- 注册到 Perfetto 追踪系统

**为什么不能放在头文件中**:
- 会导致多重定义错误（每个包含该头文件的编译单元都会定义一次）
- 必须在单一编译单元中调用一次
- 需要全局单例语义

## 内部实现细节

### 条件编译

```cpp
#ifdef SK_ANDROID_FRAMEWORK_USE_PERFETTO
// 仅在 Android Framework 构建中启用
PERFETTO_TRACK_EVENT_STATIC_STORAGE();
#endif
```

**编译配置**:
- Android Framework 构建: 启用 Perfetto 支持
- 标准 Skia 构建: 不包含此功能（使用其他追踪后端或禁用追踪）
- 第三方应用: 通常不启用

### 依赖的头文件

**SkTraceEventCommon.h**: Skia 追踪事件的公共头文件
- 定义追踪宏和接口
- 根据平台选择追踪后端（Perfetto、Systrace、Chrome Tracing 等）
- 提供统一的追踪 API

## 依赖关系

### 直接依赖
- **Perfetto SDK**: 提供 `PERFETTO_TRACK_EVENT_STATIC_STORAGE` 宏
- **SkTraceEventCommon.h**: Skia 追踪系统的公共头文件

### 被依赖
- **Skia 库**: 在 Android Framework 中编译时需要此文件
- **Android 系统追踪**: Perfetto 系统依赖此初始化

## 设计模式与设计决策

### 单例模式（隐式）

通过宏在全局作用域创建静态存储，确保：
- 进程中只有一个实例
- 程序启动时自动初始化
- 全局可访问

### 平台抽象

通过条件编译隔离平台特定代码：
- Android Framework 使用 Perfetto
- 其他平台使用不同的追踪后端
- 应用层代码无需感知差异

### 最小化文件

将宏调用隔离到单独的 .cpp 文件：
- 避免污染头文件
- 减少编译依赖
- 防止多重定义

## 性能考量

### 初始化开销

静态存储在程序启动时初始化：
- 一次性开销，不影响运行时性能
- Perfetto 设计为低开销追踪系统
- 未启用追踪时几乎零开销

### 内存占用

静态存储包含：
- 追踪类别注册表
- 事件描述符
- 通常几十 KB，对现代设备可忽略

### 追踪性能

Perfetto 的性能特点：
- 基于共享内存的零拷贝设计
- 异步记录，不阻塞主线程
- 可配置的缓冲区大小
- 生产环境可用的低开销

## 使用场景

### Android Framework 性能分析

开发者和系统工程师使用 Perfetto 分析：
- Skia 渲染性能
- 图形管道瓶颈
- 帧率问题诊断
- 内存分配模式

### 追踪工具集成

与 Android 生态系统工具集成：
- Android Studio Profiler
- Perfetto UI (ui.perfetto.dev)
- Systrace
- atrace 命令行工具

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkTraceEventCommon.h` | 依赖 | Skia 追踪事件公共头文件 |
| `include/core/SkTraceEvent.h` | 相关 | 追踪事件的公共 API |
| Perfetto SDK | 依赖 | Perfetto 追踪系统 SDK |
| Android Framework 构建系统 | 使用 | 编译配置和宏定义 |

## 注意事项

**重要**: 此文件虽然只有一行代码，但对 Android Framework 中的 Skia 性能追踪至关重要。删除或修改可能导致：
- 追踪数据丢失
- 性能分析工具失效
- 编译错误（如果其他代码依赖 Perfetto 初始化）

**编译要求**: 必须在所有其他使用 Perfetto 追踪的 Skia 源文件之前编译，确保静态存储在追踪事件注册前初始化。
