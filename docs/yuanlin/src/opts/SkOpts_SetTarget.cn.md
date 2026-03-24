# SkOpts_SetTarget

> 源文件: `src/opts/SkOpts_SetTarget.h`

## 概述

`SkOpts_SetTarget.h` 是 Skia 优化（opts）系统的核心基础设施头文件，负责根据目标 CPU 指令集架构设置编译命名空间和编译器属性。它的作用是让同一份 C++ 源代码能够针对不同的 SIMD 指令集（如 SSE2、SSSE3、AVX、AVX2、NEON、LSX/LASX 等）编译出多个特化版本，并在运行时根据 CPU 能力动态选择最优实现。

该文件有意不使用 include guard（`#ifndef ... #define ... #endif`），因为它需要被同一编译单元多次包含，每次使用不同的 `SK_OPTS_TARGET` 值来为不同的指令集配置编译环境。

## 架构位置

在 Skia 的优化架构中，`SkOpts_SetTarget.h` 处于编译基础设施层：

```
应用层代码
    |
SkOpts.h (运行时函数指针分发)
    |
SkOpts_xxx.cpp (各指令集的初始化入口)
    |
SkXxx_opts.h (包含实际优化实现的头文件)
    |
SkOpts_SetTarget.h / SkOpts_RestoreTarget.h (编译环境设置/恢复)
    |
SkFeatures.h (CPU 特性检测宏)
```

使用流程：在编译某个特定指令集的优化代码之前，先 `#include "src/opts/SkOpts_SetTarget.h"` 设置编译环境，然后包含实际的优化实现头文件，最后 `#include "src/opts/SkOpts_RestoreTarget.h"` 恢复编译环境。

## 主要类与结构体

该文件不定义任何类或结构体。它完全由预处理器宏和编译器指令组成。

### 关键宏定义

| 宏名称 | 说明 |
|--------|------|
| `SK_OPTS_TARGET` | 必须在包含本文件前定义，指定目标指令集（如 `SK_OPTS_TARGET_DEFAULT`、`SK_OPTS_TARGET_SSSE3` 等） |
| `SK_OPTS_NS` | 根据目标指令集自动设置的命名空间名称（如 `neon`、`skx`、`avx2`、`sse2`、`portable` 等） |
| `SK_OLD_CPU_SSE_LEVEL` | 在非默认目标模式下，保存原始 SSE 级别以供恢复使用 |
| `DEFINE_DEFAULT` | 仅在默认目标模式下定义，用于将函数指针绑定到默认命名空间的实现 |

## 公共 API 函数

该文件不包含任何函数定义。它通过宏和编译器指令影响后续包含的代码的编译行为。

### `DEFINE_DEFAULT(name)` 宏

```cpp
#define DEFINE_DEFAULT(name) decltype(name) name = SK_OPTS_NS::name
```

仅在 `SK_OPTS_TARGET == SK_OPTS_TARGET_DEFAULT` 模式下可用。用于将全局函数指针绑定到编译时默认指令集命名空间中的实现。

## 内部实现细节

### 两种工作模式

#### 1. 默认目标模式（`SK_OPTS_TARGET_DEFAULT`）

当 `SK_OPTS_TARGET == SK_OPTS_TARGET_DEFAULT` 时，文件根据编译器已知的 CPU 特性宏自动选择最高级别的命名空间：

```
检测优先级（从高到低）：
ARM NEON -> SKX -> AVX2 -> AVX -> SSE4.2 -> SSE4.1 -> SSSE3 -> SSE3 -> SSE2 -> SSE1 -> LASX -> LSX -> portable
```

此模式下：
- `SK_OPTS_NS` 被设置为对应的命名空间名称
- 定义 `DEFINE_DEFAULT` 宏用于函数指针初始化
- 不修改任何编译器选项

#### 2. 指定目标模式（非 `SK_OPTS_TARGET_DEFAULT`）

当指定了具体的目标指令集时，文件会：

1. **保存当前 SSE 级别**: 将 `SK_CPU_SSE_LEVEL` 保存到 `SK_OLD_CPU_SSE_LEVEL`，并取消定义原始宏。
2. **设置新的 SSE 级别**: 根据目标指令集重新定义 `SK_CPU_SSE_LEVEL`。
3. **设置编译器属性**: 使用 `pragma` 指令告知编译器为后续函数启用特定指令集：
   - Clang: `#pragma clang attribute push(__attribute__((target(...))), apply_to=function)`
   - GCC: `#pragma GCC push_options` + `#pragma GCC target(...)`
   - MSVC: 不需要特殊处理（通过 intrinsic 头文件即可）
4. **包含 intrinsic 头文件**: 针对 clang-cl（Clang 的 MSVC 兼容模式），显式包含所需的 intrinsic 头文件。

### 支持的目标指令集

| 目标宏 | 命名空间 | SSE 级别 | 编译器 target 属性 |
|--------|----------|----------|-------------------|
| `SK_OPTS_TARGET_SSSE3` | `ssse3` | `SK_CPU_SSE_LEVEL_SSSE3` | `sse2,ssse3` |
| `SK_OPTS_TARGET_AVX` | `avx` | `SK_CPU_SSE_LEVEL_AVX` | `sse2,ssse3,sse4.1,sse4.2,avx` |
| `SK_OPTS_TARGET_HSW` | `hsw` | `SK_CPU_SSE_LEVEL_AVX2` | `sse2,ssse3,sse4.1,sse4.2,avx,avx2,bmi,bmi2,f16c,fma` |
| `SK_OPTS_TARGET_LASX` | `lasx` | N/A（使用 `SK_CPU_LSX_LEVEL`） | `lasx` |

### clang-cl 兼容性处理

文件中包含了针对 clang-cl（`__clang__` + `_MSC_VER` 同时定义）的特殊处理。由于 Clang 在 MSVC 兼容模式下会跳过"不支持"的 intrinsic 头文件，因此需要显式包含各级别的 intrinsic 头文件：

- `pmmintrin.h` (SSE3)
- `tmmintrin.h` (SSSE3)
- `smmintrin.h` (SSE4.1)
- `avxintrin.h` (AVX)
- `avx2intrin.h` (AVX2)
- `f16cintrin.h` (F16C)
- `bmi2intrin.h` (BMI2)
- `fmaintrin.h` (FMA)

此外还包含了对 LLVM RTM intrinsic bug 的 workaround（`#define __RTMINTRIN_H`）。

### GCC 限制

代码注释中提到，GCC 不允许 `target()` 属性中的字符串通过预处理器宏展开，必须是字面字符串。这就是为什么每个目标指令集都需要独立的 `#elif` 分支，而不能通过宏来消除重复代码。

## 依赖关系

### 直接依赖
- `include/private/base/SkFeatures.h` - 定义 CPU 特性检测宏（`SK_CPU_SSE_LEVEL`、`SK_ARM_HAS_NEON`、`SK_CPU_LSX_LEVEL` 等）

### 配对文件
- `src/opts/SkOpts_RestoreTarget.h` - 恢复本文件所做的编译环境修改。每次包含 `SkOpts_SetTarget.h` 后，必须在优化代码之后包含 `SkOpts_RestoreTarget.h`。

### 被引用方
- `src/opts/SkOpts_skx.cpp` 等优化入口文件
- 所有需要编译多指令集版本的 `*_opts.h` 文件的使用者

## 设计模式与设计决策

### 无 include guard 设计
有意省略 include guard 是该文件最显著的设计决策。这允许同一编译单元多次包含该文件，每次设置不同的目标指令集，从而在单个 `.cpp` 文件中编译出多个指令集版本的代码。

### Push/Pop 编译器属性
使用编译器的 push/pop 机制（Clang 的 `attribute push/pop`、GCC 的 `push_options/pop_options`）确保指令集设置只影响夹在 SetTarget 和 RestoreTarget 之间的代码，不会泄漏到其他代码。

### 命名空间隔离
通过 `SK_OPTS_NS` 宏将不同指令集的实现放入不同的命名空间（如 `ssse3`、`avx`、`hsw`），避免符号冲突，并允许运行时通过函数指针选择最优实现。

### 编译器抽象
同时支持 Clang、GCC 和 MSVC 三大编译器家族，通过条件编译实现跨编译器的统一接口。

## 性能考量

- **编译时优化**: 该文件本身不产生任何运行时代码，所有工作都在编译预处理阶段完成，因此没有运行时开销。
- **指令集分层**: 支持从基础的 SSE1 到高级的 AVX2/SKX，以及 ARM NEON 和龙芯 LSX/LASX，覆盖了主流 CPU 架构的 SIMD 能力。
- **运行时分发**: 通过 `DEFINE_DEFAULT` 宏和 SkOpts 的初始化机制，实现了零开销的运行时指令集选择（函数指针只在程序启动时设置一次）。

## 相关文件

- `src/opts/SkOpts_RestoreTarget.h` - 配对使用的编译环境恢复文件
- `include/private/base/SkFeatures.h` - CPU 特性检测宏定义
- `src/core/SkOpts.h` - 运行时优化函数指针声明
- `src/opts/SkOpts_skx.cpp` - SKX 指令集优化入口（使用本文件的典型示例）
- `src/opts/SkBlitRow_opts.h` - 使用 `SK_OPTS_NS` 命名空间的优化实现示例
- `src/opts/SkBlitMask_opts.h` - 使用 `SK_OPTS_NS` 命名空间的优化实现示例
