# skcms_TransformSkx - AVX-512 颜色转换编译单元

> 源文件: `modules/skcms/src/skcms_TransformSkx.cc`

## 概述

skcms_TransformSkx.cc 是 skcms 颜色转换引擎的 AVX-512（Skylake-X）指令集特化编译单元。它在 `skcms_private::skx` 命名空间中生成 16 路 SIMD 并行的颜色转换代码。当目标平台不支持 AVX-512 时，自动回退到 baseline 实现。

## 架构位置

该文件是 skcms 多指令集分发架构中的三个编译单元之一（baseline、hsw、skx），专门针对 AVX-512F + AVX-512DQ 指令集编译。运行时根据 CPU 能力检测选择是否使用此路径。

**分发链**: `skcms_Transform()` -> CPU 检测 -> `skx::run_program()` (本文件) / `hsw::run_program()` / `baseline::run_program()`

## 主要类与结构体

无独立定义的类或结构体，所有类型通过包含 Transform_inl.h 获得。

## 公共 API 函数

### `skcms_private::skx::run_program`
AVX-512 版本的颜色转换管线执行函数。

- **启用 SKX 时**: 定义 `USING_AVX512F`，设置 `N=16`，包含 Transform_inl.h 生成 16 路 SIMD 代码
- **禁用 SKX 时**（`SKCMS_DISABLE_SKX`）: 直接转发到 `baseline::run_program`

## 内部实现细节

### 编译条件
```cpp
#if defined(SKCMS_DISABLE_SKX)
    // 回退到 baseline
#else
    #define USING_AVX512F
    #define N 16
    template <typename T> using V = skcms_private::Vec<N,T>;
    #include "Transform_inl.h"
#endif
```

### 头文件依赖
按条件包含平台特定头文件：
- ARM: `arm_neon.h`
- x86 SSE: `immintrin.h`（以及 Clang 的额外头文件 `smmintrin.h`, `avxintrin.h` 等）

## 依赖关系

- **skcms_public.h**: skcms 公共类型
- **skcms_internals.h**: 内部宏和配置
- **skcms_Transform.h**: Op 枚举和 Vec 类型
- **Transform_inl.h**: 操作的参数化实现

## 设计模式与设计决策

1. **条件编译回退**: 当 AVX-512 不可用时，不会产生编译错误，而是平滑回退到 baseline 实现。
2. **独立编译单元**: SKX 代码编译为独立的 .o 文件，使用 `-mavx512f -mavx512dq` 编译选项，不影响其他代码的编译。
3. **最小化胶水代码**: 文件只有 58 行，核心逻辑完全通过 `#include "Transform_inl.h"` 复用。

## 性能考量

- **16 路并行**: 每次处理 16 个像素，是 baseline SSE 的 4 倍、AVX2 的 2 倍
- **AVX-512 特有指令**: 利用 `_mm512_i32gather_epi32` 等宽向量 gather 指令加速 CLUT 采样
- **适用场景**: 大批量像素处理（如图像色彩空间转换）可获得显著加速
- **寄存器压力**: 16 路 SIMD 使用 32 个 ZMM 寄存器，函数内联可能增加溢出
- **自动回退**: 不支持 SKX 时编译为简单的转发函数，零额外开销

## 使用注意事项

1. 该文件需要使用 `-mavx512f -mavx512dq` 编译标志
2. `SKCMS_DISABLE_SKX` 宏可强制禁用 AVX-512 路径
3. 在 Android 平台上 SKX 被自动禁用（不太可能受益）
4. 非 x86-64 平台上 SKX 也被自动禁用
5. 运行时 CPU 检测由 skcms_Transform 调度层处理，本文件不涉及

## 相关文件

- `modules/skcms/src/Transform_inl.h` - 共享的操作实现
- `modules/skcms/src/skcms_Transform.h` - 操作枚举和接口声明
- `modules/skcms/src/skcms_internals.h` - SKCMS_DISABLE_SKX 宏定义
- `modules/skcms/src/skcms_TransformHsw.cc` - 类似的 AVX2 编译单元
