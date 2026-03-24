# CrashHandler - 崩溃处理与堆栈追踪

> 源文件:
> - [tools/CrashHandler.h](../../tools/CrashHandler.h)
> - [tools/CrashHandler.cpp](../../tools/CrashHandler.cpp)

## 概述

CrashHandler 提供了一个跨平台的崩溃信号处理机制，在程序崩溃时自动打印堆栈追踪信息。支持 macOS、Linux（含 Fuchsia）和 Windows 平台，帮助开发者快速定位 Skia 工具和测试中的崩溃原因。

## 架构位置

位于 `tools/` 目录下，是一个底层工具组件。它在 DM（Skia 测试运行器）、nanobench 等工具程序启动时被调用，不依赖 Skia 的图形渲染管线。

## 主要类与结构体

本模块不包含类定义，仅提供一个全局函数 `SetupCrashHandler()`。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `SetupCrashHandler()` | 注册崩溃信号处理器，如果尚未注册且平台支持 |

## 内部实现细节

### macOS 实现
- 使用 `libunwind` 库进行本地栈展开（定义 `UNW_LOCAL_ONLY` 选择更快的实现）
- 使用 `abi::__cxa_demangle` 对 C++ 符号名进行反修饰
- 注册处理的信号：SIGABRT、SIGBUS、SIGFPE、SIGILL、SIGSEGV、SIGTRAP

### Linux 实现
- 标准 Linux 使用 `backtrace()` / `backtrace_symbols()` + `dladdr()` / `__cxa_demangle`
- Fuchsia 使用特殊的 `backtrace_request()` 机制，通过软件断点触发系统异常处理打印回溯

### Windows 实现
- 使用 `SetUnhandledExceptionFilter` 注册异常过滤器
- 通过 `StackWalk64` 遍历调用栈，`SymGetSymFromAddr64` 解析符号名
- 支持 x86、AMD64、ARM64 架构
- 处理的异常：`EXCEPTION_ACCESS_VIOLATION`、`EXCEPTION_BREAKPOINT`、`EXCEPTION_INT_DIVIDE_BY_ZERO`、`EXCEPTION_STACK_OVERFLOW`

### 信号处理策略
- 仅在当前处理器为 `SIG_DFL`（默认处理器）时注册，避免覆盖 `catchsegv` 等工具
- 处理器中调用 `_Exit(sig)` 立即终止，不触发 `atexit` 回调或通知其他线程

## 依赖关系

- **平台 API**：
  - macOS: libunwind、cxxabi
  - Linux: execinfo、dlfcn、cxxabi（Fuchsia: zircon 内联汇编）
  - Windows: DbgHelp、Windows API
- **Skia 内部**：SkDebug（日志输出）、SkLeanWindows（精简 Windows 头文件）、SkMalloc

## 设计模式与设计决策

- **条件编译**：通过 `SK_BUILD_FOR_MAC` / `SK_BUILD_FOR_UNIX` / `SK_BUILD_FOR_WIN` 宏选择平台实现。
- **防御性注册**：检查现有处理器，避免覆盖已安装的调试工具。
- **空实现回退**：不支持的平台提供空的 `SetupCrashHandler()` 实现。

## 性能考量

- 仅在崩溃时执行，对正常运行无性能影响。
- macOS 使用 `UNW_LOCAL_ONLY` 优化，避免远程栈展开的开销。
- 处理器中直接使用 `_Exit` 避免复杂的清理流程。

## 相关文件

- `dm/DM.cpp` - DM 测试运行器中调用 `SetupCrashHandler()`
- `bench/nanobench.cpp` - 基准测试工具中调用
- `include/private/base/SkDebug.h` - SkDebugf 日志输出
