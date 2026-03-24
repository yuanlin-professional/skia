# SkSwizzler_opts_lasx

> 源文件: src/core/SkSwizzler_opts_lasx.cpp

## 概述

`SkSwizzler_opts_lasx.cpp` 是 Skia 图形库中针对 LoongArch 架构的 LASX (Loongson Advanced SIMD eXtension) 指令集优化的像素格式转换实现文件。LoongArch 是中国龙芯处理器使用的自主指令集架构,LASX 是其 256 位 SIMD 扩展指令集,功能类似于 Intel 的 AVX2。该文件为 LoongArch 平台提供高性能的像素通道交换、颜色格式转换等操作,一次可以处理 8 个 32 位像素。

## 架构位置

该文件是像素处理优化层的平台特定实现,为 LoongArch 架构提供优化支持。

```
优化实现架构:
  SkSwizzle 公共 API
    ↓
  SkSwizzlePriv (函数指针定义)
    ↓
  SkSwizzler_opts.cpp (运行时选择)
    ↓
  ┌────────────┬────────────┬────────────────┐
  │ x86 优化    │ ARM 优化   │ LoongArch ← 本文件 │
  │ (SSSE3/AVX2)│ (NEON)     │ (LASX)         │
  └────────────┴────────────┴────────────────┘
```

## 主要类与结构体

### 命名空间结构

```cpp
namespace SkOpts {
    void Init_Swizzler_lasx();
}
```

**初始化函数:**
在检测到 LoongArch CPU 支持 LASX 指令集时调用,将全局函数指针设置为 LASX 优化版本。

### 实现的函数指针

该文件通过包含 `src/opts/SkSwizzler_opts.inc` 实现以下函数(在 `lasx` 命名空间中):

| 函数名 | 类型 | 功能 |
|-------|------|------|
| `lasx::RGBA_to_BGRA` | `Swizzle_8888_u32` | RGBA ↔ BGRA 交换 |
| `lasx::RGBA_to_rgbA` | `Swizzle_8888_u32` | 预乘 alpha |
| `lasx::RGBA_to_bgrA` | `Swizzle_8888_u32` | 交换并预乘 |
| `lasx::gray_to_RGB1` | `Swizzle_8888_u8` | 灰度扩展 |
| `lasx::grayA_to_RGBA` | `Swizzle_8888_u8` | 灰度+alpha 扩展 |
| `lasx::grayA_to_rgbA` | `Swizzle_8888_u8` | 灰度扩展并预乘 |
| `lasx::inverted_CMYK_to_RGB1` | `Swizzle_8888_u32` | CMYK 转 RGB |
| `lasx::inverted_CMYK_to_BGR1` | `Swizzle_8888_u32` | CMYK 转 BGR |

**注意:** 与 HSW (AVX2) 版本类似,LASX 版本不包含 `RGB_to_RGB1` 和 `RGB_to_BGR1` 函数。

## 公共 API 函数

### Init_Swizzler_lasx

```cpp
void Init_Swizzler_lasx() {
    RGBA_to_BGRA          = lasx::RGBA_to_BGRA;
    RGBA_to_rgbA          = lasx::RGBA_to_rgbA;
    RGBA_to_bgrA          = lasx::RGBA_to_bgrA;
    gray_to_RGB1          = lasx::gray_to_RGB1;
    grayA_to_RGBA         = lasx::grayA_to_RGBA;
    grayA_to_rgbA         = lasx::grayA_to_rgbA;
    inverted_CMYK_to_RGB1 = lasx::inverted_CMYK_to_RGB1;
    inverted_CMYK_to_BGR1 = lasx::inverted_CMYK_to_BGR1;
}
```

**功能:**
将 `SkOpts` 命名空间中的全局函数指针替换为 LASX 优化版本。

**调用时机:**
在 `SkOpts::Init_Swizzler()` 中,当检测到 CPU 支持 LoongArch LASX 扩展时调用。

## 内部实现细节

### 条件编译控制

```cpp
#if defined(SK_CPU_LOONGARCH) && !defined(SK_ENABLE_OPTIMIZE_SIZE)
```

**编译条件:**
1. **SK_CPU_LOONGARCH**: 必须是 LoongArch 平台
2. **!SK_ENABLE_OPTIMIZE_SIZE**: 未启用代码体积优化模式

**编译逻辑:**
- 仅在 LoongArch 平台编译
- 代码体积优化模式下跳过(减少二进制大小)
- 没有基准指令级别检查(与 x86 不同)

### 编译目标设置

```cpp
#define SK_OPTS_TARGET SK_OPTS_TARGET_LASX
#include "src/opts/SkOpts_SetTarget.h"

#include "src/opts/SkSwizzler_opts.inc"

#include "src/opts/SkOpts_RestoreTarget.h"
```

**编译流程:**
1. **设置目标**: 定义 `SK_OPTS_TARGET` 为 LASX
2. **激活编译标志**: 添加 LASX 相关编译器标志
3. **包含实现**: 编译共享的 SIMD 实现代码
4. **恢复设置**: 恢复默认编译标志

### LASX 指令集特性

**LASX 概述:**
- **向量宽度**: 256 位(类似 AVX2)
- **每次处理**: 8 个 32 位像素或 32 个字节
- **寄存器**: 32 个 256 位向量寄存器($xr0-$xr31)
- **指令集**: 类似 AVX2 的功能,但语法和编码不同

**关键指令类型:**
- **字节重排**: 类似 `PSHUFB` 的功能
- **向量算术**: 加、减、乘等
- **逻辑运算**: AND、OR、XOR 等
- **加载/存储**: 对齐和非对齐访问

### IWYU Pragma

```cpp
#include "include/private/base/SkFeatures.h" // IWYU pragma: keep
#include "src/core/SkOptsTargets.h" // IWYU pragma: keep
#include "src/core/SkSwizzlePriv.h" // IWYU pragma: keep
```

**IWYU (Include What You Use):**
- `pragma: keep` 告诉 IWYU 工具保留这些包含
- 即使工具认为不直接使用,这些头文件对宏定义是必需的
- 确保条件编译正确工作

### 典型实现模式(概念性)

```cpp
// 使用 LoongArch intrinsics (概念性示例)
void RGBA_to_BGRA(uint32_t* dst, const uint32_t* src, int count) {
    // LASX 向量类型
    __m256i swap_rb_mask = /* 创建交换 R/B 的掩码 */;

    while (count >= 8) {
        __m256i pixels = __lasx_xvld(src, 0);  // 加载 8 个像素
        __m256i swapped = __lasx_xvshuf_b(pixels, pixels, swap_rb_mask);
        __lasx_xvst(swapped, dst, 0);  // 存储 8 个像素
        src += 8;
        dst += 8;
        count -= 8;
    }
    // 处理剩余像素
}
```

**注意:** 实际实现在 `SkSwizzler_opts.inc` 中,通过抽象层适配不同平台的 intrinsics。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkFeatures.h` | CPU 架构宏定义 |
| `SkOptsTargets.h` | 优化目标定义 |
| `SkSwizzlePriv.h` | 函数指针声明 |
| `SkOpts_SetTarget.h` | 编译器标志控制 |
| `SkSwizzler_opts.inc` | 实际 SIMD 实现 |
| `SkOpts_RestoreTarget.h` | 恢复编译器设置 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `SkSwizzler_opts.cpp` | 运行时调用 `Init_Swizzler_lasx()` |
| CPU 特性检测 | 决定是否调用此实现 |

## 设计模式与设计决策

### 设计模式

1. **平台抽象**: 通过共享 `.inc` 文件支持多平台
2. **运行时选择**: 动态检测 CPU 能力并选择实现
3. **条件编译**: 仅在目标平台编译

### 设计决策

**1. 为何支持 LoongArch?**
- **市场需求**: 中国市场对国产处理器的支持
- **性能需求**: 提供与 Intel/AMD 相当的性能
- **架构多样性**: 支持更多硬件平台

**2. 为何对标 AVX2 功能?**
- LASX 设计上类似 AVX2(256 位宽)
- 提供相似的性能特征
- 简化代码移植和维护

**3. 为何不包含 RGB_to_RGB1?**
- 与 AVX2 版本保持一致
- 可能性能提升不明显
- 使用 LSX(128 位)版本或默认版本更合适

**4. 为何没有 LSX 版本?**
- LSX(128 位,类似 SSE)可能包含在基准编译中
- LASX 作为额外优化层
- 简化优化层级(类似 x86 跳过 SSE 直接 SSSE3)

**5. 为何使用 IWYU pragma?**
- 自动化工具可能错误删除必要的头文件
- 宏依赖不总是被工具检测到
- 确保构建系统正确性

## 性能考量

### 性能特点

| 特性 | LSX (128位) | LASX (256位) | 提升 |
|------|------------|-------------|------|
| 向量宽度 | 128 位 | 256 位 | 2x |
| 每次处理像素 | 4 个 | 8 个 | 2x |
| 理论吞吐量 | ~4 GB/s | ~8 GB/s | 2x |

### LoongArch 处理器特性

**龙芯 3A5000/6000:**
- 支持 LASX 指令集
- 4-16 核心配置
- 主频 2.5-3.0 GHz
- 与 Intel Skylake 性能相当

### 性能瓶颈

1. **内存带宽**: 与 x86 类似,通常受限于内存
2. **编译器成熟度**: LoongArch 工具链较新,优化可能不如 x86
3. **微架构差异**: 不同批次的龙芯处理器性能可能不同

### 适用场景

**最佳场景:**
- 龙芯 3A5000 及后续处理器
- 中国市场的桌面和服务器应用
- 需要国产化软件栈的项目

**限制:**
- 市场占有率较低(主要在中国)
- 生态系统仍在发展中
- 第三方库支持可能有限

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkSwizzlePriv.h` | 函数指针声明 |
| `src/core/SkSwizzler_opts.cpp` | 初始化和选择逻辑 |
| `src/core/SkSwizzler_opts_ssse3.cpp` | x86 SSSE3 优化 |
| `src/core/SkSwizzler_opts_hsw.cpp` | x86 AVX2 优化 |
| `src/opts/SkSwizzler_opts.inc` | 共享的 SIMD 实现代码 |
| `src/opts/SkOpts_SetTarget.h` | 编译器标志设置 |
| `src/opts/SkOpts_RestoreTarget.h` | 编译器标志恢复 |
| `src/core/SkCpu.h` | CPU 特性检测 |
| `src/core/SkOptsTargets.h` | 优化目标宏定义 |

## 技术细节

### LoongArch 架构

**架构特点:**
- **位数**: 64 位(LoongArch64)
- **字节序**: 小端(Little-Endian)
- **指令格式**: 固定长度 32 位指令
- **寄存器**: 32 个通用寄存器,32 个浮点寄存器,32 个向量寄存器

**SIMD 层级:**
1. **LSX**: 128 位向量扩展(类似 SSE)
2. **LASX**: 256 位向量扩展(类似 AVX)

### 编译器支持

**GCC:**
```bash
-mlasx  # 启用 LASX 指令集
```

**LLVM/Clang:**
```bash
-march=loongarch64 -mlasx
```

### 运行时检测

```cpp
#if defined(SK_CPU_LOONGARCH)
    #if SK_CPU_LSX_LEVEL < SK_CPU_LSX_LEVEL_LASX
        if (SkCpu::Supports(SkCpu::LOONGARCH_ASX)) {
            Init_Swizzler_lasx();
        }
    #endif
#endif
```

**检测方法:**
- 读取 CPU 配置寄存器
- 检查 LASX 功能位
- 验证操作系统支持

### 与 AVX2 的对比

| 特性 | AVX2 (Intel) | LASX (LoongArch) |
|------|-------------|------------------|
| 向量宽度 | 256 位 | 256 位 |
| 寄存器数量 | 16 (YMM) | 32 (XR) |
| 指令编码 | x86 变长 | LoongArch 定长 |
| 成熟度 | 2013+, 非常成熟 | 2020+, 快速发展 |
| 生态系统 | 广泛支持 | 主要在中国 |

### 跨平台抽象

`SkSwizzler_opts.inc` 使用预处理器和 Skia 的向量抽象层(`SkVx`)来支持多平台:
```cpp
#if defined(__AVX2__)
    // 使用 AVX2 intrinsics
#elif defined(__loongarch_sx)
    // 使用 LoongArch intrinsics
#elif defined(__ARM_NEON)
    // 使用 ARM NEON intrinsics
#else
    // 便携式 C++ 实现
#endif
```

## 未来展望

### LoongArch 生态发展

1. **操作系统**: Linux 内核主线支持(5.19+)
2. **编译器**: GCC 12+, LLVM 16+ 官方支持
3. **应用软件**: 主流软件逐步适配
4. **硬件**: 新一代处理器持续发布

### Skia 对 LoongArch 的支持

- **当前**: 基础 LASX 优化
- **未来可能**: 更多特定优化,更完善的测试
- **挑战**: 测试设备可用性,社区贡献

### 性能优化方向

1. **微架构调优**: 针对具体龙芯处理器型号优化
2. **编译器优化**: 利用更新的工具链特性
3. **指令选择**: 探索 LASX 独特的指令优势
