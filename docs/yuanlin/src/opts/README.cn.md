# src/opts - SIMD 优化代码路径模块

## 概述

`src/opts` 是 Skia 中集中管理 SIMD（单指令多数据）优化代码路径的核心模块。该模块利用各种处理器的向量指令集（SSE2、SSSE3、SSE4.1、AVX、AVX2/HSW、AVX-512/SKX、ARM NEON、LoongArch LSX/LASX）对 Skia 最关键的像素处理操作进行加速。这些优化覆盖了光栅化管线、位图采样、像素混合、掩码绘制、内存填充和颜色格式转换等核心功能。

本模块的设计核心是一套精巧的编译时多目标架构（Multi-Target Architecture）系统。通过 `SkOpts_SetTarget.h` 和 `SkOpts_RestoreTarget.h` 这对头文件，同一份优化代码（如 `SkRasterPipeline_opts.h`）可以在不同的编译目标下被多次包含，每次编译时通过 `#pragma clang attribute push` 或 `#pragma GCC target` 启用不同的指令集扩展。每个目标会生成一个独立命名空间（如 `hsw`、`skx`、`avx`）中的函数，并在运行时通过 CPU 特性检测选择最佳实现。

`SkRasterPipeline_opts.h` 是本模块中最庞大且最重要的文件，它实现了 Skia 光栅化管线（Raster Pipeline）的所有阶段函数。光栅化管线是 Skia 的核心像素处理引擎，几乎所有的 CPU 端 2D 渲染操作最终都通过这个管线执行。该文件定义了自己的 SIMD 向量类型（使用编译器扩展 `__attribute__((ext_vector_type))` 而非 SkVx），以确保向量参数能通过硬件寄存器传递，这是光栅化管线高性能的关键设计决策。

除光栅化管线外，模块中的其他优化文件使用 Skia 的通用 SIMD 封装库 SkVx（`src/base/SkVx.h`）编写，在保持代码可读性的同时获得良好的跨平台向量化性能。所有代码都放置在 `SK_OPTS_NS` 命名空间中，运行时系统通过函数指针表将这些命名空间中的函数绑定到全局入口点（`SkOpts::*`）。

## 架构图

```
+-------------------------------------------------------------------+
|                    运行时 CPU 特性检测                               |
|  SkOpts::Init() -> SkCpu::Supports(SkCpu::HSW/SKX/...)            |
+-------------------------------------------------------------------+
                              |
              +---------------+------------------+
              |               |                  |
              v               v                  v
      +-------------+  +-------------+  +------------------+
      | 默认目标     |  | HSW 目标     |  | SKX 目标          |
      | (SSE2/NEON/ |  | (AVX2+FMA+  |  | (AVX-512+VNNI)   |
      |  portable)  |  |  BMI2+F16C) |  |                  |
      +-------------+  +-------------+  +------------------+
              |               |                  |
              v               v                  v
+-------------------------------------------------------------------+
|                    SkOpts 函数指针表                                |
|  ops_highp[], ops_lowp[], start_pipeline_highp/lowp               |
|  blit_row_s32a_opaque, blit_mask_d32_a8, memset16/32/64           |
|  S32_alpha_D32_filter_DX, RGBA_to_BGRA, ...                      |
+-------------------------------------------------------------------+
              |
              v
+-------------------------------------------------------------------+
|                    Skia 核心渲染引擎                                |
|  SkRasterPipeline, SkBlitter, SkBitmapProcState, SkSwizzler       |
+-------------------------------------------------------------------+

编译时目标选择机制:
+------------------------------------------------------------+
| SkOpts_SetTarget.h                                         |
|   #define SK_OPTS_TARGET SK_OPTS_TARGET_HSW                |
|   #pragma clang attribute push(target("avx2,fma,..."))     |
|   #define SK_OPTS_NS hsw                                   |
|   #define SK_CPU_SSE_LEVEL SK_CPU_SSE_LEVEL_AVX2           |
+------------------------------------------------------------+
              |
              v  (包含优化代码头文件)
+------------------------------------------------------------+
| SkRasterPipeline_opts.h / SkBlitRow_opts.h / 等             |
| 所有函数生成到 namespace hsw { ... }                        |
+------------------------------------------------------------+
              |
              v
+------------------------------------------------------------+
| SkOpts_RestoreTarget.h                                     |
|   #pragma clang attribute pop                              |
|   #undef SK_CPU_SSE_LEVEL / 恢复原始值                      |
+------------------------------------------------------------+
```

## 目录结构

```
src/opts/
|-- BUILD.bazel                   # Bazel 构建配置
|-- SkRasterPipeline_opts.h       # 光栅化管线所有阶段的 SIMD 实现
|-- SkBitmapProcState_opts.h      # 位图采样优化 (双线性过滤)
|-- SkBlitMask_opts.h             # 掩码混合优化 (A8 掩码 -> D32)
|-- SkBlitRow_opts.h              # 像素行混合优化 (SrcOver)
|-- SkMemset_opts.h               # 内存填充优化 (memset16/32/64)
|-- SkSwizzler_opts.inc           # 颜色格式转换优化 (RGBA<->BGRA等)
|-- SkOpts_SetTarget.h            # 编译目标设置（定义指令集和命名空间）
|-- SkOpts_RestoreTarget.h        # 编译目标恢复（取消指令集设置）
|-- SkOpts_hsw.cpp                # HSW (Haswell/AVX2) 目标编译单元
|-- SkOpts_skx.cpp                # SKX (Skylake-X/AVX-512) 目标编译单元
|-- SkOpts_lasx.cpp               # LASX (LoongArch 高级SIMD) 目标编译单元
```

## 关键类与函数

### SkRasterPipeline_opts.h（光栅化管线优化）
```cpp
// 自定义 SIMD 向量类型（非 SkVx，为寄存器传递优化）
template <int N, typename T> using Vec = T __attribute__((ext_vector_type(N)));

// SIMD 宽度根据目标自动选择
// NEON:    N=4 (128-bit)
// SSE2:    N=4 (128-bit)
// HSW:     N=8 (256-bit)
// SKX:     N=16 (512-bit)

// 管线阶段函数签名
using Stage = void(Params*, SkRasterPipelineStage*, ...);
// 8个参数直接映射到硬件寄存器: r,g,b,a, dr,dg,db,da
```
这是整个模块中最核心的文件。它为 SkRasterPipeline 的每个操作阶段（如 `load_8888`、`store_8888`、`srcover_rgba_8888`、`premul`、`matrix_2x3` 等几十个阶段）提供了多种 SIMD 宽度的实现。关键设计决策：
- 使用编译器向量扩展替代 SkVx，确保参数通过寄存器传递
- 每个阶段函数是尾调用链的一环，由管线启动器驱动
- 高精度路径（highp，float）和低精度路径（lowp，uint16_t）两套管线

### SkBitmapProcState_opts.h（位图采样优化）
```cpp
namespace SK_OPTS_NS {
    void S32_alpha_D32_filter_DX(const SkBitmapProcState& s,
                                  const uint32_t* xy, int count,
                                  uint32_t* colors);
    void S32_alpha_D32_filter_DXDY(const SkBitmapProcState& s,
                                    const uint32_t* xy, int count,
                                    SkPMColor* colors);
}
```
实现了双线性纹理过滤的 SIMD 优化版本。核心操作是对 2x2 像素网格进行加权插值。提供了五种架构特定实现：
- **SSSE3**: 利用 `_mm_maddubs_epi16()` 进行高效的字节级乘加，一次处理4个像素
- **SSE2**: 使用基础的 16 位乘法和移位运算
- **NEON**: 利用 `vmull_u8` 和 `vmla_u16` 进行向量乘加
- **LASX**: LoongArch 256 位高级 SIMD 实现
- **LSX**: LoongArch 128 位 SIMD 实现
- **通用**: 纯标量回退实现

### SkBlitRow_opts.h（像素行混合优化）
```cpp
// SrcOver 混合：b = s + d * (1 - srcA)
// 近似优化：b = s + (d * (256 - srcA)) >> 8

// AVX2 版本 - 一次处理 8 个像素
static inline __m256i SkPMSrcOver_AVX2(const __m256i& src, const __m256i& dst);

// SSE2 版本 - 一次处理 4 个像素
static inline __m128i SkPMSrcOver_SSE2(const __m128i& src, const __m128i& dst);

// NEON 版本 - 使用交错加载一次处理 8 个像素
static inline uint8x8x4_t SkPMSrcOver_neon8(uint8x8x4_t dst, uint8x8x4_t src);

// LASX/LSX 版本 - LoongArch SIMD
static inline __m256i SkPMSrcOver_LASX(const __m256i& src, const __m256i& dst);

namespace SK_OPTS_NS {
    void blit_row_s32a_opaque(SkPMColor* dst, const SkPMColor* src, int len, U8CPU alpha);
    void blit_row_color32(SkPMColor* dst, int count, SkPMColor color);
}
```
`blit_row_s32a_opaque` 是 Skia 中最频繁调用的混合函数之一。它实现了预乘 Alpha SrcOver 混合操作。代码设计上使用了"瀑布式"（waterfall）分发策略：先尝试最宽的 SIMD 宽度（AVX2 处理8个像素），然后回退到较窄的宽度（SSE2 处理4个像素），最后用标量处理剩余像素。安全性方面特别注意不使用数据相关的分支（如 `vpmovmskb` + 条件跳转）以防止时序攻击。

### SkBlitMask_opts.h（掩码混合优化）
```cpp
namespace SK_OPTS_NS {
    void blit_mask_d32_a8(SkPMColor* dst, size_t dstRB,
                           const SkAlpha* mask, size_t maskRB,
                           SkColor color, int w, int h);
}
```
将 A8 格式的 Alpha 掩码与颜色混合后绘制到 32 位目标像素。根据颜色特性分为三个优化路径：
- `blit_mask_d32_a8_black` - 颜色为黑色（最简单，只需 Alpha 通道操作）
- `blit_mask_d32_a8_opaque` - 颜色不透明（省略颜色 Alpha 乘法）
- `blit_mask_d32_a8_general` - 半透明颜色（完整混合计算）

NEON 实现使用 `vld4_u8` 交错加载将 BGRA 分离为四个独立通道，LSX 实现使用 shuffle 操作实现类似的通道分离。

### SkMemset_opts.h（内存填充优化）
```cpp
namespace SK_OPTS_NS {
    void memset16(uint16_t buffer[], uint16_t value, int count);
    void memset32(uint32_t buffer[], uint32_t value, int count);
    void memset64(uint64_t buffer[], uint64_t value, int count);
    void rect_memset16/32/64(...);  // 矩形区域填充
}
```
使用 SkVx 向量类型实现高效的内存填充操作。AVX 模式下使用 256 位（32字节）向量，其他模式使用 128 位（16字节）向量。通过模板统一实现 16/32/64 位三种宽度。`rect_memset*` 变体支持按行步进的矩形区域填充。

### SkSwizzler_opts.inc（颜色格式转换优化）
```cpp
namespace SK_OPTS_NS {
    SI float reciprocal_alpha_times_255(float a);  // 安全除法（防时序攻击）
    SI float reciprocal_alpha(float a);

    // 格式转换函数（在不同目标中多次编译）
    // RGBA <-> BGRA 通道交换
    // 预乘/反预乘 Alpha 处理
}
```
该文件被设计为 `.inc` 格式（而非 `.h`），因为它需要在多个编译单元中以不同的指令集目标被包含。它实现了颜色格式之间的高效转换，包括通道重排（RGBA/BGRA 互转）和 Alpha 预乘/反预乘操作。SSE 实现使用条件屏蔽（`_mm_and_ps` + 比较结果）替代分支来处理 Alpha 为零的情况，防止时序攻击。

### SkOpts_SetTarget.h / SkOpts_RestoreTarget.h（目标切换机制）
```cpp
// SkOpts_SetTarget.h - 设置编译目标
#if SK_OPTS_TARGET == SK_OPTS_TARGET_HSW
    #define SK_CPU_SSE_LEVEL SK_CPU_SSE_LEVEL_AVX2
    #define SK_OPTS_NS hsw
    #pragma clang attribute push(
        __attribute__((target("sse2,ssse3,sse4.1,sse4.2,avx,avx2,bmi,bmi2,f16c,fma"))),
        apply_to=function)
#endif

// SkOpts_RestoreTarget.h - 恢复编译目标
#undef SK_CPU_SSE_LEVEL
#define SK_CPU_SSE_LEVEL SK_OLD_CPU_SSE_LEVEL
#pragma clang attribute pop
```
这对头文件是整个多目标编译系统的核心。支持的目标包括：
- `SK_OPTS_TARGET_DEFAULT` - 编译器默认目标（NEON/SSE2/portable）
- `SK_OPTS_TARGET_SSSE3` - SSSE3 指令集
- `SK_OPTS_TARGET_AVX` - AVX 指令集
- `SK_OPTS_TARGET_HSW` - Haswell (AVX2+FMA+BMI2+F16C)
- `SK_OPTS_TARGET_LASX` - LoongArch 高级 SIMD

### SkOpts_hsw.cpp / SkOpts_skx.cpp（目标编译单元）
```cpp
// SkOpts_hsw.cpp
#define SK_OPTS_NS hsw
#include "src/opts/SkRasterPipeline_opts.h"

namespace SkOpts {
    void Init_hsw() {
        // 绑定 hsw 命名空间中的函数到全局函数指针
        raster_pipeline_lowp_stride = SK_OPTS_NS::raster_pipeline_lowp_stride();
        raster_pipeline_highp_stride = SK_OPTS_NS::raster_pipeline_highp_stride();
        #define M(st) ops_highp[(int)SkRasterPipelineOp::st] = (StageFn)SK_OPTS_NS::st;
            SK_RASTER_PIPELINE_OPS_ALL(M)
        #undef M
    }
}
```
每个目标编译单元（.cpp 文件）定义特定的命名空间，包含优化头文件使代码在该指令集下编译，然后提供一个 `Init_*()` 函数将该命名空间中的所有函数指针注册到 `SkOpts` 全局表中。

## 依赖关系

### 上游依赖
- `src/base/SkVx.h` - Skia 通用 SIMD 向量库（除 RasterPipeline 外的优化使用）
- `src/core/SkRasterPipeline.h` - 光栅化管线定义
- `src/core/SkOpts.h` - 全局函数指针表声明
- `src/core/SkBitmapProcState.h` - 位图采样状态
- `src/core/SkColorData.h` - 颜色数据处理工具
- `src/core/Sk4px.h` - 4像素打包操作（掩码混合回退路径）
- `include/private/base/SkFeatures.h` - 平台特性检测宏

### 下游消费者
- `src/core/SkOpts.cpp` - 全局函数指针表初始化
- `src/core/SkRasterPipeline.cpp` - 光栅化管线调度
- `src/core/SkBlitter.cpp` - 像素绘制
- `src/core/SkBitmapProcState.cpp` - 位图采样
- `src/core/SkSwizzler.cpp` - 颜色格式转换

## 设计模式分析

### 编译时多态（Compile-Time Polymorphism）
整个模块基于编译时多态设计。同一份源代码通过宏控制在不同指令集下多次编译，每次生成到不同命名空间中。这比传统的运行时虚函数分发高效得多，因为编译器可以充分内联和优化每个特定指令集的代码路径。

### 函数指针表模式（Function Pointer Table / Dispatch Table）
`SkOpts` 命名空间维护了一组全局函数指针，运行时根据 CPU 特性检测结果选择最优实现绑定到这些指针上。这种模式将指令集选择的开销降低到初始化时的一次性操作，之后的每次调用都是直接的函数指针调用。

### 瀑布式分发（Waterfall Dispatch）
`blit_row_s32a_opaque` 展示了瀑布式分发模式：在单个函数内从最宽的 SIMD 宽度开始（AVX2 一次8像素），处理完能处理的部分后回退到较窄的宽度（SSE2 一次4像素），最后用标量处理余数。这种模式避免了函数调用开销，充分利用了不同宽度的向量指令。

### 模板参数化优化（Template-Parameterized Optimization）
`blit_mask_d32_a8_neon<isTranslucent>` 使用模板布尔参数在编译时消除半透明/不透明情况的分支。编译器会为 `true` 和 `false` 两种情况生成完全不同的指令序列，避免运行时分支判断。

### 头文件即编译单元模式（Header-as-Translation-Unit）
`SkSwizzler_opts.inc` 使用 `.inc` 扩展名，明确表示它不是普通头文件，而是需要在多个编译单元中以不同配置被包含的代码片段。这种模式是多目标编译系统的基础。

### 安全优化模式（Security-Aware Optimization）
多处代码特别注意避免基于像素数据的条件分支，以防止时序攻击（timing attacks）。例如 `SkSwizzler_opts.inc` 中使用 SSE 的 `_mm_and_ps` 配合比较结果实现无分支的条件选择，`SkBlitRow_opts.h` 中特别注释提醒不要使用 `vptest` 或 `pmovmskb` 进行数据相关的分支。

## 数据流

```
1. 启动初始化
   SkOpts::Init()
   检测 CPU 特性 (SkCpu::Supports)
   绑定最优实现到函数指针表
        |
        v
2. 渲染请求
   SkCanvas 操作 --> SkBlitter / SkRasterPipeline
        |
        v
3. 函数分发
   通过 SkOpts 函数指针调用对应的优化实现
   例如: SkOpts::blit_row_s32a_opaque --> hsw::blit_row_s32a_opaque
        |
        v
4. SIMD 执行
   +-- 光栅化管线路径 --------------------------------+
   |  SkRasterPipeline -> start_pipeline              |
   |  -> 阶段函数尾调用链                              |
   |  每个阶段处理 N 个像素 (N = SIMD 宽度)            |
   |  highp (float) 或 lowp (uint16) 精度              |
   +--------------------------------------------------+
   |
   +-- 位图采样路径 ----------------------------------+
   |  SkBitmapProcState -> S32_alpha_D32_filter_DX    |
   |  对每个输出像素：                                 |
   |    解码坐标 -> 加载 2x2 源像素 -> 双线性插值       |
   +--------------------------------------------------+
   |
   +-- 像素混合路径 ----------------------------------+
   |  SkBlitter -> blit_row_s32a_opaque               |
   |  AVX2: 8像素/次 -> SSE2: 4像素/次 -> 标量: 1像素  |
   +--------------------------------------------------+
   |
   +-- 内存填充路径 ----------------------------------+
      memset16/32/64                                   |
      AVX: 32字节/次 -> SSE: 16字节/次 -> 标量: 1元素   |
   +--------------------------------------------------+
```

## 相关文档与参考

- `src/core/SkOpts.h` - 全局优化函数指针表声明
- `src/core/SkOpts.cpp` - 函数指针初始化和 CPU 特性检测
- `src/core/SkRasterPipeline.h` - 光栅化管线公共接口
- `src/base/SkVx.h` - Skia 通用 SIMD 向量封装库
- `include/private/base/SkFeatures.h` - 平台特性检测宏（`SK_CPU_SSE_LEVEL` 等）
- Intel Intrinsics Guide - SSE/AVX 指令集参考
- ARM NEON Intrinsics Reference - ARM NEON 指令集参考
- [Skia SkRasterPipeline 设计文档](https://skia.org/docs/dev/design/) - 光栅化管线架构
- Valve "Improved Alpha-Tested Magnification" (SIGGRAPH 2007) - SDF 文本中引用的距离场技术
- LoongArch SIMD 扩展指令手册 - LSX/LASX 指令集参考
