# SkLog_android

> 源文件: [src/ports/SkLog_android.cpp](../../../../src/ports/SkLog_android.cpp)

## 概述

本文件实现了 Skia 日志系统在 Android 平台上的输出后端。日志消息通过 Android 的 `__android_log_vprint()` 发送到 logcat 系统，同时可选地输出到标准输出 (`stdout`)。支持将 Skia 日志优先级映射到 Android 日志优先级（Fatal、Error、Warning、Info、Debug），并为 Render Engine 构建提供了特殊的优先级覆盖。

## 架构位置

```
SkLog (日志系统)
  ├── SkLog_win.cpp     (Windows: stderr + OutputDebugStringA)
  ├── SkLog_android.cpp (本文件: Android logcat + 可选 stdout)
  └── SkLog_stdio.cpp   (其他平台: 仅 stderr)
```

仅在 `SK_BUILD_FOR_ANDROID` 宏定义时编译。

## 主要类与结构体

本文件不定义类或结构体。

### 全局变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `gSkDebugToStdOut` | `bool` | 是否同时输出到 stdout，默认 `false`，适用于命令行工具 |

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `void SkLogVAList(SkLogPriority priority, const char format[], va_list args)` | 将格式化日志输出到 Android logcat（及可选的 stdout） |

## 内部实现细节

### 优先级映射

Skia 的 `SkLogPriority` 到 Android `android_LogPriority` 的映射:

| SkLogPriority | Android 优先级 |
|:---:|:---:|
| `kFatal` | `ANDROID_LOG_FATAL` |
| `kError` | `ANDROID_LOG_ERROR` |
| `kWarning` | `ANDROID_LOG_WARN` |
| `kInfo` | `ANDROID_LOG_INFO` |
| `kDebug` | `ANDROID_LOG_DEBUG` |
| 其他 | `ANDROID_LOG_DEBUG` |

### 双通道输出

1. **stdout (可选)**: 如果 `gSkDebugToStdOut == true`，先使用 `va_copy` 复制参数列表，调用 `vprintf` 输出到 stdout，并 `fflush(stdout)` 确保实时性
2. **logcat (始终)**: 调用 `__android_log_vprint(android_priority, "skia", format, args)` 输出到系统日志

### Render Engine 特殊处理

```cpp
#if defined(SK_IN_RENDERENGINE)
    android_priority = ANDROID_LOG_WARN;
#endif
```

当 Skia 在 Android Render Engine 中编译时，所有日志强制提升为 Warning 级别。注释标注这是一个临时 hack，应在更新 `SkDebugf` 调用点后移除。

### LOG_TAG 定义

```cpp
#ifdef LOG_TAG
  #undef LOG_TAG
#endif
#define LOG_TAG "skia"
```

确保日志标签为 `"skia"`，防止被外部定义覆盖。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/private/base/SkDebug.h` | 调试工具 |
| `include/private/base/SkFeatures.h` | 平台特性检测 |
| `include/private/base/SkLog.h` | 日志接口声明 |
| `<stdio.h>` | vprintf, fflush |
| `<cstdarg>` | va_list, va_copy |
| `<android/log.h>` | Android NDK 日志 API |

## 设计模式与设计决策

1. **优先级映射**: 将 Skia 的抽象优先级转换为 Android 平台的原生优先级
2. **可配置的双输出**: `gSkDebugToStdOut` 全局变量允许命令行工具启用 stdout 输出
3. **LOG_TAG 防御**: `#undef` + `#define` 确保日志标签不被外部影响
4. **Render Engine 适配**: 条件编译覆盖优先级，适应 Render Engine 的日志过滤需求
5. **va_copy 安全**: stdout 输出使用参数副本，保持原始 va_list 可用于 logcat

## 性能考量

- `__android_log_vprint` 是一个进程间通信操作（写入 logd），在高频日志场景下可能成为瓶颈
- `gSkDebugToStdOut` 默认关闭，避免不必要的 stdout 输出开销
- `fflush(stdout)` 在每次输出后强制刷新，确保实时性但增加 I/O 开销
- switch-case 优先级映射是 O(1) 操作，开销可忽略
- `va_copy` 引入少量复制开销，仅在 stdout 输出启用时执行

## 相关文件

- `include/private/base/SkLog.h` — 日志接口声明
- `src/ports/SkLog_win.cpp` — Windows 平台日志
- `src/ports/SkLog_stdio.cpp` — 通用平台日志
