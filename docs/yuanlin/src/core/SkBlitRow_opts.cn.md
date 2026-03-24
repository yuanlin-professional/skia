# SkBlitRow_opts

> 源文件: src/core/SkBlitRow_opts.cpp

## 概述

`SkBlitRow_opts.cpp` 是 Skia 行混合优化系统的初始化和调度中心。该文件定义了两个核心行混合函数的默认实现，并提供运行时初始化机制，根据 CPU 特性选择和加载最优的 SIMD 优化版本。它实现了 Skia 的多平台性能优化策略：一个二进制文件包含多个 CPU 特定的实现，在程序启动时自动检测并选择最佳版本。

## 架构位置

该模块是 Skia CPU 优化基础设施的核心协调者：

```
应用程序启动
    ↓
SkOpts::Init_BlitRow() ← 当前模块
    ↓
CPU 特性检测 (SkCpu::Supports)
    ↓
条件调用平台特定初始化:
    ├── Init_BlitRow_hsw() (x86 AVX2)
    └── Init_BlitRow_lasx() (LoongArch LASX)
    ↓
更新函数指针:
    ├── SkOpts::blit_row_color32
    └── SkOpts::blit_row_s32a_opaque
    ↓
SkBlitRow 使用优化后的函数指针
    ↓
SkBlitter_ARGB32 等模块调用
```

该模块与以下组件协同工作：

- **SkBlitRow.h**: 定义函数指针类型和接口
- **SkCpu**: 提供 CPU 特性检测
- **SkBlitRow_opts_hsw.cpp / lasx.cpp**: 平台特定的优化实现
- **SkBlitRow_opts.h**: 包含实际的 SIMD 向量化代码
- **SkBlitter_ARGB32**: 使用这些优化函数的主要消费者

## 主要类与结构体

该文件不定义类或结构体，仅包含命名空间级别的函数和变量。

## 公共 API 函数

### SkOpts 命名空间中的函数指针

#### blit_row_color32

```cpp
void (*blit_row_color32)(SkPMColor dst[], SkPMColor src, int count);
```

将单个颜色 `src` 复制到目标数组 `dst` 的 `count` 个位置。

**默认实现** (`SK_OPTS_TARGET_DEFAULT::blit_row_color32`):
- 使用平台的基线 SIMD 指令集
- x86: SSE2（128 位，一次 4 像素）
- ARM: NEON（128 位，一次 4 像素）
- LoongArch: LSX（128 位，一次 4 像素）
- 其他: 标量循环

**优化版本:**
- x86 Haswell+: AVX2（256 位，一次 8 像素）
- LoongArch: LASX（256 位，一次 8 像素）

#### blit_row_s32a_opaque

```cpp
void (*blit_row_s32a_opaque)(SkPMColor dst[], const SkPMColor src[],
                             int count, U8CPU alpha);
```

将源像素数组 `src` 混合到目标数组 `dst`，使用全局 alpha 值。假设源像素已经预乘 alpha 且源本身是不透明的。

**混合公式:**
```cpp
dst[i] = src[i] + SkAlphaMulQ(dst[i], 255 - SkGetPackedA32(src[i]))
```

**默认实现:**
- 使用基线 SIMD 指令集进行向量化混合
- 包含预乘 alpha 计算

**优化版本:**
- 使用 AVX2 或 LASX 进行更宽的向量化

### Init_BlitRow

```cpp
void Init_BlitRow();
```

初始化行混合函数指针。在程序启动时自动调用（通过静态变量初始化）。

**执行流程:**

1. **条件编译检查**: 如果定义了 `SK_ENABLE_OPTIMIZE_SIZE`，跳过所有优化，使用默认实现

2. **x86 平台** (`SK_CPU_X86`):
   - 如果编译时 SSE 级别 < AVX2（`SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_AVX2`）
   - 且运行时 CPU 支持 Haswell AVX2（`SkCpu::Supports(SkCpu::HSW)`）
   - 调用 `Init_BlitRow_hsw()` 加载 AVX2 实现

3. **龙芯平台** (`SK_CPU_LOONGARCH`):
   - 如果编译时 LSX 级别 < LASX（`SK_CPU_LSX_LEVEL < SK_CPU_LSX_LEVEL_LASX`）
   - 且运行时 CPU 支持 LASX（`SkCpu::Supports(SkCpu::LOONGARCH_ASX)`）
   - 调用 `Init_BlitRow_lasx()` 加载 LASX 实现

4. **返回 true**: 表示初始化完成

**自动调用机制:**
```cpp
static bool gInitialized = init();
```
静态变量在程序启动时初始化，触发 `init()` 函数执行。

## 内部实现细节

### 默认实现定义

```cpp
#define SK_OPTS_TARGET SK_OPTS_TARGET_DEFAULT
#include "src/opts/SkOpts_SetTarget.h"
#include "src/opts/SkBlitRow_opts.h"
#include "src/opts/SkOpts_RestoreTarget.h"
```

这段代码：
1. 设置编译器目标为默认（基线 SIMD 级别）
2. 包含 `SkBlitRow_opts.h`，其中定义了 `blit_row_color32` 和 `blit_row_s32a_opaque` 的实现
3. 恢复编译器目标设置

包含后，这些函数在 `SK_OPTS_TARGET_DEFAULT` 命名空间中定义（通常展开为空命名空间或基线架构命名空间）。

### 函数指针初始化

```cpp
namespace SkOpts {
    DEFINE_DEFAULT(blit_row_color32);
    DEFINE_DEFAULT(blit_row_s32a_opaque);
    // ...
}
```

`DEFINE_DEFAULT` 宏将默认实现赋值给函数指针。宏定义可能类似：
```cpp
#define DEFINE_DEFAULT(name) \
    decltype(name)* name = SK_OPTS_TARGET_DEFAULT::name;
```

### 外部初始化函数声明

```cpp
void Init_BlitRow_hsw();
void Init_BlitRow_lasx();
```

声明平台特定的初始化函数，这些函数在各自的 `.cpp` 文件中定义。

### 条件编译的平台调度

```cpp
static bool init() {
#if defined(SK_ENABLE_OPTIMIZE_SIZE)
    // 所有 Init_foo 函数在优化大小时省略
#elif defined(SK_CPU_X86)
    #if SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_AVX2
        if (SkCpu::Supports(SkCpu::HSW)) { Init_BlitRow_hsw(); }
    #endif
#elif defined(SK_CPU_LOONGARCH)
    #if SK_CPU_LSX_LEVEL < SK_CPU_LSX_LEVEL_LASX
        if (SkCpu::Supports(SkCpu::LOONGARCH_ASX)) { Init_BlitRow_lasx(); }
    #endif
#endif
    return true;
}
```

**条件逻辑:**

1. **优化大小**: 跳过所有优化，减小二进制大小
2. **已编译 AVX2**: 如果编译器已针对 AVX2，默认实现就是 AVX2，无需运行时切换
3. **运行时检测**: 仅在基线编译但运行时 CPU 支持更高级特性时，才进行函数指针替换

### 静态初始化时机

```cpp
void Init_BlitRow() {
    [[maybe_unused]] static bool gInitialized = init();
}
```

`[[maybe_unused]]` 抑制未使用变量警告。`gInitialized` 的静态初始化在程序启动时执行，确保在任何绘制操作前完成优化函数选择。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkFeatures.h` | 提供平台特性宏 |
| `SkBlitRow.h` | 定义函数指针类型 |
| `SkCpu.h` | 提供 CPU 特性检测 |
| `SkOptsTargets.h` | 定义 CPU 目标宏 |
| `SkOpts_SetTarget.h` | 设置编译器目标 |
| `SkBlitRow_opts.h` | 包含实际的 SIMD 实现 |
| `SkOpts_RestoreTarget.h` | 恢复编译器目标 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SkBlitRow.h` | 使用此处定义的函数指针 |
| `SkBlitter_ARGB32.cpp` | 调用 `SkOpts::blit_row_color32` 等函数 |
| `SkARGB32_Shader_Blitter` | 使用行混合函数混合 shader 输出 |
| `SkOpts.cpp` | 可能调用 `Init_BlitRow()` 作为全局初始化的一部分 |

## 设计模式与设计决策

### 策略模式

函数指针实现了策略模式，允许运行时选择不同的算法实现：
- **策略接口**: 函数指针类型
- **具体策略**: 默认、HSW、LASX 实现
- **上下文**: `SkOpts` 命名空间持有当前策略

### 单例模式（静态初始化）

使用静态变量确保初始化只执行一次：
```cpp
static bool gInitialized = init();
```

### 工厂模式（条件构造）

`init()` 函数根据 CPU 特性选择并"构造"（加载）合适的实现。

### 编译时 + 运行时混合优化

**编译时决策:**
- 条件编译跳过不支持的平台代码
- 如果已针对高级 ISA 编译，跳过运行时检测

**运行时决策:**
- 在基线编译时，检测 CPU 是否支持更高级 ISA
- 动态替换函数指针

这种混合策略平衡了：
- **二进制大小**: 仅包含必要的优化代码
- **性能**: 自动选择最优实现
- **兼容性**: 单个二进制支持多代 CPU

### 最小化开销设计

- **零成本抽象**: 函数指针在热路径中几乎无开销
- **一次性初始化**: 初始化开销分摊到整个程序生命周期
- **条件编译**: 未使用的代码完全不编译

## 性能考量

### 初始化开销

初始化在程序启动时执行一次，开销包括：
- CPU 特性检测（通常几十个 CPU 周期）
- 条件分支判断
- 函数指针赋值

总开销通常在 1 微秒以下，对程序启动时间影响可忽略。

### 运行时函数指针调用

现代 CPU 的分支预测器能高效处理间接跳转：
- **预测准确**: 函数指针在程序生命周期内不变
- **开销**: 通常 1-2 个额外周期（相比直接调用）
- **相对开销**: 处理数百像素时可忽略

### SIMD 优化收益

选择正确的 SIMD 实现带来显著性能提升：

| 平台 | 基线 | 优化 | 理论加速比 | 实际加速比 |
|------|------|------|-----------|-----------|
| x86 | SSE2 (128位) | AVX2 (256位) | 2x | 1.5-1.8x |
| LoongArch | LSX (128位) | LASX (256位) | 2x | 1.5-1.8x |

实际加速比低于理论值的原因：
- 内存带宽限制
- 循环开销
- 尾部标量处理
- 指令延迟

### 缓存友好性

行混合操作天然缓存友好：
- 连续内存访问（像素行）
- 可预测的访问模式
- 利用空间局部性

### 编译器优化

使用 `SkOpts_SetTarget.h` 确保编译器使用正确的 ISA 优化：
- 向量化循环
- 寄存器分配优化
- 指令调度

## 相关文件

| 文件路径 | 关系 |
|---------|------|
| `src/core/SkBlitRow.h` | 定义函数指针接口 |
| `src/core/SkBlitRow_opts_hsw.cpp` | x86 AVX2 优化实现 |
| `src/core/SkBlitRow_opts_lasx.cpp` | LoongArch LASX 优化实现 |
| `src/opts/SkBlitRow_opts.h` | 实际的 SIMD 向量化代码 |
| `src/opts/SkOpts_SetTarget.h` | 编译器目标设置工具 |
| `src/opts/SkOpts_RestoreTarget.h` | 编译器目标恢复工具 |
| `src/core/SkOptsTargets.h` | CPU 目标宏定义 |
| `src/core/SkCpu.h` | CPU 特性检测接口 |
| `src/core/SkCpu.cpp` | CPU 特性检测实现 |
| `include/private/base/SkFeatures.h` | 平台特性宏 |
| `src/core/SkBlitter_ARGB32.cpp` | 主要使用者 |
| `src/core/SkARGB32_Shader_Blitter` | Shader blitter 使用者 |
