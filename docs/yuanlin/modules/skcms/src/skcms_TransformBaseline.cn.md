# skcms_TransformBaseline

> 源文件: modules/skcms/src/skcms_TransformBaseline.cc

## 概述

`skcms_TransformBaseline.cc` 是 skcms（Skia Color Management System）颜色空间转换引擎的基线实现文件。该文件通过实例化通用的颜色转换模板（`Transform_inl.h`）来提供基础的、可移植的颜色转换功能。作为 skcms 的后备实现，它确保颜色管理功能在所有平台上都能正常工作，即使在不支持高级 SIMD 指令集（如 AVX、Neon）的平台上。

该实现支持两种编译模式：可移植标量模式（`SKCMS_PORTABLE`）和基础 SIMD 模式。在标量模式下，每次处理单个像素（N=1）；在 SIMD 模式下，使用平台基础 SIMD 指令（如 SSE、Neon）每次处理 4 个像素。这种设计确保了代码的可移植性和基本性能保证。

## 架构位置

`skcms_TransformBaseline` 在颜色管理架构中的位置：

```
Skia 颜色管理层次
├── modules/skcms/                颜色管理模块
│   ├── skcms_public.h            公共 API
│   ├── src/
│   │   ├── skcms_Transform.h     转换操作定义
│   │   ├── skcms_internals.h     内部工具
│   │   ├── Transform_inl.h       通用转换模板（核心）
│   │   ├── skcms_TransformBaseline.cc  本文件（基线实现）
│   │   ├── skcms_TransformHsw.cc      AVX2 优化实现
│   │   └── skcms_TransformSkx.cc      AVX-512 优化实现
│   └── skcms.cc                  主入口（运行时分发）
└── src/core/
    ├── SkColorSpace.cpp          Skia 颜色空间封装
    └── SkRasterPipeline.cpp      光栅化管线
```

**运行时选择策略**：
1. CPU 特性检测（在 `skcms.cc` 中）
2. 优先选择优化实现（Skx > Hsw > Baseline）
3. 如果优化实现不可用，回退到 Baseline

## 主要类与结构体

### 命名空间组织

```cpp
namespace skcms_private {
namespace baseline {
    // 基线实现
}
}
```

**命名空间设计**：
- `skcms_private`：隔离内部实现，避免符号冲突
- `baseline`：与其他优化实现（`hsw`、`skx`）区分

### 编译时配置

```cpp
#if defined(SKCMS_PORTABLE)
    #define N 1                         // 每次处理 1 个像素
    template <typename T> using V = T;  // 标量类型
#else
    #define N 4                         // 每次处理 4 个像素
    template <typename T> using V = skcms_private::Vec<N,T>;  // 向量类型
#endif
```

**配置说明**：
- `N`：并行处理的像素数（SIMD 宽度）
- `V<T>`：向量类型模板，封装平台 SIMD 类型

### 平台 SIMD 支持

```cpp
#if defined(__ARM_NEON)
    #include <arm_neon.h>          // ARM Neon intrinsics
#elif defined(__SSE__)
    #include <immintrin.h>         // x86 SSE/AVX intrinsics
#elif defined(__loongarch_sx)
    #include <lsxintrin.h>         // LoongArch SIMD
#endif
```

**支持的 SIMD 指令集**：
- **ARM**：Neon（128位）
- **x86**：SSE/SSE2（128位）
- **LoongArch**：LSX（128位）

## 公共 API 函数

该文件不直接导出公共函数，而是通过 `#include "Transform_inl.h"` 实例化模板函数。主要生成的函数包括：

### run_program (隐式生成)

```cpp
void run_program(const Op* program, const void** contexts, ptrdiff_t programSize,
                 const char* src, char* dst, int n,
                 size_t src_bpp, size_t dst_bpp);
```

**功能**：执行颜色转换程序（操作序列）。

**参数**：
- `program`：操作数组（如 load → gamma → matrix → store）
- `contexts`：操作上下文数据（如 gamma 曲线参数）
- `programSize`：程序大小
- `src`：源像素缓冲区
- `dst`：目标像素缓冲区
- `n`：像素数量
- `src_bpp`：源像素字节数
- `dst_bpp`：目标像素字节数

### 加载/存储操作 (隐式生成)

通过宏定义生成大量操作函数：

```cpp
// 加载操作示例
SKCMS_WORK_OPS(M)
    M(load_a8)      // 加载 8位 alpha
    M(load_8888)    // 加载 RGBA8888
    M(load_ffff)    // 加载 RGBA float32
    // ... 更多格式

// 存储操作示例
SKCMS_STORE_OPS(M)
    M(store_a8)
    M(store_8888)
    M(store_ffff)
    // ... 更多格式
```

### 颜色空间转换操作 (隐式生成)

```cpp
// Gamma 校正
gamma_r, gamma_g, gamma_b, gamma_rgb

// 传递函数（Transfer Function）
tf_r, tf_g, tf_b, tf_rgb

// PQ（Perceptual Quantizer，HDR）
pq_r, pq_g, pq_b, pq_rgb

// HLG（Hybrid Log-Gamma，HDR）
hlg_r, hlg_g, hlg_b, hlg_rgb

// 矩阵变换
matrix_3x3    // RGB → RGB
matrix_3x4    // RGB+A → RGB+A

// 颜色空间转换
lab_to_xyz    // Lab → XYZ
xyz_to_lab    // XYZ → Lab

// 查找表（LUT）
table_r, table_g, table_b, table_a
clut_A2B, clut_B2A  // 多维 LUT
```

## 内部实现细节

### 模板实例化机制

通过包含 `Transform_inl.h` 实现代码重用：

```cpp
#define N 4
template <typename T> using V = skcms_private::Vec<N,T>;
#include "Transform_inl.h"  // 实例化所有转换操作
```

**工作原理**：
1. `Transform_inl.h` 包含模板化的颜色转换实现
2. 通过 `N` 和 `V<T>` 控制 SIMD 宽度和类型
3. 编译器为 `N=4` 生成专门的代码
4. 对于 `N=1`（标量模式），生成无 SIMD 的代码

### SIMD 向量抽象

`Vec<N,T>` 提供统一的向量接口：

```cpp
// 示例：N=4 时的向量操作
V<float> r, g, b, a;  // 4 个 float 的向量

// 加载
r = load<float>(src_ptr);

// 算术运算
r = r * 2.0f + 1.0f;

// 比较
V<bool> mask = r > 0.5f;

// 存储
store(dst_ptr, r);
```

**平台映射**：
- **x86 SSE**：`V<float>` → `__m128`
- **ARM Neon**：`V<float>` → `float32x4_t`
- **标量**：`V<float>` → `float`

### 标量模式的退化

当 `N=1` 时：

```cpp
template <typename T> using V = T;  // 向量就是标量
```

所有向量操作退化为标量操作：

```cpp
// N=4 版本
V<float> r = load<float>(src);  // 加载 4 个 float
r = r * 2.0f;                   // 并行乘法

// N=1 版本
float r = load<float>(src);     // 加载 1 个 float
r = r * 2.0f;                   // 标量乘法
```

编译器会完全展开循环，生成高效的标量代码。

### 内联头文件模式

`Transform_inl.h` 采用内联实现：

**优点**：
- 代码重用：一份代码生成多个优化版本
- 编译时优化：内联消除抽象开销
- 灵活配置：通过宏控制行为

**缺点**：
- 编译时间长：多次实例化模板
- 二进制大小：生成多份代码副本

## 依赖关系

### 头文件依赖

```cpp
#include "skcms_public.h"      // 公共 API 定义
#include "skcms_internals.h"   // 内部工具宏
#include "skcms_Transform.h"   // 操作定义
#include <assert.h>
#include <float.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
```

### SIMD 头文件（条件编译）

```cpp
#if defined(__ARM_NEON)
    #include <arm_neon.h>
#elif defined(__SSE__)
    #include <immintrin.h>
    #if defined(__clang__)
        #include <smmintrin.h>  // SSE4.1
    #endif
#elif defined(__loongarch_sx)
    #include <lsxintrin.h>
#endif
```

### 模板依赖

```cpp
#include "Transform_inl.h"  // 核心转换逻辑
```

## 设计模式与设计决策

### 策略模式（运行时分发）

skcms 使用策略模式选择实现：

```cpp
// 伪代码（在 skcms.cc 中）
if (cpu_supports_avx512()) {
    skcms_private::skx::run_program(...);
} else if (cpu_supports_avx2()) {
    skcms_private::hsw::run_program(...);
} else {
    skcms_private::baseline::run_program(...);  // 本文件
}
```

**优势**：
- 自动选择最优实现
- 透明的性能提升
- 保证兼容性

### 模板元编程

通过模板参数控制生成代码：

```cpp
#define N 4  // 编译时常量
template <typename T> using V = Vec<N,T>;
```

**好处**：
- 零运行时开销
- 编译器能完全优化
- 类型安全

### 内联头文件模式

`Transform_inl.h` 包含实现而非声明：

**设计理由**：
- 需要为不同 `N` 值生成代码
- 模板必须在头文件中定义
- 通过命名空间避免符号冲突

### 可移植性优先

默认支持标量模式：

```cpp
#if defined(SKCMS_PORTABLE)
    #define N 1
```

**设计决策**：
- 不依赖 SIMD 指令
- 支持所有平台（包括嵌入式）
- 可用于调试和验证

## 性能考量

### SIMD 宽度选择

基线实现使用 `N=4`：

**原因**：
- 匹配 SSE/Neon 的自然宽度（128位）
- 平衡性能和代码大小
- 现代 CPU 广泛支持

**对比**：
- `N=1`：标量，最慢但最兼容
- `N=4`：SSE/Neon，基础 SIMD
- `N=8`：AVX2，更快（在 Hsw 实现）
- `N=16`：AVX-512，最快（在 Skx 实现）

### 内存对齐

SIMD 操作对内存对齐敏感：

```cpp
// 理想情况：对齐到 16 字节
float* aligned_ptr = ...; // __attribute__((aligned(16)))

// 实际代码需要处理未对齐情况
V<float> data = load_unaligned(ptr);
```

基线实现通常使用未对齐加载，牺牲少量性能换取通用性。

### 编译器优化

关键优化标志：

```bash
-O3                 # 激进优化
-march=native       # 针对本地 CPU 优化
-ffast-math         # 快速浮点数学（可能损失精度）
```

### 性能基准

典型性能（相对标量实现）：

- **标量（N=1）**：基线 1x
- **SSE/Neon（N=4）**：约 3-4x
- **AVX2（N=8）**：约 6-8x
- **AVX-512（N=16）**：约 10-15x

实际加速比取决于操作类型和数据局部性。

## 相关文件

### 接口定义
- `/Users/yuanlin/workspace/skia/modules/skcms/skcms_public.h` - 公共 API

### 核心实现
- `/Users/yuanlin/workspace/skia/modules/skcms/src/Transform_inl.h` - 转换逻辑模板
- `/Users/yuanlin/workspace/skia/modules/skcms/src/skcms_Transform.h` - 操作定义

### 优化实现
- `/Users/yuanlin/workspace/skia/modules/skcms/src/skcms_TransformHsw.cc` - AVX2 优化（N=8）
- `/Users/yuanlin/workspace/skia/modules/skcms/src/skcms_TransformSkx.cc` - AVX-512 优化（N=16）

### 运行时分发
- `/Users/yuanlin/workspace/skia/modules/skcms/skcms.cc` - CPU 检测和函数分发

### 内部工具
- `/Users/yuanlin/workspace/skia/modules/skcms/src/skcms_internals.h` - 宏定义和工具

### 使用场景
- `/Users/yuanlin/workspace/skia/src/core/SkColorSpace.cpp` - Skia 颜色空间管理
- `/Users/yuanlin/workspace/skia/src/core/SkRasterPipeline.cpp` - 光栅化管线
