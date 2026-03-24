# SkMemory_mozalloc

> 源文件: [src/ports/SkMemory_mozalloc.cpp](../../../../src/ports/SkMemory_mozalloc.cpp)

## 概述

本文件实现了 Skia 的内存分配接口的 Mozilla mozalloc 后端。当 Skia 在 Mozilla Firefox 浏览器中使用时，内存分配需要通过 Mozilla 的自定义分配器 (`mozalloc`) 进行，以确保与浏览器的内存管理和 OOM (Out-Of-Memory) 处理策略一致。

## 架构位置

本文件是 Skia 内存管理的可替代后端，与 `SkMemory_malloc.cpp` 互斥编译:

```
include/private/base/SkMalloc.h (接口声明)
  ├── src/ports/SkMemory_malloc.cpp   (默认: 标准 malloc)
  └── src/ports/SkMemory_mozalloc.cpp (本文件: Mozilla 环境)
```

## 主要类与结构体

本文件不定义类或结构体。

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `void sk_abort_no_print()` | 通过 `mozalloc_abort` 终止程序 |
| `void sk_out_of_memory(void)` | 通过 `mozalloc_handle_oom` 处理内存耗尽 |
| `void sk_free(void* p)` | 直接调用 `free()` 释放内存 |
| `void* sk_realloc_throw(void* addr, size_t size)` | 使用 `moz_xrealloc` 重分配（失败时终止） |
| `void* sk_malloc_flags(size_t size, unsigned flags)` | 根据标志选择 mozalloc 或标准分配函数 |
| `size_t sk_malloc_size(void* addr, size_t size)` | 使用 `moz_malloc_usable_size` 查询实际分配大小 |

## 内部实现细节

### sk_malloc_flags - 分配策略

根据 flags 的不同组合选择分配函数:

| SK_MALLOC_ZERO_INITIALIZE | SK_MALLOC_THROW | 调用函数 |
|:---:|:---:|:---|
| 是 | 是 | `moz_xcalloc(size, 1)` — 零初始化 + 失败终止 |
| 是 | 否 | `calloc(size, 1)` — 零初始化 + 返回 nullptr |
| 否 | 是 | `moz_xmalloc(size)` — 失败终止 |
| 否 | 否 | `malloc(size)` — 返回 nullptr |

`moz_x*` 系列函数在分配失败时会自动触发 Mozilla 的 OOM 处理流程（终止进程并报告），因此带 `SK_MALLOC_THROW` 标志时使用它们。

### sk_free 与 malloc 的关系

与 `SkMemory_malloc.cpp` 不同，mozalloc 版本的 `sk_free` 不包含 null 守卫:
```cpp
void sk_free(void* p) {
    free(p);  // 直接调用，无 null 检查
}
```
这是因为 Mozilla 的 `free` 实现已经处理了 null 指针。

### sk_abort_no_print

使用 `mozalloc_abort("Abort from sk_abort")`，带有描述性消息，这与标准 malloc 版本的无消息终止不同。

### sk_out_of_memory

先触发调试断言 (`SkDEBUGFAIL`)，然后调用 `mozalloc_handle_oom(0)` 让 Mozilla 的 OOM 处理器接管。参数 `0` 表示未指定分配大小。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/private/base/SkMalloc.h` | Skia 内存分配接口 |
| `include/core/SkTypes.h` | 基础类型 |
| `mozilla/mozalloc.h` | Mozilla 分配器 (moz_xmalloc, moz_xcalloc, moz_xrealloc) |
| `mozilla/mozalloc_abort.h` | Mozilla 终止函数 |
| `mozilla/mozalloc_oom.h` | Mozilla OOM 处理 |
| `<algorithm>` | std::max |

## 设计模式与设计决策

1. **可插拔内存后端**: 通过编译时替换 `.cpp` 文件实现内存分配策略的切换
2. **与浏览器 OOM 集成**: `moz_x*` 函数的失败处理路径与 Firefox 的崩溃报告系统集成
3. **最小接口差异**: 与 `SkMemory_malloc.cpp` 实现相同的函数签名，确保透明替换
4. **条件使用 mozalloc**: 仅在需要抛出异常 (`SK_MALLOC_THROW`) 时使用 `moz_x*`，非异常路径使用标准 `malloc/calloc`

## 性能考量

- mozalloc 函数本身是标准分配器的薄封装，额外开销极小
- `sk_free` 不含 null 守卫，比 malloc 版本少一次分支判断
- `moz_malloc_usable_size` 提供实际分配大小查询，允许上层代码利用多余空间

## 相关文件

- `include/private/base/SkMalloc.h` — 内存分配接口声明
- `src/ports/SkMemory_malloc.cpp` — 标准 malloc 替代实现
