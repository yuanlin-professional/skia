# SkLog_stdio

> 源文件: [src/ports/SkLog_stdio.cpp](../../../../src/ports/SkLog_stdio.cpp)

## 概述

本文件实现了 Skia 日志系统在非 Windows、非 Android 平台（如 Linux、macOS、ChromeOS 等）上的输出后端。实现极为简洁：将格式化日志消息直接输出到标准错误流 (`stderr`)。这是三个平台日志后端中最简单的一个。

## 架构位置

```
SkLog (日志系统)
  ├── SkLog_win.cpp     (Windows: stderr + OutputDebugStringA)
  ├── SkLog_android.cpp (Android: stdout + __android_log_vprint)
  └── SkLog_stdio.cpp   (本文件: 其他平台, 仅 stderr)
```

通过条件编译 `#if !defined(SK_BUILD_FOR_WIN) && !defined(SK_BUILD_FOR_ANDROID)` 选择本实现。

## 主要类与结构体

本文件不定义类或结构体。

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `void SkLogVAList(SkLogPriority priority, const char format[], va_list args)` | 将格式化日志消息输出到 stderr |

**参数说明:**
- `priority`: 日志优先级（当前实现未使用此参数进行过滤）
- `format`: printf 风格格式字符串
- `args`: 可变参数列表

## 内部实现细节

```cpp
void SkLogVAList(SkLogPriority priority, const char format[], va_list args) {
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wformat-nonliteral"
    vfprintf(stderr, format, args);
#pragma GCC diagnostic pop
}
```

- 直接使用 `vfprintf(stderr, ...)` 输出
- 使用 `#pragma GCC diagnostic` 抑制 `-Wformat-nonliteral` 警告，因为 `format` 不是字面字符串
- 不调用 `fflush(stderr)` — 在 POSIX 系统上 stderr 默认是无缓冲的
- `priority` 参数被忽略，所有级别的日志均输出

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/private/base/SkDebug.h` | 调试工具 |
| `include/private/base/SkFeatures.h` | 平台特性检测 |
| `include/private/base/SkLoadUserConfig.h` | 用户配置加载 |
| `include/private/base/SkLog.h` | 日志接口声明 |
| `<stdarg.h>` | va_list 类型 |
| `<stdio.h>` | vfprintf |

## 设计模式与设计决策

1. **最小实现**: 仅 6 行有效代码，是最简洁的日志后端
2. **POSIX 行为假设**: 不显式 fflush，依赖 POSIX stderr 的默认无缓冲行为
3. **编译器警告抑制**: 使用 pragma 处理非字面格式字符串警告，这是 va_list 转发场景中的常见做法
4. **优先级保留但不使用**: 接口中保留 priority 参数，便于未来扩展过滤逻辑

## 性能考量

- stderr 在 POSIX 系统上默认无缓冲，每次写入都直接输出，无需额外 flush
- 不做任何字符串格式化预处理，直接传递给 `vfprintf`，开销最小
- 无优先级过滤意味着所有日志都会输出，在高频日志场景下可能影响性能
- 与 Windows 版本相比，没有额外的缓冲区拷贝（Windows 需要为 OutputDebugStringA 准备副本）
- 与 Android 版本相比，没有 IPC 开销（Android 的 logcat 需要进程间通信）

## 使用场景

本实现在以下平台上作为默认日志后端:
- Linux (包括 ChromeOS)
- macOS
- FreeBSD 和其他 POSIX 兼容系统
- 通过 `SkDebugf()` 宏的调用最终到达此函数

## 与其他平台实现的比较

| 特性 | stdio (本文件) | Windows | Android |
|------|:---:|:---:|:---:|
| stderr 输出 | 是 | 是 | 否 |
| stdout 输出 | 否 | 否 | 可选 |
| 调试器输出 | 否 | 是 (OutputDebugStringA) | 否 |
| logcat 输出 | 否 | 否 | 是 |
| 优先级使用 | 否 | 否 | 是 |
| 缓冲区拷贝 | 否 | 是 (2048字节) | 否 |
| 显式 fflush | 否 | 是 | 仅 stdout |

## 相关文件

- `include/private/base/SkLog.h` — 日志接口声明
- `src/ports/SkLog_win.cpp` — Windows 平台日志
- `src/ports/SkLog_android.cpp` — Android 平台日志
