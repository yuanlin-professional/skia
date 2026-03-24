# SkMemset_opts

> 源文件: `src/opts/SkMemset_opts.h`

## 概述

`SkMemset_opts.h` 提供了 Skia 图形库中针对 16 位、32 位和 64 位数据类型的优化内存填充（memset）函数。与标准库的 `memset` 仅支持逐字节填充不同，本文件中的函数允许以特定宽度的值填充内存区域，这在图形渲染中极为常见（例如用某个颜色值填充像素缓冲区）。

该文件利用 SIMD 向量化技术（通过 `SkVx.h` 提供的跨平台向量抽象），在支持 AVX 的平台上使用 256 位向量操作，在其他平台上使用 128 位向量操作，以实现比标量循环更高的填充吞吐量。

## 架构位置

该文件位于 `src/opts/` 目录下，属于 Skia 的 **平台优化层（opts layer）**。它通过 `SK_OPTS_NS` 命名空间机制被编入多个架构特化版本中：

```
应用层（SkCanvas、SkBitmap 等）
  -> 核心层（SkOpts::memset16/32/64）
       -> 优化层（SK_OPTS_NS::memset16/32/64）   <-- 本文件
            -> 底层向量抽象（skvx::Vec）
                 -> CPU SIMD 指令（SSE2/AVX/NEON/LSX 等）
```

在实际调用链中，`SkOpts::memset32` 等函数指针指向本文件中对应的实现，通过运行时分发选择最佳版本。

## 主要类与结构体

本文件不定义类或结构体，仅包含模板函数和内联函数。

### 模板函数

#### `memsetT<T>`

```cpp
template <typename T>
static void memsetT(T buffer[], T value, int count);
```

核心的泛型内存填充模板。根据编译时的 CPU 指令级别自动选择向量宽度：

- **AVX 平台** (`SK_CPU_SSE_LEVEL >= SK_CPU_SSE_LEVEL_AVX`): 使用 `32 / sizeof(T)` 个元素的向量（256 位）
- **其他平台**: 使用 `16 / sizeof(T)` 个元素的向量（128 位）

#### `rect_memsetT<T>`

```cpp
template <typename T>
static void rect_memsetT(T buffer[], T value, int count, size_t rowBytes, int height);
```

矩形区域内存填充模板，按行逐行调用 `memsetT`，支持行间步幅（rowBytes）不等于行宽的情况（例如带有行内边距的像素缓冲区）。

## 公共 API 函数

### 线性填充函数

| 函数 | 签名 | 说明 |
|------|------|------|
| `memset16` | `void memset16(uint16_t buffer[], uint16_t value, int count)` | 用 16 位值填充缓冲区 |
| `memset32` | `void memset32(uint32_t buffer[], uint32_t value, int count)` | 用 32 位值填充缓冲区（常用于 ARGB 颜色填充） |
| `memset64` | `void memset64(uint64_t buffer[], uint64_t value, int count)` | 用 64 位值填充缓冲区 |

### 矩形填充函数

| 函数 | 签名 | 说明 |
|------|------|------|
| `rect_memset16` | `void rect_memset16(uint16_t[], uint16_t, int, size_t, int)` | 按行填充 16 位值的矩形区域 |
| `rect_memset32` | `void rect_memset32(uint32_t[], uint32_t, int, size_t, int)` | 按行填充 32 位值的矩形区域 |
| `rect_memset64` | `void rect_memset64(uint64_t[], uint64_t, int, size_t, int)` | 按行填充 64 位值的矩形区域 |

所有公共函数均标记为 `/*not static*/ inline`，这是 SkOpts 系统的约定：非 static 以便外部可以获取函数指针，inline 以便在同一编译单元中使用时可以被内联。

## 内部实现细节

### 向量化填充算法

`memsetT` 的实现分为两个阶段：

1. **向量化主循环**: 将填充值广播到 `skvx::Vec<VecSize, T>` 向量中，然后以 `VecSize` 个元素为步长写入目标缓冲区。每次写入操作等价于一条 SIMD store 指令（如 `_mm256_storeu_si256` 或 `vst1q_u32`）。

```cpp
skvx::Vec<VecSize,T> wideValue(value);
while (count >= VecSize) {
    wideValue.store(buffer);
    buffer += VecSize;
    count  -= VecSize;
}
```

2. **标量尾部处理**: 当剩余元素不足一个向量宽度时，退回标量逐元素填充。

```cpp
while (count-- > 0) {
    *buffer++ = value;
}
```

### 向量宽度选择

通过编译时条件判断选择向量宽度：

| 平台 | 向量字节数 | uint16_t 向量元素数 | uint32_t 向量元素数 | uint64_t 向量元素数 |
|------|-----------|-------------------|-------------------|-------------------|
| AVX  | 32 字节    | 16                | 8                 | 4                 |
| 其他  | 16 字节    | 8                 | 4                 | 2                 |

### 矩形填充的行步进

`rect_memsetT` 使用字符指针算术来按行步进，以正确处理 `rowBytes > count * sizeof(T)` 的情况：

```cpp
buffer = (T*)((char*)buffer + rowBytes);
```

这种设计确保了即使缓冲区有行对齐填充（padding），也能正确定位到下一行的起始位置。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `<stdint.h>` | 标准整数类型定义 |
| `src/base/SkVx.h` | Skia 的跨平台 SIMD 向量抽象库（`skvx::Vec`） |
| `SK_CPU_SSE_LEVEL` 编译宏 | 用于在编译时选择向量宽度 |

## 设计模式与设计决策

### 模板泛化

使用 `memsetT<T>` 模板将 16/32/64 位填充统一到同一算法中，避免代码重复。类型参数 `T` 自动决定每个向量能容纳的元素数量。

### skvx 抽象层

依赖 `skvx::Vec` 而非直接使用平台特定的内建函数（如 `_mm_set1_epi32`），使得代码在所有支持平台上可移植。`skvx` 会在编译时自动将 `Vec::store()` 等操作映射到最佳的 SIMD 指令。

### `/*not static*/ inline` 约定

Skia opts 系统中的一个重要约定。这些函数不能声明为 `static`，因为它们需要被外部代码通过函数指针引用（在 `SkOpts::Init()` 期间）。同时标记为 `inline` 以允许编译器在直接调用时内联优化。

### 向量宽度仅区分 AVX 和非 AVX

设计上只区分了两个级别（256 位 AVX 和 128 位其他），而没有为 AVX-512 提供 512 位版本。这可能是因为 memset 操作主要受限于内存带宽而非计算吞吐量，更宽的向量在此场景中收益有限。

## 性能考量

- **内存带宽受限**: memset 是典型的内存带宽受限操作，向量化的主要收益在于减少 store 指令数量和循环开销
- **对齐问题**: 当前实现使用非对齐 store（通过 `skvx::Vec::store()`），现代 CPU 上非对齐 store 的性能惩罚已经很小
- **尾部处理开销**: 标量尾部循环最多执行 `VecSize - 1` 次迭代。对于大缓冲区，这一开销可忽略不计
- **矩形填充的缓存行为**: 逐行填充的访问模式对缓存友好，因为每行是连续内存访问
- **编译器自动向量化**: 现代编译器可能对简单的标量 memset 循环自动向量化，但显式使用 SIMD 可以确保在所有优化级别下都获得向量化

## 相关文件

- `src/base/SkVx.h` - Skia 跨平台 SIMD 向量抽象库
- `src/core/SkOpts.h` - SkOpts 命名空间声明，包含 `memset16`/`memset32`/`memset64` 函数指针
- `src/core/SkOpts.cpp` - 函数指针的默认初始化
- `include/core/SkColor.h` - `SkPMColor` 等类型定义（memset32 的常见使用场景）
- `src/core/SkDraw.cpp` - 绘制操作中 memset 的典型调用方
- `src/core/SkBlitter.cpp` - 像素填充操作中的 memset 使用
