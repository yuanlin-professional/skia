# SkSwizzler_opts_hsw

> 源文件: src/core/SkSwizzler_opts_hsw.cpp

## 概述

`SkSwizzler_opts_hsw.cpp` 是 Skia 图形库中针对 Intel Haswell (HSW) 微架构优化的像素格式转换实现文件。Haswell 是 Intel 在 2013 年推出的处理器架构,引入了 AVX2 指令集扩展,支持 256 位 SIMD 运算。该文件通过 AVX2 指令实现高性能的像素通道交换、预乘/反预乘 alpha、颜色格式转换等操作,相比 SSSE3 实现可以一次处理更多像素(8 个 vs 4 个)。

## 架构位置

该文件是像素处理优化层的一个平台特定实现,在运行时动态选择使用。

```
优化实现架构:
  SkSwizzle 公共 API
    ↓
  SkSwizzlePriv (函数指针定义)
    ↓
  SkSwizzler_opts.cpp (运行时选择)
    ↓
  ┌─────────────────┬──────────────────┬──────────────────┐
  │ 默认实现         │ SSSE3 优化       │ HSW 优化 ← 本文件 │
  └─────────────────┴──────────────────┴──────────────────┘
```

## 主要类与结构体

### 命名空间结构

```cpp
namespace SkOpts {
    void Init_Swizzler_hsw();
}
```

**初始化函数:**
在检测到 CPU 支持 AVX2 时调用,将全局函数指针设置为 HSW 优化版本。

### 实现的函数指针

该文件通过包含 `src/opts/SkSwizzler_opts.inc` 实现以下函数(在 `hsw` 命名空间中):

| 函数名 | 类型 | 功能 |
|-------|------|------|
| `hsw::RGBA_to_BGRA` | `Swizzle_8888_u32` | RGBA ↔ BGRA 交换 |
| `hsw::RGBA_to_rgbA` | `Swizzle_8888_u32` | 预乘 alpha |
| `hsw::RGBA_to_bgrA` | `Swizzle_8888_u32` | 交换并预乘 |
| `hsw::gray_to_RGB1` | `Swizzle_8888_u8` | 灰度扩展 |
| `hsw::grayA_to_RGBA` | `Swizzle_8888_u8` | 灰度+alpha 扩展 |
| `hsw::grayA_to_rgbA` | `Swizzle_8888_u8` | 灰度扩展并预乘 |
| `hsw::inverted_CMYK_to_RGB1` | `Swizzle_8888_u32` | CMYK 转 RGB |
| `hsw::inverted_CMYK_to_BGR1` | `Swizzle_8888_u32` | CMYK 转 BGR |

## 公共 API 函数

### Init_Swizzler_hsw

```cpp
void Init_Swizzler_hsw() {
    RGBA_to_BGRA          = hsw::RGBA_to_BGRA;
    RGBA_to_rgbA          = hsw::RGBA_to_rgbA;
    RGBA_to_bgrA          = hsw::RGBA_to_bgrA;
    gray_to_RGB1          = hsw::gray_to_RGB1;
    grayA_to_RGBA         = hsw::grayA_to_RGBA;
    grayA_to_rgbA         = hsw::grayA_to_rgbA;
    inverted_CMYK_to_RGB1 = hsw::inverted_CMYK_to_RGB1;
    inverted_CMYK_to_BGR1 = hsw::inverted_CMYK_to_BGR1;
}
```

**功能:**
将 `SkOpts` 命名空间中的全局函数指针替换为 HSW 优化版本。

**调用时机:**
在 `SkOpts::Init_Swizzler()` 中,当检测到 CPU 支持 AVX2 时调用。

## 内部实现细节

### 条件编译控制

```cpp
#if defined(SK_CPU_X86) && \
    !defined(SK_ENABLE_OPTIMIZE_SIZE) && \
    SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_AVX2
```

**编译条件:**
1. **SK_CPU_X86**: 必须是 x86/x64 平台
2. **!SK_ENABLE_OPTIMIZE_SIZE**: 未启用代码体积优化模式
3. **SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_AVX2**: 基准编译未包含 AVX2

**为何需要第三个条件?**
- 如果基准编译已经是 AVX2,则无需单独编译此文件
- 避免代码重复和二进制膨胀
- 确保只在需要时才包含多个版本

### 编译目标设置

```cpp
#define SK_OPTS_TARGET SK_OPTS_TARGET_HSW
#include "src/opts/SkOpts_SetTarget.h"

#include "src/opts/SkSwizzler_opts.inc"

#include "src/opts/SkOpts_RestoreTarget.h"
```

**编译流程:**
1. **设置目标**: 定义 `SK_OPTS_TARGET` 为 HSW
2. **激活编译标志**: `SkOpts_SetTarget.h` 添加 AVX2 编译器标志(如 `-mavx2`)
3. **包含实现**: `SkSwizzler_opts.inc` 包含实际的 SIMD 代码
4. **恢复设置**: `SkOpts_RestoreTarget.h` 恢复默认编译标志

### AVX2 优化特性

**指令集优势:**
- **256 位向量**: 一次处理 8 个 32 位像素(vs SSSE3 的 4 个)
- **更多寄存器**: 16 个 YMM 寄存器
- **融合乘加**: FMA (Fused Multiply-Add) 指令
- **改进的 shuffle**: 更灵活的通道重排

**性能提升:**
相比 SSSE3 实现,理论加速比为 **2x**(实际约 1.5-1.8x,受内存带宽限制)。

### 典型实现模式(伪代码)

```cpp
void RGBA_to_BGRA(uint32_t* dst, const uint32_t* src, int count) {
    // 处理 8 个像素为一组
    while (count >= 8) {
        __m256i pixels = _mm256_loadu_si256((__m256i*)src);
        __m256i swapped = _mm256_shuffle_epi8(pixels, swap_rb_mask);
        _mm256_storeu_si256((__m256i*)dst, swapped);
        src += 8;
        dst += 8;
        count -= 8;
    }
    // 处理剩余像素(小于 8 个)
    // ...
}
```

### 对齐与非对齐访问

AVX2 实现使用 `_mm256_loadu_si256` 和 `_mm256_storeu_si256`:
- **u 表示 unaligned**: 支持非对齐内存访问
- **性能影响**: 非对齐访问略慢,但避免了对齐要求
- **兼容性**: 更广泛适用,不要求特殊内存分配

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkFeatures.h` | CPU 特性宏定义 |
| `SkOptsTargets.h` | 优化目标定义 |
| `SkSwizzlePriv.h` | 函数指针声明 |
| `SkOpts_SetTarget.h` | 编译器标志控制 |
| `SkSwizzler_opts.inc` | 实际 SIMD 实现 |
| `SkOpts_RestoreTarget.h` | 恢复编译器设置 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `SkSwizzler_opts.cpp` | 运行时调用 `Init_Swizzler_hsw()` |
| CPU 特性检测 | 决定是否调用此实现 |

## 设计模式与设计决策

### 设计模式

1. **函数指针策略模式**: 运行时选择最优实现
2. **条件编译模式**: 根据平台和配置选择性编译
3. **命名空间隔离**: 避免不同优化版本的符号冲突

### 设计决策

**1. 为何单独编译 HSW 版本?**
- **二进制兼容性**: 同一个可执行文件可以在不支持 AVX2 的 CPU 上运行
- **渐进式优化**: 根据目标 CPU 能力自动选择最佳实现
- **代码维护**: 核心逻辑在 `.inc` 文件中共享,只需编译多次

**2. 为何需要 SK_ENABLE_OPTIMIZE_SIZE 检查?**
- 代码体积优化模式下,跳过多个版本的编译
- 减少二进制大小,适用于嵌入式或移动设备
- 权衡性能和大小

**3. 为何使用 .inc 文件?**
- 同一份代码编译为不同指令集版本
- 避免代码重复
- 简化维护:修改一处,所有版本受益

**4. 为何不总是使用 AVX2?**
- 旧 CPU 不支持(如 Ivy Bridge 之前的 Intel CPU)
- 需要运行时检测和动态选择
- 确保在所有 x86 平台上都能运行

**5. 为何包含 RGB_to_RGB1?**
- HSW 版本注释显示**不包含** `RGB_to_RGB1` 和 `RGB_to_BGR1`
- 这两个函数可能不适合 AVX2 优化(性能提升不明显)
- 保持使用 SSSE3 版本或默认版本

## 性能考量

### 性能优势

| 特性 | SSSE3 | HSW (AVX2) | 提升 |
|------|-------|------------|------|
| 向量宽度 | 128 位 | 256 位 | 2x |
| 每次处理像素 | 4 个 | 8 个 | 2x |
| 实际吞吐量 | ~4 GB/s | ~8 GB/s | ~2x |

### 性能瓶颈

1. **内存带宽**: 大部分场景受限于内存带宽,而非计算能力
2. **L1/L2 缓存**: 小数据集可以达到峰值性能
3. **非对齐访问**: 有轻微性能损失(约 5-10%)

### 适用场景

**最佳场景:**
- 大图像处理(超过 L3 缓存)
- 连续内存访问
- 2013 年后的 Intel CPU(Haswell+)

**不适用场景:**
- 旧 CPU(检测会自动回退)
- 优化代码体积的构建
- 非常小的像素块(< 32 像素,初始化开销大)

### 测试与验证

**如何验证是否使用了 HSW 版本?**
1. 运行时日志(如果启用)
2. 性能基准测试对比
3. 调试器查看函数指针地址
4. CPU 计数器(查看 AVX2 指令使用)

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkSwizzlePriv.h` | 函数指针声明 |
| `src/core/SkSwizzler_opts.cpp` | 初始化和选择逻辑 |
| `src/core/SkSwizzler_opts_ssse3.cpp` | SSSE3 优化版本(前代) |
| `src/core/SkSwizzler_opts_lasx.cpp` | LoongArch 优化版本(其他架构) |
| `src/opts/SkSwizzler_opts.inc` | 共享的 SIMD 实现代码 |
| `src/opts/SkOpts_SetTarget.h` | 编译器标志设置 |
| `src/opts/SkOpts_RestoreTarget.h` | 编译器标志恢复 |
| `src/core/SkCpu.h` | CPU 特性检测 |
| `src/core/SkOptsTargets.h` | 优化目标宏定义 |
| `include/private/base/SkFeatures.h` | CPU 架构宏 |

## 技术细节

### Haswell 微架构特性

**引入时间:** 2013 年

**关键改进:**
- AVX2 指令集(256 位整数 SIMD)
- FMA3(融合乘加)
- BMI1/BMI2(位操作指令)
- 改进的乱序执行

**支持的处理器系列:**
- Intel Core 第 4 代(Haswell)
- Intel Core 第 5 代(Broadwell)
- Intel Core 第 6 代+(Skylake 及后续)
- AMD Zen 1 及后续(也支持 AVX2)

### 编译器支持

**GCC/Clang:**
```bash
-mavx2  # 启用 AVX2 指令
```

**MSVC:**
```bash
/arch:AVX2  # 启用 AVX2 指令
```

### 运行时检测

```cpp
if (SkCpu::Supports(SkCpu::HSW)) {
    Init_Swizzler_hsw();
}
```

检测方法:
- CPUID 指令查询 AVX2 支持
- 检测 OS 是否保存 YMM 寄存器状态
- 两者都满足才启用
