# SkBlitRow_opts_lasx

> 源文件: src/core/SkBlitRow_opts_lasx.cpp

## 概述

`SkBlitRow_opts_lasx.cpp` 为龙芯架构（LoongArch）处理器提供了基于 LASX（LoongArch Advanced SIMD Extension）指令集的像素行混合优化实现。LASX 是龙芯架构的 256 位 SIMD 扩展，类似于 x86 的 AVX2。该文件作为条件编译单元，仅在龙芯平台且未启用大小优化时编译，为 `SkOpts` 命名空间注册两个核心行混合函数的 LASX 优化版本。

## 架构位置

该模块位于 Skia 的 CPU 特定优化层，是运行时函数调度系统的一部分：

```
SkOpts (运行时调度)
    ↓
SkBlitRow (行混合抽象接口)
    ↓
SkBlitRow_opts_lasx (龙芯 LASX 优化实现) ← 当前模块
    ↓
实际的 LASX 向量化代码 (src/opts/SkBlitRow_opts.h)
```

该模块与以下组件协同工作：

- **SkBlitRow**: 提供函数指针接口，定义需要优化的行混合操作
- **SkOpts_SetTarget / RestoreTarget**: 控制编译器目标 ISA
- **SkBlitRow_opts.h**: 包含实际的 LASX 向量化实现
- **SkBlitRow_opts.cpp**: 默认实现和初始化逻辑
- **SkCpu**: CPU 特性检测，决定是否调用 LASX 初始化

## 主要类与结构体

该文件不定义类或结构体，仅包含一个初始化函数。

## 公共 API 函数

### Init_BlitRow_lasx

```cpp
void Init_BlitRow_lasx();
```

在 `SkOpts` 命名空间中定义的初始化函数，将 LASX 优化的函数指针赋值给全局函数指针变量。

**功能:**
- 将 `lasx::blit_row_color32` 赋值给 `SkOpts::blit_row_color32`
- 将 `lasx::blit_row_s32a_opaque` 赋值给 `SkOpts::blit_row_s32a_opaque`

**调用时机:**
仅在以下条件同时满足时调用：
1. 编译平台为龙芯架构（`SK_CPU_LOONGARCH`）
2. 未启用大小优化（`!SK_ENABLE_OPTIMIZE_SIZE`）
3. 基线 LSX 级别低于 LASX（`SK_CPU_LSX_LEVEL < SK_CPU_LSX_LEVEL_LASX`）
4. 运行时 CPU 支持 LASX 指令（`SkCpu::Supports(SkCpu::LOONGARCH_ASX)`）

## 内部实现细节

### 条件编译保护

```cpp
#if defined(SK_CPU_LOONGARCH) && !defined(SK_ENABLE_OPTIMIZE_SIZE)
// ... 代码 ...
#endif
```

确保代码仅在龙芯平台且未优化大小时编译，避免在其他平台产生无用代码。

### 编译器目标设置

```cpp
#define SK_OPTS_TARGET SK_OPTS_TARGET_LASX
#include "src/opts/SkOpts_SetTarget.h"
```

设置编译器目标为 LASX 指令集，启用 `-mlasx` 等编译器标志。

```cpp
#include "src/opts/SkOpts_RestoreTarget.h"
```

恢复默认编译器目标，防止影响文件后续代码。

### 函数指针注册

```cpp
namespace SkOpts {
    void Init_BlitRow_lasx() {
        blit_row_color32     = lasx::blit_row_color32;
        blit_row_s32a_opaque = lasx::blit_row_s32a_opaque;
    }
}
```

将 `lasx` 命名空间（由 `SkBlitRow_opts.h` 定义）中的函数赋值给 `SkOpts` 命名空间的全局函数指针。

### 优化的函数

#### blit_row_color32
```cpp
void blit_row_color32(SkPMColor dst[], SkPMColor src, int count);
```

使用 LASX 指令将纯色 `src` 复制到 `dst` 数组，一次处理多个像素（通常 8 个，因为 LASX 是 256 位）。

#### blit_row_s32a_opaque
```cpp
void blit_row_s32a_opaque(SkPMColor dst[], const SkPMColor src[], int count, U8CPU alpha);
```

使用 LASX 指令将源像素数组 `src` 混合到 `dst`，假设源像素已预乘 alpha 且不透明，使用给定的全局 `alpha` 值。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkFeatures.h` | 提供平台特性宏定义 |
| `SkBlitRow.h` | 定义行混合函数接口 |
| `SkOptsTargets.h` | 定义 CPU 目标宏（`SK_OPTS_TARGET_LASX`） |
| `SkOpts_SetTarget.h` | 设置编译器目标 ISA |
| `SkBlitRow_opts.h` | 包含实际的 LASX 向量化实现 |
| `SkOpts_RestoreTarget.h` | 恢复默认编译器目标 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SkBlitRow_opts.cpp` | 在运行时根据 CPU 特性调用 `Init_BlitRow_lasx` |
| `SkBlitRow` | 通过函数指针使用 LASX 优化的实现 |
| `SkBlitter_ARGB32.cpp` | 间接使用行混合函数进行像素绘制 |

## 设计模式与设计决策

### 运行时函数调度模式

Skia 使用运行时函数指针替换实现 CPU 特定优化，而非编译时条件编译：

1. **默认实现**: 提供可移植的基线实现
2. **特性检测**: 运行时检测 CPU 是否支持特定指令集
3. **函数替换**: 如果支持，将函数指针替换为优化版本

这种设计允许单个二进制文件支持多种 CPU，并自动选择最优实现。

### 编译器目标隔离

使用 `SkOpts_SetTarget.h` 和 `SkOpts_RestoreTarget.h` 确保 LASX 指令仅在特定代码段启用：

- **优点**: 避免整个编译单元使用 LASX，防止编译器在不支持的路径生成 LASX 代码
- **实现**: 通过编译器特定的 pragma 或命令行标志控制

### 条件编译优化

仅在必要平台编译优化代码，减小二进制大小：

```cpp
#if defined(SK_CPU_LOONGARCH) && !defined(SK_ENABLE_OPTIMIZE_SIZE)
```

- 在非龙芯平台上，整个文件变为空文件
- 在优化大小的构建中，跳过 SIMD 优化以减小代码体积

### 命名空间隔离

将 LASX 实现放在 `lasx::` 命名空间，避免与其他平台的实现冲突（如 `hsw::`、`avx::`）。

## 性能考量

### LASX 指令集优势

LASX 提供 256 位 SIMD 寄存器，一次可处理：
- **8 个 32 位像素** (`SkPMColor`)
- **16 个 16 位值**
- **32 个 8 位值**

相比标量代码，理论性能提升可达 8 倍（实际通常为 4-6 倍，考虑内存带宽和指令延迟）。

### 内存带宽

LASX 操作通常受内存带宽限制而非计算限制，因为：
- 像素数据读写是主要开销
- 混合计算相对简单

因此，对齐的内存访问和缓存局部性至关重要。

### 函数指针开销

函数指针调用有轻微开销，但相比于处理的像素数量（通常数百或数千），这个开销可忽略。

### 条件编译开销

在不支持的平台上，该文件编译为空，不产生任何代码或数据，完全没有运行时开销。

## 相关文件

| 文件路径 | 关系 |
|---------|------|
| `src/core/SkBlitRow.h` | 行混合函数接口定义 |
| `src/core/SkBlitRow_opts.cpp` | 默认实现和初始化调度逻辑 |
| `src/core/SkBlitRow_opts_hsw.cpp` | x86 HSW（AVX2）对应实现 |
| `src/opts/SkBlitRow_opts.h` | 实际的 SIMD 向量化代码 |
| `src/opts/SkOpts_SetTarget.h` | 编译器目标设置工具 |
| `src/opts/SkOpts_RestoreTarget.h` | 编译器目标恢复工具 |
| `src/core/SkOptsTargets.h` | CPU 目标宏定义 |
| `src/core/SkCpu.h` | CPU 特性检测接口 |
| `include/private/base/SkFeatures.h` | 平台特性宏 |
| `src/core/SkBlitter_ARGB32.cpp` | 使用行混合函数的 blitter 实现 |
