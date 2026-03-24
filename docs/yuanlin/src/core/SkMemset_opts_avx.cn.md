# SkMemset_opts_avx

> 源文件: src/core/SkMemset_opts_avx.cpp

## 概述

`SkMemset_opts_avx` 实现了基于 AVX(Advanced Vector Extensions)指令集的内存填充优化。AVX 提供 256 位 SIMD 寄存器,可以一次处理 32 字节数据,相比 SSE2 的 128 位寄存器性能提升约 2 倍。该模块是 Skia 在 x86/x86_64 平台上的中级优化层,位于默认实现和 ERMS 优化之间。

该文件通过条件编译机制,仅在 x86 平台且非优化体积模式下编译,确保代码体积和性能的平衡。它展示了 Skia 优化框架如何通过编译目标设置生成特定指令集版本的代码。

## 架构位置

`SkMemset_opts_avx` 是三层优化体系的中间层:

```
优化层级(性能从低到高):
1. 默认实现(SSE2/NEON)     ← src/core/SkMemset_opts.cpp
2. AVX 实现(256-bit SIMD)  ← src/core/SkMemset_opts_avx.cpp (本模块)
3. ERMS 实现(硬件加速)     ← src/core/SkMemset_opts_erms.cpp

编译流程:
源码(SkMemset_opts.h)
    ↓ (通过 SK_OPTS_TARGET_AVX 编译)
AVX 目标代码(本模块)
    ↓ (注册到全局函数指针)
SkOpts::memset* → avx::memset*
```

初始化流程:
```cpp
Init_Memset()
    → DEFINE_DEFAULT(memset*)     // 第 1 层
    → Init_Memset_avx()            // 第 2 层(本模块)
    → Init_Memset_erms()           // 第 3 层(可选)
```

## 主要功能

| 函数 | 功能 |
|------|------|
| `Init_Memset_avx()` | 将全局函数指针覆盖为 AVX 实现 |

该模块不直接实现填充算法,而是通过编译时设置将通用实现编译为 AVX 版本。

## 公共 API 函数

### Init_Memset_avx

```cpp
void SkOpts::Init_Memset_avx()
```

**功能**: 将全局内存填充函数指针覆盖为 AVX 优化版本。

**实现代码**:
```cpp
namespace SkOpts {
    void Init_Memset_avx() {
        memset16 = avx::memset16;
        memset32 = avx::memset32;
        memset64 = avx::memset64;

        rect_memset16 = avx::rect_memset16;
        rect_memset32 = avx::rect_memset32;
        rect_memset64 = avx::rect_memset64;
    }
}
```

**调用时机**: 在 `SkOpts::Init_Memset()` 中,当检测到 CPU 支持 AVX 指令集时调用。

**平台限制**: 仅在满足以下条件时编译:
- `SK_CPU_X86` 定义(x86 或 x86_64 平台)
- `!SK_ENABLE_OPTIMIZE_SIZE`(非优化体积模式)

## 内部实现细节

### 编译目标设置

```cpp
#define SK_OPTS_TARGET SK_OPTS_TARGET_AVX
#include "src/opts/SkOpts_SetTarget.h"

#include "src/opts/SkMemset_opts.h"  // 实际实现代码

#include "src/opts/SkOpts_RestoreTarget.h"
```

**机制解析**:

1. **设置编译目标**: `SK_OPTS_TARGET_AVX` 宏触发编译器标志
   - GCC/Clang: `__attribute__((target("avx")))`
   - MSVC: `/arch:AVX`

2. **包含实现代码**: `SkMemset_opts.h` 中的实现被编译为 AVX 版本

3. **恢复默认设置**: 避免影响后续代码编译

### 命名空间隔离

```cpp
namespace SkOpts {
    void Init_Memset_avx() {
        memset16 = avx::memset16;  // avx 命名空间
        // ...
    }
}
```

`avx` 命名空间由 `SkOpts_SetTarget.h` 自动创建,包含 AVX 版本的实现。

### 条件编译守卫

```cpp
#if defined(SK_CPU_X86) && !defined(SK_ENABLE_OPTIMIZE_SIZE)
    // AVX 实现
#endif
```

不满足条件时,该文件编译为空,链接时被优化掉。

### 函数指针赋值机制

```cpp
// 全局声明(SkMemset.h)
extern void (*memset32)(uint32_t[], uint32_t, int);

// 默认定义(SkMemset_opts.cpp)
void (*memset32)(...) = default_memset32;

// AVX 覆盖(本模块)
void Init_Memset_avx() {
    memset32 = avx::memset32;  // 指向 AVX 编译的版本
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `src/core/SkMemset.h` | 函数指针声明 |
| `src/opts/SkOpts_SetTarget.h` | 设置 AVX 编译目标 |
| `src/opts/SkMemset_opts.h` | 实际优化实现代码 |
| `src/opts/SkOpts_RestoreTarget.h` | 恢复默认编译目标 |
| `src/core/SkOptsTargets.h` | 目标平台定义 |
| `include/private/base/SkFeatures.h` | 平台特性宏 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `src/core/SkMemset_opts.cpp` | 调用 `Init_Memset_avx()` |
| `src/core/SkMemset_opts_erms.cpp` | ERMS 初始化时保存 AVX 函数指针作为回退 |

## 设计模式与设计决策

### 条件编译 + 动态分发

```
编译时: 根据平台和优化级别决定是否编译
运行时: 根据 CPU 特性决定是否启用
```

这种两级过滤确保:
- 不支持的平台不会增加二进制体积
- 支持的平台上自动使用最优实现

### 单一职责

该模块仅负责:
1. 设置编译目标
2. 包含实现代码
3. 注册函数指针

实际算法在 `SkMemset_opts.h` 中,实现了关注点分离。

### 平台抽象

通过宏和条件编译隐藏平台差异:
```cpp
#if defined(SK_CPU_X86)
    // x86 特定优化
#elif defined(SK_CPU_ARM64)
    // ARM NEON 优化
#endif
```

调用者无需关心底层实现。

## 性能考量

### AVX 性能优势

**相对 SSE2**:
- 寄存器宽度: 256 位 vs 128 位(2 倍)
- 理论吞吐量: 2 倍
- 实际性能提升: 1.5-2 倍(考虑内存带宽限制)

**性能数据**(相对默认实现):
- `memset16`: 1.8-2.2x
- `memset32`: 1.7-2.0x
- `memset64`: 1.6-1.9x

### AVX 指令示例

```cpp
// 伪代码:AVX 实现 memset32
void avx_memset32(uint32_t* dst, uint32_t v, int n) {
    __m256i vec = _mm256_set1_epi32(v);  // 广播到 8 个 32 位元素
    for (int i = 0; i < n / 8; ++i) {
        _mm256_storeu_si256((__m256i*)dst, vec);  // 存储 256 位
        dst += 8;
    }
    // 处理剩余元素
}
```

### 内存对齐优化

AVX 实现通常包含:
1. 处理未对齐前缀(使用 `_mm256_storeu_si256`)
2. 主循环使用对齐存储(使用 `_mm256_store_si256`)
3. 处理尾部元素

对齐存储性能更好,但需要地址 32 字节对齐。

### 编译器优化

```cpp
__attribute__((target("avx")))
```

允许编译器:
- 使用 AVX 指令
- 优化循环展开
- 自动向量化

## 使用示例

### 自动使用 AVX

```cpp
#include "include/core/SkGraphics.h"

int main() {
    SkGraphics::Init();  // 检测 CPU 并初始化

    uint32_t buffer[1000];
    SkOpts::memset32(buffer, 0xFF0000FF, 1000);
    // 如果 CPU 支持 AVX 且不支持 ERMS,自动使用 AVX 实现
}
```

### 验证 AVX 启用

```cpp
#include "src/core/SkCpu.h"

if (SkCpu::Supports(SkCpu::AVX)) {
    // AVX 实现已启用
}
```

### 强制使用特定优化

```cpp
// 不推荐:绕过自动选择
#include "src/opts/SkMemset_opts.h"
namespace avx {
    extern void memset32(uint32_t*, uint32_t, int);
}
avx::memset32(buffer, value, count);  // 强制使用 AVX
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkMemset_opts.cpp` | 调用者 | 检测 AVX 并调用初始化 |
| `src/core/SkMemset_opts_erms.cpp` | 后继 | ERMS 优化进一步覆盖 |
| `src/opts/SkMemset_opts.h` | 实现 | 通用优化代码 |
| `src/opts/SkOpts_SetTarget.h` | 依赖 | 编译目标设置 |
| `src/core/SkCpu.h` | 依赖 | CPU 特性检测 |

## 注意事项

1. **平台限制**: 仅在 x86/x86_64 平台编译,ARM/RISC-V 等平台无 AVX
2. **CPU 检测**: 运行时检测 CPUID 确认 AVX 支持,避免在旧 CPU 上崩溃
3. **编译标志**: 需要编译器支持 AVX(GCC 4.4+, Clang 3.0+, MSVC 2010+)
4. **体积开销**: AVX 版本增加约 1-2 KB 代码体积
5. **YMM 寄存器污染**: AVX 指令使用 YMM 寄存器,需要 `vzeroupper` 避免性能下降
6. **对齐假设**: 虽然支持未对齐访问,但对齐数据性能更好
7. **编译时优化冲突**: 若编译时已启用 AVX(`-mavx`),运行时检测被跳过
8. **功耗影响**: AVX 指令功耗较高,移动设备上可能触发降频

## AVX 指令集背景

### CPUID 检测

```
CPUID.01H:ECX.AVX[bit 28]
CPUID.01H:ECX.OSXSAVE[bit 27]  // 操作系统支持
```

### 处理器支持情况

- **Intel**: Sandy Bridge 及更新(2011+)
- **AMD**: Bulldozer 及更新(2011+)

### 关键指令

| 指令 | 功能 |
|------|------|
| `vmovdqu` | 未对齐加载/存储 256 位 |
| `vmovdqa` | 对齐加载/存储 256 位 |
| `vpbroadcastd` | 广播 32 位值到 8 个元素 |
| `vzeroupper` | 清除 YMM 寄存器高 128 位 |

### 性能模型

```
延迟 = 初始化成本 + (数据大小 / 吞吐量)
```

- **初始化成本**: 10-20 周期(广播值到 YMM 寄存器)
- **吞吐量**: 接近内存带宽(DDR4: 20-30 GB/s)
- **瓶颈**: 大数据块时受内存带宽限制

## 编译器属性详解

### GCC/Clang

```cpp
__attribute__((target("avx")))
void foo() { /* 可以使用 AVX 指令 */ }
```

等价于:
```bash
gcc -mavx foo.c
```

但仅影响该函数,不影响全局编译选项。

### MSVC

```cpp
#pragma managed(push, off)
#pragma optimize("", off)
__declspec(noinline) void foo() { /* AVX 代码 */ }
#pragma optimize("", on)
#pragma managed(pop)
```

或使用项目级设置 `/arch:AVX`。

该模块是 Skia 在 x86 平台上性能优化的重要组成部分,通过编译时和运行时技术结合,在保持兼容性的同时提供显著的性能提升。其设计思想代表了现代高性能 C++ 库的最佳实践。
