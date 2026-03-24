# SkBlitRow_opts_hsw

> 源文件: src/core/SkBlitRow_opts_hsw.cpp

## 概述

`SkBlitRow_opts_hsw.cpp` 为 Intel Haswell（及更新）架构提供了基于 AVX2 指令集的像素行混合优化实现。HSW（Haswell）是 Intel 第四代酷睿处理器的代号，首次引入 AVX2 扩展，提供 256 位整数 SIMD 操作。该文件作为条件编译单元，仅在 x86 平台且未启用大小优化时编译，为 `SkOpts` 命名空间注册两个核心行混合函数的 AVX2 优化版本。

## 架构位置

该模块位于 Skia 的 CPU 特定优化层，是运行时函数调度系统的一部分：

```
SkOpts (运行时调度)
    ↓
SkBlitRow (行混合抽象接口)
    ↓
SkBlitRow_opts_hsw (Intel AVX2 优化实现) ← 当前模块
    ↓
实际的 AVX2 向量化代码 (src/opts/SkBlitRow_opts.h)
```

该模块与以下组件协同工作：

- **SkBlitRow**: 提供函数指针接口，定义需要优化的行混合操作
- **SkOpts_SetTarget / RestoreTarget**: 控制编译器目标 ISA
- **SkBlitRow_opts.h**: 包含实际的 AVX2 向量化实现
- **SkBlitRow_opts.cpp**: 默认实现和初始化逻辑
- **SkCpu**: CPU 特性检测，决定是否调用 HSW 初始化

## 主要类与结构体

该文件不定义类或结构体，仅包含一个初始化函数。

## 公共 API 函数

### Init_BlitRow_hsw

```cpp
void Init_BlitRow_hsw();
```

在 `SkOpts` 命名空间中定义的初始化函数，将 AVX2 优化的函数指针赋值给全局函数指针变量。

**功能:**
- 将 `hsw::blit_row_color32` 赋值给 `SkOpts::blit_row_color32`
- 将 `hsw::blit_row_s32a_opaque` 赋值给 `SkOpts::blit_row_s32a_opaque`

**调用时机:**
仅在以下条件同时满足时调用：
1. 编译平台为 x86/x86_64（`SK_CPU_X86`）
2. 未启用大小优化（`!SK_ENABLE_OPTIMIZE_SIZE`）
3. 基线 SSE 级别低于 AVX2（`SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_AVX2`）
4. 运行时 CPU 支持 AVX2 指令（`SkCpu::Supports(SkCpu::HSW)`）

## 内部实现细节

### 条件编译保护

```cpp
#if defined(SK_CPU_X86) && !defined(SK_ENABLE_OPTIMIZE_SIZE)
// ... 代码 ...
#endif
```

确保代码仅在 x86 平台且未优化大小时编译，避免在其他平台产生无用代码。

### 编译器目标设置

```cpp
#define SK_OPTS_TARGET SK_OPTS_TARGET_HSW
#include "src/opts/SkOpts_SetTarget.h"
```

设置编译器目标为 Haswell（AVX2）指令集，启用 `-mavx2 -mfma -mf16c -mbmi -mbmi2` 等编译器标志。

```cpp
#include "src/opts/SkOpts_RestoreTarget.h"
```

恢复默认编译器目标，防止影响文件后续代码。

### 函数指针注册

```cpp
namespace SkOpts {
    void Init_BlitRow_hsw() {
        blit_row_color32     = hsw::blit_row_color32;
        blit_row_s32a_opaque = hsw::blit_row_s32a_opaque;
    }
}
```

将 `hsw` 命名空间（由 `SkBlitRow_opts.h` 定义）中的函数赋值给 `SkOpts` 命名空间的全局函数指针。

### 优化的函数

#### blit_row_color32
```cpp
void blit_row_color32(SkPMColor dst[], SkPMColor src, int count);
```

使用 AVX2 指令将纯色 `src` 复制到 `dst` 数组，一次处理 8 个像素（256 位 / 32 位 = 8）。

**AVX2 优势:**
- 使用 `_mm256_set1_epi32(src)` 广播颜色值
- 使用 `_mm256_storeu_si256` 一次写入 8 个像素
- 相比 SSE2 的 4 像素处理，吞吐量翻倍

#### blit_row_s32a_opaque
```cpp
void blit_row_s32a_opaque(SkPMColor dst[], const SkPMColor src[], int count, U8CPU alpha);
```

使用 AVX2 指令将源像素数组 `src` 混合到 `dst`，假设源像素已预乘 alpha 且不透明，使用给定的全局 `alpha` 值。

**AVX2 优势:**
- 使用 `_mm256_loadu_si256` 一次加载 8 个源像素
- 使用 `_mm256_mullo_epi16` 进行向量化乘法
- 使用 `_mm256_packus_epi16` 打包结果
- 显著减少循环迭代次数

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkFeatures.h` | 提供平台特性宏定义 |
| `SkBlitRow.h` | 定义行混合函数接口 |
| `SkOptsTargets.h` | 定义 CPU 目标宏（`SK_OPTS_TARGET_HSW`） |
| `SkOpts_SetTarget.h` | 设置编译器目标 ISA |
| `SkBlitRow_opts.h` | 包含实际的 AVX2 向量化实现 |
| `SkOpts_RestoreTarget.h` | 恢复默认编译器目标 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SkBlitRow_opts.cpp` | 在运行时根据 CPU 特性调用 `Init_BlitRow_hsw` |
| `SkBlitRow` | 通过函数指针使用 AVX2 优化的实现 |
| `SkBlitter_ARGB32.cpp` | 间接使用行混合函数进行像素绘制 |

## 设计模式与设计决策

### 运行时函数调度模式

Skia 使用运行时函数指针替换实现 CPU 特定优化，而非编译时条件编译：

1. **默认实现**: 提供基于 SSE2 的基线实现（x86 平台的最低要求）
2. **特性检测**: 运行时检测 CPU 是否支持 AVX2（Haswell 或更新）
3. **函数替换**: 如果支持，将函数指针替换为 AVX2 优化版本

这种设计允许单个二进制文件支持从 Nehalem（2008）到最新 CPU 的所有 Intel 处理器。

### 编译器目标隔离

使用 `SkOpts_SetTarget.h` 和 `SkOpts_RestoreTarget.h` 确保 AVX2 指令仅在特定代码段启用：

- **防止非法指令**: 在不支持 AVX2 的 CPU 上，如果编译器在非保护代码中生成 AVX2 指令，会导致程序崩溃
- **实现**: 在 GCC/Clang 中使用 `#pragma GCC target("avx2")`，在 MSVC 中使用 `/arch:AVX2`

### 条件编译优化

仅在 x86 平台编译 AVX2 代码：

```cpp
#if defined(SK_CPU_X86) && !defined(SK_ENABLE_OPTIMIZE_SIZE)
```

- 在 ARM、龙芯等平台上，整个文件为空
- 在优化大小的构建中，跳过 SIMD 优化以减小代码体积

### 命名空间隔离

将 AVX2 实现放在 `hsw::` 命名空间，避免与其他优化级别冲突：
- `sse2::` - 基线 SSE2 实现
- `hsw::` - Haswell AVX2 实现
- `skx::` - Skylake-X AVX-512 实现（如果存在）

## 性能考量

### AVX2 指令集优势

AVX2 提供 256 位 SIMD 寄存器，相比 SSE2 的 128 位寄存器：
- **宽度翻倍**: 一次处理 8 个 32 位像素 vs 4 个
- **新指令**: 提供更强大的整数操作（如 `_mm256_mullo_epi32`）
- **性能提升**: 理论上接近 2 倍，实际通常为 1.5-1.8 倍（受内存带宽限制）

### 内存带宽考量

AVX2 优化通常受内存带宽限制：
- **读取**: 每次循环读取 32 字节（8 个像素）
- **写入**: 每次循环写入 32 字节
- **总带宽**: 64 字节/迭代，接近现代 CPU 的缓存行大小

因此，内存对齐和缓存友好的访问模式至关重要。

### 分支预测友好

循环结构简单，分支可预测：
```cpp
while (count >= 8) {
    // AVX2 处理
    count -= 8;
}
while (count > 0) {
    // 标量处理尾部
    count--;
}
```

### 函数指针开销

虽然使用函数指针间接调用，但：
- 调用一次处理大量像素（通常数百个）
- 现代 CPU 的分支预测器能准确预测间接跳转
- 开销相比像素处理时间可忽略

### Haswell 微架构优势

Haswell 引入的特性使 AVX2 更高效：
- **融合乘加（FMA）**: 一条指令完成乘法和加法
- **更宽的执行单元**: 支持 256 位向量操作
- **改进的内存子系统**: 更好的非对齐访问性能

## 相关文件

| 文件路径 | 关系 |
|---------|------|
| `src/core/SkBlitRow.h` | 行混合函数接口定义 |
| `src/core/SkBlitRow_opts.cpp` | 默认实现和初始化调度逻辑 |
| `src/core/SkBlitRow_opts_lasx.cpp` | 龙芯 LASX 对应实现 |
| `src/opts/SkBlitRow_opts.h` | 实际的 SIMD 向量化代码 |
| `src/opts/SkOpts_SetTarget.h` | 编译器目标设置工具 |
| `src/opts/SkOpts_RestoreTarget.h` | 编译器目标恢复工具 |
| `src/core/SkOptsTargets.h` | CPU 目标宏定义 |
| `src/core/SkCpu.h` | CPU 特性检测接口 |
| `include/private/base/SkFeatures.h` | 平台特性宏 |
| `src/core/SkBlitter_ARGB32.cpp` | 使用行混合函数的 blitter 实现 |
