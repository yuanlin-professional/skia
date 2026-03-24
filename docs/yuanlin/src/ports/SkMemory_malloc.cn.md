# SkMemory_malloc

> 源文件: [src/ports/SkMemory_malloc.cpp](../../../../src/ports/SkMemory_malloc.cpp)

## 概述

本文件实现了 Skia 的核心内存分配接口，基于标准 C 库的 `malloc`/`calloc`/`realloc`/`free` 函数。这是 Skia 默认的内存分配后端，所有 Skia 内部的内存分配（通过 `sk_malloc_flags`、`sk_realloc_throw`、`sk_free` 等）最终都由本文件的函数处理。此外还包含了 `sk_abort_no_print` 和 `sk_out_of_memory` 等异常处理函数。

## 架构位置

本文件是 Skia 内存管理子系统的底层实现，是两个可选内存后端之一（另一个是 Mozilla 的 `SkMemory_mozalloc.cpp`）。

```
include/private/base/SkMalloc.h (接口声明)
  ├── src/ports/SkMemory_malloc.cpp  (本文件: 标准 malloc 实现)
  └── src/ports/SkMemory_mozalloc.cpp (Mozilla mozalloc 实现)
```

## 主要类与结构体

本文件不定义类或结构体。

## 公共 API 函数

### 内存分配与释放

| 函数签名 | 功能说明 |
|---------|---------|
| `void* sk_malloc_flags(size_t size, unsigned flags)` | 核心分配函数，支持零初始化和异常抛出标志 |
| `void* sk_realloc_throw(void* addr, size_t size)` | 重新分配内存，失败时终止程序 |
| `void sk_free(void* p)` | 释放内存，带 null 检查守卫 |
| `size_t sk_malloc_size(void* addr, size_t size)` | 查询实际分配的内存大小 |

### 异常处理

| 函数签名 | 功能说明 |
|---------|---------|
| `void sk_abort_no_print()` | 无输出的程序终止 |
| `void sk_out_of_memory(void)` | 内存耗尽处理（调试断言后终止） |

## 内部实现细节

### sk_malloc_flags - 核心分配

分配逻辑根据 flags 标志位组合决定行为:

1. **`SK_MALLOC_ZERO_INITIALIZE`**: 使用 `calloc(size, 1)` 分配零初始化内存
2. **无零初始化标志**: 使用 `malloc(size)` 分配
3. **`SK_MALLOC_THROW`**: 分配失败时调用 `throw_on_failure()` 终止程序
4. **无 THROW 标志**: 分配失败时返回 `nullptr`

**Android Framework 特殊处理:**
```cpp
(void)mallopt(M_THREAD_DISABLE_MEM_INIT, 1);  // 关闭 malloc 零初始化
p = malloc(size);
(void)mallopt(M_THREAD_DISABLE_MEM_INIT, 0);  // 恢复默认行为
```
Android Bionic 默认会对 `malloc` 分配的内存进行零初始化（安全考虑），但这对 HWUI 渲染性能有显著影响，因此 Skia 在 Android Framework 构建中临时关闭此行为。

### sk_free - 带守卫的释放

```cpp
void sk_free(void* p) {
    if (p != nullptr) {
        free(p);
    }
}
```
null 检查守卫被保留的原因: 注释引用了 Skia CL 588037 的测试结果，该守卫在多个测试和平台上提供了可测量的性能提升。

### sk_abort_no_print - 平台差异化终止

- **Windows Debug**: 使用 `__fastfail(FAST_FAIL_FATAL_APP_EXIT)` 触发快速失败
- **Clang**: 使用 `__builtin_trap()` 生成陷阱指令
- **其他**: 使用标准 `abort()`

### sk_malloc_size - 实际分配大小查询

针对不同平台使用对应的 API 查询分配器实际分配的字节数:
- **macOS/iOS**: `malloc_size()`
- **Android (API >= 17)**: `malloc_usable_size()`
- **Linux**: `malloc_usable_size()`
- **Windows**: `_msize()`

### throw_on_failure - 分配失败处理

当分配大小 > 0 但返回 `nullptr` 时，调用 `sk_out_of_memory(size)` 终止程序。`size == 0` 时允许返回 `nullptr`。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/private/base/SkAssert.h` | 断言宏 |
| `include/private/base/SkDebug.h` | 调试输出 |
| `include/private/base/SkFeatures.h` | 平台特性检测 |
| `include/private/base/SkMalloc.h` | 接口声明 |
| `<cstdlib>` | malloc/calloc/realloc/free/abort |
| `<algorithm>` | std::max (用于 sk_malloc_size) |
| `<malloc/malloc.h>` | macOS/iOS: malloc_size |
| `<malloc.h>` | Android/Linux/Windows: malloc_usable_size/_msize |
| `<intrin.h>` | Windows Debug: __fastfail |

## 设计模式与设计决策

1. **策略模式**: 内存分配后端可在构建时通过链接不同的 `.cpp` 文件替换（malloc vs mozalloc）
2. **标志位组合**: `sk_malloc_flags` 通过位标志组合支持多种分配策略，避免函数爆炸
3. **Android 性能优化**: 临时关闭 Bionic 的内存零初始化，平衡安全性和渲染性能
4. **AFL Fuzz 特殊处理**: 在模糊测试构建中使用 `exit(1)` 而非 `abort()`，避免将内存耗尽误报为崩溃
5. **防御性 null 守卫**: `sk_free` 中的 null 检查基于实际性能测试保留
6. **条件编译层次**: 多层 `#if` / `#ifdef` 确保每个平台使用最合适的 API

## 函数调用关系

```
sk_malloc_throw(size)         -> sk_malloc_flags(size, SK_MALLOC_THROW)
sk_malloc_canfail(size)       -> sk_malloc_flags(size, 0)
sk_calloc_throw(size)         -> sk_malloc_flags(size, SK_MALLOC_THROW | SK_MALLOC_ZERO_INITIALIZE)
sk_calloc_canfail(size)       -> sk_malloc_flags(size, SK_MALLOC_ZERO_INITIALIZE)
sk_malloc_flags(size, flags)  -> calloc() / malloc() -> throw_on_failure()
sk_realloc_throw(addr, size)  -> realloc() -> throw_on_failure()
                                 sk_free() (when size == 0)
```

这些上层函数在 `SkMalloc.h` 中定义为内联函数，最终都调用本文件中的 `sk_malloc_flags`。

## 性能考量

- `sk_free` 的 null 守卫经实测在多平台上提供性能提升（可能因减少 free(nullptr) 的系统调用开销）
- Android Framework 上临时禁用内存初始化是为了 HWUI 渲染性能
- `sk_malloc_size` 允许上层代码利用分配器实际分配的多余空间，减少不必要的重新分配
- `calloc` 用于零初始化分配，比 `malloc + memset` 更高效（操作系统可能使用零页映射）
- `sk_realloc_throw(addr, 0)` 特殊处理为 `sk_free(addr); return nullptr;`，避免标准库在 size=0 时的未定义行为
- `throw_on_failure` 的 `size > 0` 检查避免了 `malloc(0)` 返回 nullptr 时的误报
- `sk_abort_no_print` 在 Windows Debug 模式下使用 `__fastfail` 生成完整的崩溃转储

## 平台差异汇总

| 平台 | malloc 特殊处理 | abort 实现 | malloc_size API |
|------|----------------|-----------|-----------------|
| macOS/iOS | 无 | `__builtin_trap()` | `malloc_size()` |
| Android Framework | 临时禁用零初始化 | `abort()` | `malloc_usable_size()` |
| Linux | 无 | `__builtin_trap()` | `malloc_usable_size()` |
| Windows | 无 | `__fastfail()` (Debug) / `abort()` | `_msize()` |
| AFL Fuzz | 无 | `exit(1)` | 使用默认 size |

## 相关文件

- `include/private/base/SkMalloc.h` — 内存分配接口声明
- `src/ports/SkMemory_mozalloc.cpp` — Mozilla mozalloc 替代实现
- `include/private/base/SkDebug.h` — 调试工具（SK_DEBUGFAILF）
- `include/private/base/SkFeatures.h` — 平台特性检测
