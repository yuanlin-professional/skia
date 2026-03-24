# SkSwizzler_opts_ssse3

> 源文件: src/core/SkSwizzler_opts_ssse3.cpp

## 概述

`SkSwizzler_opts_ssse3.cpp` 是 Skia 图形库中针对 Intel SSSE3 (Supplemental SSE3) 指令集优化的像素格式转换实现文件。SSSE3 是 Intel 在 2006 年引入的 SSE 扩展指令集,相比 SSE3 增加了更强大的字节重排和符号操作指令。该文件实现了使用 128 位 SIMD 指令的像素通道交换、预乘 alpha、颜色格式转换等操作,可以一次处理 4 个 32 位像素,相比标量代码有显著性能提升。

## 架构位置

该文件是像素处理优化层的平台特定实现,为较旧但仍广泛使用的 x86 处理器提供优化。

```
优化实现架构:
  SkSwizzle 公共 API
    ↓
  SkSwizzlePriv (函数指针定义)
    ↓
  SkSwizzler_opts.cpp (运行时选择)
    ↓
  ┌────────────┬─────────────────┬──────────────┐
  │ 默认实现    │ SSSE3 ← 本文件  │ HSW (AVX2)   │
  └────────────┴─────────────────┴──────────────┘
```

## 主要类与结构体

### 命名空间结构

```cpp
namespace SkOpts {
    void Init_Swizzler_ssse3();
}
```

**初始化函数:**
在检测到 CPU 支持 SSSE3 但不支持 AVX2 时调用,将全局函数指针设置为 SSSE3 优化版本。

### 实现的函数指针

该文件通过包含 `src/opts/SkSwizzler_opts.inc` 实现以下函数(在 `ssse3` 命名空间中):

| 函数名 | 类型 | 功能 |
|-------|------|------|
| `ssse3::RGBA_to_BGRA` | `Swizzle_8888_u32` | RGBA ↔ BGRA 交换 |
| `ssse3::RGBA_to_rgbA` | `Swizzle_8888_u32` | 预乘 alpha |
| `ssse3::RGBA_to_bgrA` | `Swizzle_8888_u32` | 交换并预乘 |
| `ssse3::RGB_to_RGB1` | `Swizzle_8888_u8` | RGB → RGBA (插入不透明 alpha) |
| `ssse3::RGB_to_BGR1` | `Swizzle_8888_u8` | RGB → BGRA |
| `ssse3::gray_to_RGB1` | `Swizzle_8888_u8` | 灰度扩展 |
| `ssse3::grayA_to_RGBA` | `Swizzle_8888_u8` | 灰度+alpha 扩展 |
| `ssse3::grayA_to_rgbA` | `Swizzle_8888_u8` | 灰度扩展并预乘 |
| `ssse3::inverted_CMYK_to_RGB1` | `Swizzle_8888_u32` | CMYK 转 RGB |
| `ssse3::inverted_CMYK_to_BGR1` | `Swizzle_8888_u32` | CMYK 转 BGR |

**注意:** SSSE3 版本包含 `RGB_to_RGB1` 和 `RGB_to_BGR1`,而 HSW 版本不包含这两个函数。

## 公共 API 函数

### Init_Swizzler_ssse3

```cpp
void Init_Swizzler_ssse3() {
    RGBA_to_BGRA          = ssse3::RGBA_to_BGRA;
    RGBA_to_rgbA          = ssse3::RGBA_to_rgbA;
    RGBA_to_bgrA          = ssse3::RGBA_to_bgrA;
    RGB_to_RGB1           = ssse3::RGB_to_RGB1;
    RGB_to_BGR1           = ssse3::RGB_to_BGR1;
    gray_to_RGB1          = ssse3::gray_to_RGB1;
    grayA_to_RGBA         = ssse3::grayA_to_RGBA;
    grayA_to_rgbA         = ssse3::grayA_to_rgbA;
    inverted_CMYK_to_RGB1 = ssse3::inverted_CMYK_to_RGB1;
    inverted_CMYK_to_BGR1 = ssse3::inverted_CMYK_to_BGR1;
}
```

**功能:**
将 `SkOpts` 命名空间中的全局函数指针替换为 SSSE3 优化版本。

**调用时机:**
在 `SkOpts::Init_Swizzler()` 中,当检测到 CPU 支持 SSSE3 时调用。如果后续检测到支持 AVX2,会被 HSW 版本覆盖。

## 内部实现细节

### 条件编译控制

```cpp
#if defined(SK_CPU_X86) && \
    !defined(SK_ENABLE_OPTIMIZE_SIZE) && \
    SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_SSSE3
```

**编译条件:**
1. **SK_CPU_X86**: 必须是 x86/x64 平台
2. **!SK_ENABLE_OPTIMIZE_SIZE**: 未启用代码体积优化模式
3. **SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_SSSE3**: 基准编译未包含 SSSE3

**编译逻辑:**
- 如果基准编译目标已经是 SSSE3 或更高,则此文件不编译
- 确保不同指令集版本不会冲突
- 最小化二进制大小膨胀

### 编译目标设置

```cpp
#define SK_OPTS_TARGET SK_OPTS_TARGET_SSSE3
#include "src/opts/SkOpts_SetTarget.h"

#include "src/opts/SkSwizzler_opts.inc"

#include "src/opts/SkOpts_RestoreTarget.h"
```

**编译流程:**
1. **设置目标**: 定义 `SK_OPTS_TARGET` 为 SSSE3
2. **激活编译标志**: 添加 `-mssse3` 或等效编译器标志
3. **包含实现**: 编译 SIMD 优化代码
4. **恢复设置**: 恢复默认编译标志,避免影响其他文件

### SSSE3 核心指令

**关键指令:**
- **_mm_shuffle_epi8**: 根据掩码重排字节(PSHUFB)
- **_mm_maddubs_epi16**: 字节乘法并累加(PMADDUBSW)
- **_mm_sign_epi8/16/32**: 符号操作指令

**PSHUFB 的重要性:**
`_mm_shuffle_epi8` 是 SSSE3 最强大的指令之一,可以任意重排 16 个字节:
```cpp
// 交换 R 和 B 通道
__m128i shuffle_mask = _mm_setr_epi8(
    2,1,0,3,  // 第一个像素: B,G,R,A
    6,5,4,7,  // 第二个像素
    10,9,8,11,  // 第三个像素
    14,13,12,15  // 第四个像素
);
__m128i swapped = _mm_shuffle_epi8(pixels, shuffle_mask);
```

### 典型实现模式(伪代码)

```cpp
void RGBA_to_BGRA(uint32_t* dst, const uint32_t* src, int count) {
    // 创建交换 R/B 的掩码
    const __m128i swap_rb = _mm_setr_epi8(
        2,1,0,3, 6,5,4,7, 10,9,8,11, 14,13,12,15
    );

    // 每次处理 4 个像素
    while (count >= 4) {
        __m128i pixels = _mm_loadu_si128((__m128i*)src);
        __m128i swapped = _mm_shuffle_epi8(pixels, swap_rb);
        _mm_storeu_si128((__m128i*)dst, swapped);
        src += 4;
        dst += 4;
        count -= 4;
    }

    // 处理剩余像素
    while (count-- > 0) {
        uint32_t px = *src++;
        *dst++ = (px & 0xFF00FF00) |  // 保持 G 和 A
                 ((px & 0xFF) << 16) |  // R → B
                 ((px >> 16) & 0xFF);   // B → R
    }
}
```

### RGB_to_RGB1 的特殊性

这个函数将 24 位 RGB 字节流转换为 32 位 RGBA:
```
输入:  R0 G0 B0 | R1 G1 B1 | R2 G2 B2 | R3 G3 B3
输出:  R0 G0 B0 FF | R1 G1 B1 FF | R2 G2 B2 FF | R3 G3 B3 FF
```

SSSE3 的 `PSHUFB` 可以高效实现这个转换(包括插入 0xFF 作为 alpha)。

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
| `SkSwizzler_opts.cpp` | 运行时调用 `Init_Swizzler_ssse3()` |
| CPU 特性检测 | 决定是否调用此实现 |

## 设计模式与设计决策

### 设计模式

1. **分层优化策略**: SSSE3 作为中间优化层
2. **条件编译**: 仅在需要时编译
3. **命名空间隔离**: 避免符号冲突

### 设计决策

**1. 为何需要 SSSE3 版本?**
- **广泛兼容性**: 2006 年后的绝大多数 x86 CPU 都支持
- **性能提升**: 相比标量代码有 2-4 倍加速
- **降级路径**: 在不支持 AVX2 的 CPU 上提供优化

**2. 为何包含 RGB_to_RGB1?**
- SSSE3 的 `PSHUFB` 指令特别适合这种字节重排
- AVX2 版本可能不显著优于 SSSE3
- 保留 SSSE3 实现作为最佳选择

**3. 优先级顺序是什么?**
```
初始化顺序:
1. 默认实现(总是有)
2. SSSE3 实现(如果检测到)
3. HSW 实现(如果检测到,覆盖 SSSE3)
```

**4. 为何使用非对齐加载/存储?**
- 像素数据不保证 16 字节对齐
- 非对齐访问在现代 CPU 上性能损失很小
- 提高代码通用性

**5. 为何不使用 SSE2?**
- SSE2 缺少 `PSHUFB` 指令
- 字节重排需要多个指令模拟,性能不佳
- SSSE3 是合理的最低优化要求(已有 18 年历史)

## 性能考量

### 性能对比

| 实现 | 每次处理像素 | 相对性能 | 典型吞吐量 |
|------|-------------|---------|-----------|
| 标量 | 1 | 1x | ~1 GB/s |
| SSSE3 | 4 | 2-4x | ~3 GB/s |
| AVX2 | 8 | 4-8x | ~6 GB/s |

### 性能瓶颈

1. **内存带宽**: 大数据集受限于内存带宽
2. **缓存局部性**: 小数据集可以达到更高吞吐量
3. **循环开销**: 对于极小的数据块(< 16 像素),开销相对较大

### 适用场景

**最佳场景:**
- 2006-2013 年的 Intel CPU(Core 2 到 Ivy Bridge)
- AMD 旧处理器(Bulldozer 之前)
- 需要广泛兼容性的部署

**不适用场景:**
- 非常旧的 CPU(Pentium 4 等,回退到默认实现)
- 新 CPU 会自动升级到 AVX2 版本

### SSSE3 支持的处理器

**Intel:**
- Core 2 系列(2006+)
- Core i 第 1-3 代(Nehalem, Sandy Bridge, Ivy Bridge)
- Atom 系列(部分型号)

**AMD:**
- Bobcat 架构(2011+)
- Bulldozer 及后续

**不支持的 CPU:**
- Pentium 4 及更早
- AMD K8 及更早
- Atom Z5xx 系列(某些低功耗型号)

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkSwizzlePriv.h` | 函数指针声明 |
| `src/core/SkSwizzler_opts.cpp` | 初始化和选择逻辑 |
| `src/core/SkSwizzler_opts_hsw.cpp` | AVX2 优化版本(后继) |
| `src/core/SkSwizzler_opts_lasx.cpp` | LoongArch 优化版本 |
| `src/opts/SkSwizzler_opts.inc` | 共享的 SIMD 实现代码 |
| `src/opts/SkOpts_SetTarget.h` | 编译器标志设置 |
| `src/opts/SkOpts_RestoreTarget.h` | 编译器标志恢复 |
| `src/core/SkCpu.h` | CPU 特性检测 |
| `src/core/SkOptsTargets.h` | 优化目标宏定义 |

## 技术细节

### SSSE3 指令集特性

**引入时间:** 2006 年(Intel Core 2)

**关键新增指令:**
- **PSHUFB**: 字节级别的 shuffle
- **PHADDW/D**: 水平加法
- **PMADDUBSW**: 无符号/有符号字节乘法
- **PSIGN**: 符号操作
- **PALIGNR**: 字节对齐右移

### 编译器支持

**GCC/Clang:**
```bash
-mssse3  # 启用 SSSE3 指令
```

**MSVC:**
```bash
# SSSE3 包含在 /arch:SSE2 之后,默认启用
```

### 运行时检测

```cpp
#if SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_SSSE3
    if (SkCpu::Supports(SkCpu::SSSE3)) {
        Init_Swizzler_ssse3();
    }
#endif
```

检测方法:
- CPUID 指令查询 SSSE3 位(ECX 的第 9 位)
- 确保 OS 支持 SSE 状态保存

### 代码体积

每个优化版本大约增加 **2-4 KB** 代码:
- 默认实现: ~2 KB
- + SSSE3: ~4 KB
- + AVX2: ~4 KB
- **总计**: ~10 KB

对于完整的 Skia 库(数 MB),这是可接受的开销。
