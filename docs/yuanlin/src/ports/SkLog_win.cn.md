# SkLog_win

> 源文件: [src/ports/SkLog_win.cpp](../../../../src/ports/SkLog_win.cpp)

## 概述

本文件实现了 Skia 日志系统在 Windows 平台上的输出后端。核心函数 `SkLogVAList()` 将格式化日志消息同时输出到标准错误流 (`stderr`) 和 Windows 调试输出 (`OutputDebugStringA`)，使得日志在控制台和 Visual Studio 调试器的输出窗口中均可查看。

## 架构位置

Skia 的日志系统采用平台分发策略，每个平台有独立的日志输出实现：

```
SkLog (日志接口)
  ├── SkLog_win.cpp     (本文件: Windows 平台)
  ├── SkLog_android.cpp (Android 平台)
  └── SkLog_stdio.cpp   (其他平台: Linux/macOS 等)
```

本文件仅在 `SK_BUILD_FOR_WIN` 宏定义时参与编译。

## 主要类与结构体

本文件不定义类或结构体。

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `void SkLogVAList(SkLogPriority priority, const char format[], va_list args)` | 将格式化日志消息输出到 stderr 和 Windows 调试输出 |

**参数说明:**
- `priority`: 日志优先级（当前实现中未用于过滤，所有优先级均输出）
- `format`: printf 风格的格式字符串
- `args`: 可变参数列表

## 内部实现细节

### 双通道输出

1. **stderr 输出**: 使用 `va_copy` 复制参数列表后调用 `vfprintf(stderr, ...)` 输出。之后调用 `fflush(stderr)`，因为 Windows 上 stderr 可能是缓冲的。
2. **调试器输出**: 使用 `vsnprintf` 将消息格式化到固定大小缓冲区 (2048 字节)，再通过 `OutputDebugStringA()` 发送到 Windows 调试器。

### 缓冲区大小

- `kBufferSize = 2048` — 调试输出的固定缓冲区大小
- 超过此长度的消息会被 `vsnprintf` 截断
- stderr 输出不受此限制，使用 `vfprintf` 直接流式输出

### va_list 处理

- 使用 `va_copy()` 创建参数列表副本用于 stderr 输出
- 原始 `args` 用于 `vsnprintf` 格式化调试输出缓冲区
- 这是必要的，因为 `va_list` 在使用后状态不确定

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/private/base/SkDebug.h` | 调试工具 |
| `include/private/base/SkFeatures.h` | 平台特性检测 |
| `include/private/base/SkLog.h` | 日志接口声明 |
| `src/base/SkLeanWindows.h` | Windows 头文件精简包含 |
| `<stdarg.h>` | va_list 处理 |
| `<stdio.h>` | vfprintf, vsnprintf |

## 设计模式与设计决策

1. **双通道输出策略**: 同时输出到 stderr 和调试器，确保在命令行和 IDE 调试环境中都能看到日志
2. **显式 fflush**: Windows 上 stderr 可能是缓冲的（与 POSIX 默认无缓冲不同），需要显式刷新
3. **固定大小缓冲区**: 使用栈分配的 2048 字节缓冲区，避免堆分配，但牺牲了超长消息的完整性
4. **优先级参数保留**: 虽然当前未使用 `priority` 进行过滤，但接口预留了按优先级控制输出的能力

## 性能考量

- 栈分配缓冲区避免了堆分配开销
- `OutputDebugStringA` 是一个相对耗时的系统调用，在高频日志场景下可能成为瓶颈
- `fflush(stderr)` 每次日志调用都会执行，确保实时性但增加了 I/O 开销
- `va_copy` 引入少量额外复制开销，但对于日志输出场景可忽略

## 相关文件

- `include/private/base/SkLog.h` — 日志系统接口声明
- `src/ports/SkLog_android.cpp` — Android 平台日志实现
- `src/ports/SkLog_stdio.cpp` — 通用平台日志实现
- `src/base/SkLeanWindows.h` — Windows 头文件精简包含
