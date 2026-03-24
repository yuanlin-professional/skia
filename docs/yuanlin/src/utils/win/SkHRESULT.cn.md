# SkHRESULT - Windows HRESULT 错误处理工具

> 源文件:
> - `src/utils/win/SkHRESULT.h`
> - `src/utils/win/SkHRESULT.cpp`

## 概述

SkHRESULT 模块提供了一套宏和函数，用于简化 Windows COM HRESULT 错误码的检查和报告。它定义了多种错误处理宏，能够在 HRESULT 失败时自动从当前函数返回适当的值，并在调试模式下输出详细的错误信息。

## 架构位置

```
Skia Windows 平台层
├── 所有使用 COM/DirectWrite 的代码
│   └── SkHRESULT (本模块 - 错误处理基础设施)
│       ├── 错误检查宏 (HR, HRB, HRN, HRV, HRZ)
│       └── 错误追踪函数 (SkTraceHR)
└── Windows API (COM/HRESULT)
```

## 主要类与结构体

该模块没有定义类或结构体，仅包含函数和宏。

## 公共 API 函数

### `SkTraceHR`
```cpp
void SkTraceHR(const char* file, unsigned long line, HRESULT hr, const char* msg);
```
- **功能**: 输出 HRESULT 错误的详细跟踪信息。
- **输出内容**: 自定义消息（如果提供）、文件名、行号、十六进制错误码以及系统格式化的错误描述。
- **实现**: 使用 `FormatMessageA` 获取系统错误描述文本。

## 错误处理宏

### 核心宏 `HR_GENERAL`
```cpp
#define HR_GENERAL(_ex, _msg, _ret)
```
- 执行表达式 `_ex`，检查返回的 HRESULT。
- 如果 `FAILED(_hr)`，调用 `SK_TRACEHR` 并返回 `_ret`。

### 变体宏

| 宏 | 带消息版本 | 返回值 | 用途 |
|---|---|---|---|
| `HR(ex)` | `HRM(ex, msg)` | HRESULT | 返回 HRESULT 传播错误 |
| `HRB(ex)` | `HRBM(ex, msg)` | `false` | 返回 bool 的函数 |
| `HRN(ex)` | `HRNM(ex, msg)` | `nullptr` | 返回指针的函数 |
| `HRV(ex)` | `HRVM(ex, msg)` | (void) | 返回 void 的函数 |
| `HRZ(ex)` | `HRZM(ex, msg)` | `0` | 返回整数的函数 |

### `SK_TRACEHR`
```cpp
#define SK_TRACEHR(_hr, _msg)
```
- 在 `SK_DEBUG` 模式下调用 `SkTraceHR()` 输出错误信息。
- 在 Release 模式下使用 `sk_ignore_unused_variable` 消除未使用变量警告。

## 内部实现细节

### 错误消息格式化
`SkTraceHR` 使用 Windows `FormatMessageA` API 将 HRESULT 转换为可读的错误描述：
- 使用 `FORMAT_MESSAGE_ALLOCATE_BUFFER` 让系统分配缓冲区。
- 使用 `FORMAT_MESSAGE_FROM_SYSTEM` 从系统错误表查找。
- 使用 `MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT)` 获取默认语言的错误文本。
- 如果系统无法格式化错误码，输出 `<unknown>`。
- 使用 `LocalFree` 释放系统分配的缓冲区。

### Debug/Release 区分
- Debug 模式 (`SK_DEBUG`): 宏会调用 `SkTraceHR` 输出完整的错误跟踪信息。
- Release 模式: 宏仅执行表达式和检查，跳过追踪输出以避免性能开销。

## 依赖关系

- `include/core/SkTypes.h`: 基础类型和平台检测。
- `src/base/SkLeanWindows.h`: 精简的 Windows 头文件（提供 `HRESULT`、`FormatMessageA` 等）。
- `include/private/base/SkDebug.h`: `SkDebugf` 调试输出函数。

## 设计模式与设计决策

1. **早返回模式**: 宏使用 `do { ... return; } while(false)` 模式实现简洁的错误检查和早期返回。
2. **返回值多态**: 通过不同的宏后缀（B/N/V/Z）支持不同返回类型的函数，避免在每个调用点编写重复的错误检查代码。
3. **条件编译追踪**: 仅在 Debug 模式下输出错误详情，Release 模式下零开销。
4. **系统消息集成**: 利用 Windows 系统 API 将错误码转换为人类可读的描述。

## 性能考量

1. **Release 模式零追踪开销**: `SK_TRACEHR` 在 Release 模式下是空操作。
2. **仅在错误时触发**: 只有在 HRESULT 失败时才执行追踪代码。
3. **FormatMessageA 开销**: 系统错误格式化仅在调试模式的错误路径上执行，不影响正常性能。

## 相关文件

- `src/utils/win/SkDWrite.h/.cpp`: 大量使用 HRM/HRVM 等宏进行 DirectWrite 错误处理。
- `src/utils/win/SkDWriteFontFileStream.h/.cpp`: 使用 HRNM 宏。
- `src/utils/win/SkIStream.h/.cpp`: 使用这些宏处理 IStream 操作的错误。
