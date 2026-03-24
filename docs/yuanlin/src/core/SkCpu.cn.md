# SkCpu

> 源文件
> - src/core/SkCpu.h
> - src/core/SkCpu.cpp

## 概述

`SkCpu` 是 Skia 图形库中用于运行时 CPU 特性检测的模块。它在程序启动时检测当前处理器支持的 SIMD 指令集扩展(如 SSE、AVX、NEON 等),并将结果缓存供后续优化代码使用。这使得 Skia 能够根据不同硬件能力自适应选择最优执行路径,在保证兼容性的同时最大化性能。

该模块支持 x86/x64 架构的多种 SSE/AVX 扩展,以及 LoongArch 架构的 LSX/LASX 指令集。通过编译时已知特性和运行时检测的组合,实现了灵活的特性查询机制。

## 架构位置

`SkCpu` 位于 Skia 的基础设施层,为整个库提供底层硬件能力信息:

```
Skia Core Infrastructure
  ├─ Platform Abstraction
  │   ├─ SkCpu ← 当前模块(CPU 特性检测)
  │   ├─ SkOpts (优化函数指针)
  │   └─ SkOnce (单次初始化)
  ├─ SIMD Implementations
  │   ├─ SkOpts_sse*.cpp (SSE 优化)
  │   ├─ SkOpts_avx*.cpp (AVX 优化)
  │   └─ SkOpts_neon.cpp (ARM NEON)
  └─ Core Algorithms
      └─ (根据 SkCpu 结果选择实现)
```

SkOpts 模块依赖 SkCpu 的检测结果来选择合适的函数实现。

## 主要类与结构体

### SkCpu

**类型**: 结构体(struct),纯静态成员

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| gCachedFeatures | static uint32_t | 缓存的 CPU 特性位掩码(私有) |

**核心职责**:
- 定义 CPU 特性常量(枚举值)
- 提供运行时特性检测接口
- 缓存检测结果避免重复查询

### CPU 特性枚举(x86/x64)

| 常量 | 位值 | 说明 |
|------|------|------|
| SSE1 | 1 << 0 | Streaming SIMD Extensions |
| SSE2 | 1 << 1 | SSE2(Pentium 4+) |
| SSE3 | 1 << 2 | SSE3(Prescott+) |
| SSSE3 | 1 << 3 | Supplemental SSE3(Core 2+) |
| SSE41 | 1 << 4 | SSE4.1(Penryn+) |
| SSE42 | 1 << 5 | SSE4.2(Nehalem+) |
| AVX | 1 << 6 | Advanced Vector Extensions(Sandy Bridge+) |
| F16C | 1 << 7 | 半精度浮点转换(Ivy Bridge+) |
| FMA | 1 << 8 | 融合乘加指令(Haswell+) |
| AVX2 | 1 << 9 | AVX2(Haswell+) |
| BMI1 | 1 << 10 | Bit Manipulation Instructions 1 |
| BMI2 | 1 << 11 | Bit Manipulation Instructions 2 |
| HSW | AVX2\|BMI1\|BMI2\|F16C\|FMA | Haswell 处理器特性别名 |
| AVX512F | 1 << 12 | AVX-512 基础指令 |
| AVX512DQ | 1 << 13 | AVX-512 双字/四字指令 |
| AVX512IFMA | 1 << 14 | 整数融合乘加 |
| AVX512PF | 1 << 15 | 预取指令 |
| AVX512ER | 1 << 16 | 指数和倒数指令 |
| AVX512CD | 1 << 17 | 冲突检测指令 |
| AVX512BW | 1 << 18 | 字节/字操作 |
| AVX512VL | 1 << 19 | 向量长度扩展 |
| SKX | AVX512F\|AVX512DQ\|AVX512CD\|AVX512BW\|AVX512VL | Skylake-X 特性别名 |
| ERMS | 1 << 20 | Enhanced REP MOVSB/STOSB |

### CPU 特性枚举(LoongArch)

| 常量 | 位值 | 说明 |
|------|------|------|
| LOONGARCH_SX | 1 << 0 | LoongArch SIMD Extension (LSX, 128位) |
| LOONGARCH_ASX | 1 << 1 | LoongArch Advanced SIMD Extension (LASX, 256位) |

## 公共 API 函数

### CacheRuntimeFeatures

```cpp
static void CacheRuntimeFeatures()
```

检测并缓存 CPU 特性。该函数使用 `SkOnce` 确保只执行一次,即使多线程并发调用也安全。

**执行时机**: 通常在程序初始化早期调用(Skia 自动初始化)。

### Supports

```cpp
static bool Supports(uint32_t mask)
```

检查 CPU 是否支持指定的特性组合。

**参数**:
- `mask`: 特性位掩码,可以是单个特性或多个特性的按位或(OR)

**返回值**:
- `true`: CPU 支持所有指定特性
- `false`: 至少有一个特性不被支持

**实现原理**:
1. 读取缓存的 `gCachedFeatures`
2. 根据编译时宏(如 `SK_CPU_SSE_LEVEL`)添加已知特性
3. 应用 CPU 限制宏(如 `SK_CPU_LIMIT_SSE41`)
4. 检查 `(features & mask) == mask`

**示例**:
```cpp
if (SkCpu::Supports(SkCpu::SSE41)) {
    // 使用 SSE4.1 优化路径
}

if (SkCpu::Supports(SkCpu::AVX | SkCpu::F16C)) {
    // 使用 AVX + F16C 优化路径
}
```

## 内部实现细节

### x86/x64 特性检测 (read_cpu_features)

**检测方法**: 使用 CPUID 指令

**CPUID 调用**:
1. **CPUID(1)**: 基本特性
   - EAX=1 返回处理器特性标志
   - EDX[25]: SSE, EDX[26]: SSE2
   - ECX[0]: SSE3, ECX[9]: SSSE3, ECX[19]: SSE4.1, ECX[20]: SSE4.2

2. **XGETBV(0)**: 操作系统支持检查
   - 检查 XSAVE 和 OSXSAVE 标志
   - 验证 XMM(bit 1)和 YMM(bit 2)状态已启用
   - 验证 ZMM(bits 5-7)状态已启用(AVX-512)

3. **CPUID(7)**: 扩展特性
   - EAX=7, ECX=0 返回扩展特性
   - EBX[5]: AVX2, EBX[3]: BMI1, EBX[8]: BMI2, EBX[9]: ERMS
   - EBX[16-31]: AVX-512 各种子特性

**平台差异**:
- **MSVC**: 使用 `__cpuid()` 和 `_xgetbv()` 内建函数
- **GCC/Clang**: 使用 `__get_cpuid()` 和内联汇编

### LoongArch 特性检测

**检测方法**: 使用 Linux `getauxval()` 系统调用

```cpp
uint64_t hwcap = getauxval(AT_HWCAP);
if (hwcap & HWCAP_LOONGARCH_LSX)  { features |= LOONGARCH_SX; }
if (hwcap & HWCAP_LOONGARCH_LASX) { features |= LOONGARCH_ASX; }
```

`AT_HWCAP` 提供硬件能力标志,由操作系统内核填充。

### 编译时特性优化

`Supports()` 函数通过编译时宏内联已知特性:

```cpp
#if SK_CPU_SSE_LEVEL >= SK_CPU_SSE_LEVEL_SSE2
    features |= SSE2;
#endif
```

当编译时指定了最低 SSE 级别,编译器可以将条件判断优化为常量,实现零开销特性检查。

### CPU 特性限制

支持限制最大特性级别,用于测试和调试:

```cpp
#if defined(SK_CPU_LIMIT_SSE41)
    features &= (SSE1 | SSE2 | SSE3 | SSSE3 | SSE41);
#endif
```

这允许在高端硬件上测试低端代码路径。

### 线程安全

使用 `SkOnce` 实现单次初始化:

```cpp
static SkOnce once;
once([] { gCachedFeatures = read_cpu_features(); });
```

`SkOnce` 保证 lambda 只执行一次,并提供内存屏障确保可见性。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkTypes.h | 基础类型定义和平台宏 |
| include/private/base/SkOnce.h | 单次初始化原语 |
| intrin.h (MSVC) | CPUID 内建函数 |
| cpuid.h (GCC/Clang) | CPUID 内建函数 |
| sys/auxv.h (Linux) | getauxval 系统调用 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| src/opts/SkOpts.cpp | 选择优化函数实现 |
| src/core/SkSwizzle.cpp | 像素格式转换优化选择 |
| src/core/SkBlitRow.cpp | 位块传输优化选择 |
| src/effects/SkRuntimeEffect.cpp | 运行时特性决策 |

## 设计模式与设计决策

### 设计模式

1. **单例模式**: `gCachedFeatures` 全局唯一实例
2. **懒初始化**: 使用 `SkOnce` 延迟到首次调用时检测
3. **位掩码模式**: 使用位标志高效表示和组合特性
4. **门面模式**: 隐藏平台差异,提供统一接口

### 设计决策

**为何缓存特性而非每次检测**:
- CPUID 指令开销较大(数百个时钟周期)
- 特性在运行时不会改变
- 查询频繁,缓存可大幅提升性能

**为何使用内联函数**:
- `Supports()` 声明为内联,编译器可以:
  - 常量折叠:编译时已知特性直接优化为 true/false
  - 消除死代码:不支持的路径完全移除
  - 零运行时开销:在最优情况下

**编译时和运行时特性的组合**:
- 编译时特性(`SK_CPU_SSE_LEVEL`)保证最低要求
- 运行时检测发现额外能力
- 两者按位或(OR)组合,既安全又灵活

**为何支持 CPU 限制宏**:
- 允许在高端机器上测试低端路径
- 便于性能对比和回归测试
- 调试时可快速定位优化代码问题

**为何 AVX-512 检查更复杂**:
- AVX-512 需要额外的 ZMM 状态保存支持
- 某些操作系统不支持 AVX-512 上下文切换
- 必须验证 `xgetbv(0)` 中的 bits 5-7

## 性能考量

### 优化策略

1. **单次初始化**: 检测开销分摊到整个程序生命周期
2. **内联查询**: `Supports()` 内联,查询成本接近一次位运算
3. **编译时优化**: 已知特性在编译时解析,零运行时成本
4. **位掩码**: 特性检查只需一次位与和比较

### 性能特征

- **初始化开销**: 约 1-10 微秒(仅执行一次)
- **查询开销**: 内联后约 1-2 个时钟周期(读内存 + 位运算)
- **内存占用**: 4 字节静态变量

### 典型使用模式

```cpp
// 编译时已知 SSE2,运行时检测 AVX
void optimized_function(const float* data, int count) {
    if (SkCpu::Supports(SkCpu::AVX2)) {
        process_avx2(data, count);  // 使用 AVX2 SIMD
    } else if (SkCpu::Supports(SkCpu::SSE41)) {
        process_sse41(data, count); // 降级到 SSE4.1
    } else {
        process_sse2(data, count);  // 最低保证 SSE2
    }
}
```

编译器可以消除不可能的分支,生成最优代码。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/private/base/SkOnce.h | 依赖 | 单次初始化原语 |
| src/opts/SkOpts.h | 使用者 | 优化函数选择 |
| src/opts/SkOpts_sse*.cpp | 使用者 | SSE 优化实现 |
| src/opts/SkOpts_avx*.cpp | 使用者 | AVX 优化实现 |
| src/opts/SkOpts_hsw.cpp | 使用者 | Haswell 优化实现 |
| src/opts/SkOpts_skx.cpp | 使用者 | Skylake-X 优化实现 |
| src/core/SkSwizzle.cpp | 使用者 | 像素格式转换优化 |
| src/core/SkBlitRow.cpp | 使用者 | 位块传输优化 |
