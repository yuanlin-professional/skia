# SkOptsTargets

> 源文件: src/core/SkOptsTargets.h

## 概述

`SkOptsTargets.h` 是 Skia 优化系统中的核心配置头文件，定义了各种 CPU 指令集优化目标的编译时常量。该文件为 `SkOpts` 系统提供了编译目标的抽象标识，使得 Skia 能够在编译时生成针对不同 CPU 指令集优化的代码版本，并在运行时根据实际 CPU 特性选择最优实现。

这些宏常量在编译流程中被用作条件编译的标志，控制哪些优化代码会被包含在最终的二进制文件中。

## 架构位置

`SkOptsTargets` 位于 Skia 编译系统的基础设施层：

- **所属模块**: `src/core/` - 核心内部实现
- **层级定位**: 编译时配置，最底层的宏定义
- **使用阶段**: 编译时（预处理器阶段）
- **作用范围**: 控制 `src/opts/` 目录下所有优化代码的编译

## 主要类与结构体

该文件不包含类或结构体，仅定义预处理器宏常量。

### 优化目标常量

| 宏常量 | 值 | 说明 |
|--------|----|----|
| `SK_OPTS_TARGET_DEFAULT` | `0x00` | 默认目标（基础指令集，如 SSE2） |
| `SK_OPTS_TARGET_SSSE3` | `0x01` | SSSE3 指令集优化（位 0） |
| `SK_OPTS_TARGET_AVX` | `0x02` | AVX 指令集优化（位 1） |
| `SK_OPTS_TARGET_HSW` | `0x04` | Haswell (AVX2) 指令集优化（位 2） |
| `SK_OPTS_TARGET_LASX` | `0x08` | LoongArch LASX 指令集优化（位 3） |

### 位域设计

这些常量采用位域（bitfield）设计，每个常量占用一个独立的位：

```
位 7  6  5  4  3  2  1  0
           ↓  ↓  ↓  ↓  ↓
           |  |  |  |  └─ SSSE3 (0x01)
           |  |  |  └──── AVX   (0x02)
           |  |  └─────── HSW   (0x04)
           |  └────────── LASX  (0x08)
           └───────────── (保留)
```

**设计理由**: 支持使用位运算进行组合和检测。

## 公共 API 函数

该文件不包含函数，仅提供宏定义供其他编译单元使用。

## 内部实现细节

### 1. 宏的使用场景

这些宏在 Skia 的编译系统中有两个主要用途：

#### 场景 A: 条件编译

在 `src/opts/SkOpts_SetTarget.h` 中使用：

```cpp
#if SK_OPTS_TARGET == SK_OPTS_TARGET_HSW
    #define SK_CPU_SSE_LEVEL SK_CPU_SSE_LEVEL_AVX2
    // ... 设置编译器标志
#elif SK_OPTS_TARGET == SK_OPTS_TARGET_AVX
    #define SK_CPU_SSE_LEVEL SK_CPU_SSE_LEVEL_AVX
    // ... 设置编译器标志
#endif
```

#### 场景 B: 编译标志传递

在构建系统（GN/CMake）中：

```gn
# BUILD.gn 示例
if (target_cpu == "x64") {
  source_set("opts_hsw") {
    sources = [ "src/opts/SkOpts_hsw.cpp" ]
    defines = [ "SK_OPTS_TARGET=SK_OPTS_TARGET_HSW" ]
    cflags = [ "-march=haswell" ]
  }
}
```

### 2. 指令集对应关系

| 常量 | CPU 指令集 | 典型 CPU | 引入时间 | 向量宽度 |
|------|-----------|---------|---------|---------|
| `DEFAULT` | SSE2 | Pentium 4+ | 2001 | 128 位 |
| `SSSE3` | SSSE3 | Core 2+ | 2006 | 128 位 |
| `AVX` | AVX | Sandy Bridge+ | 2011 | 256 位 |
| `HSW` | AVX2 + FMA | Haswell+ | 2013 | 256 位 |
| `LASX` | LoongArch LASX | 龙芯 3A5000+ | 2021 | 256 位 |

### 3. 优化层级关系

```
DEFAULT (SSE2)
    └─ SSSE3
        └─ AVX
            └─ HSW (AVX2)

LASX (独立分支，LoongArch)
```

**注意**: `HSW` 是 `AVX` 的超集，支持 AVX2 和 FMA 指令。

### 4. 编译流程

```
源代码（*.cpp）
    ↓
定义 SK_OPTS_TARGET 宏
    ↓
包含 SkOpts_SetTarget.h
    ↓
根据 SK_OPTS_TARGET 设置编译器标志和宏
    ↓
编译优化代码
    ↓
包含 SkOpts_RestoreTarget.h（恢复设置）
    ↓
生成特定指令集的对象文件
```

### 5. 运行时选择逻辑

虽然 `SkOptsTargets.h` 是编译时配置，但它与运行时选择紧密关联：

```cpp
// SkOpts.cpp 中的运行时逻辑
void Init() {
    #if SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_AVX2
        if (SkCpu::Supports(SkCpu::HSW)) {
            Init_hsw();  // 使用 SK_OPTS_TARGET_HSW 编译的代码
        }
    #endif
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| 无 | 该文件不依赖其他模块 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `src/opts/SkOpts_SetTarget.h` | 解释和应用优化目标 |
| `src/opts/SkOpts_RestoreTarget.h` | 清理优化目标设置 |
| `src/opts/SkOpts_hsw.cpp` | 使用 `SK_OPTS_TARGET_HSW` |
| `src/opts/SkOpts_skx.cpp` | 使用 SKX 相关目标（未在此文件定义） |
| `src/opts/SkOpts_lasx.cpp` | 使用 `SK_OPTS_TARGET_LASX` |
| `src/core/SkOpts.cpp` | 间接使用（通过条件编译） |
| 构建系统 (GN/CMake) | 设置编译标志 |

## 设计模式与设计决策

### 1. 位域标志模式

**设计决策**: 使用位掩码而非枚举或整数。

**优势**:
- 支持多目标组合（理论上可以 `HSW | SSSE3`）
- 快速位运算检测
- 紧凑的存储

**实际使用**: Skia 当前每个编译单元只使用一个目标，但设计上支持扩展。

### 2. 零值默认策略

**设计决策**: 默认目标值为 `0x00`。

**优势**:
- 未定义 `SK_OPTS_TARGET` 时自动回退到默认
- 简化条件判断（`if (!SK_OPTS_TARGET)` 表示默认）
- 与 C++ 零初始化语义一致

### 3. 平台特定常量

**设计决策**: 在同一文件中混合 x86 和 LoongArch 目标。

**理由**:
- 统一管理所有平台的优化目标
- 避免平台特定的头文件
- 简化构建系统

**代价**: 增加了跨平台的复杂性（需要确保值不冲突）

### 4. 十六进制表示

**设计决策**: 使用十六进制（`0x04`）而非十进制或二进制字面量。

**理由**:
- 位域模式更直观（`0x01`, `0x02`, `0x04`, `0x08` 清晰显示位位置）
- C++ 传统习惯（标志常量通常用十六进制）
- 避免 C++14 前不支持二进制字面量的问题

### 5. 无 SKX 定义

**观察**: 代码中提到 `Init_skx()` 但未定义 `SK_OPTS_TARGET_SKX`。

**原因**: SKX (Skylake-X, AVX512) 可能使用不同的机制或仍在开发中。

**推测**: 可能定义为 `0x10` 或使用其他配置方式。

### 6. 命名约定

**模式**: `SK_OPTS_TARGET_<ARCH>`

**解释**:
- `HSW`: Haswell 微架构代号
- `SSSE3`: 指令集名称
- `AVX`: 指令集名称
- `LASX`: LoongArch 特定扩展名称

**优势**: 直接映射到 CPU 特性，便于理解和维护。

## 性能考量

### 1. 编译时开销

**影响**: 多个优化目标导致相同代码被编译多次。

**示例**:
- `SkRasterPipeline_opts.h` 可能被编译 3-4 次（DEFAULT, AVX, HSW, SKX）
- 编译时间增加 2-4 倍

**缓解**:
- 优化仅应用于热路径代码
- 构建系统并行编译

### 2. 二进制体积

**影响**: 每个优化目标增加约 10-50KB 代码。

**示例**: 包含 HSW 和 SKX 优化可能增加 100KB 二进制体积。

**缓解**:
- `SK_ENABLE_OPTIMIZE_SIZE` 宏禁用所有优化
- 移动端通常只保留默认实现

### 3. 运行时性能

**收益**: 不同指令集的性能差异：

| 指令集 | 相对性能（归一化到 SSE2） |
|--------|-------------------------|
| SSE2 | 1.0x (基准) |
| SSSE3 | 1.1-1.3x |
| AVX | 1.5-2.0x |
| AVX2 (HSW) | 2.0-3.0x |
| AVX512 (SKX) | 2.5-4.0x |
| LASX | 1.8-2.5x |

**注意**: 实际性能取决于具体算法和数据。

### 4. CPU 检测开销

运行时 CPU 特性检测（`SkCpu::Supports()`）通常在初始化阶段执行一次，开销可忽略。

### 5. 指令集选择策略

**策略**: 选择 CPU 支持的最高级指令集。

**示例**:
```cpp
// 支持 AVX512 的 CPU
Init_skx();  // 使用 AVX512 实现
// 不会调用 Init_hsw() 或 Init_avx()
```

**注意**: 部分平台可能 AVX512 性能不佳（频率下降），Skia 可能需要启发式选择。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkOpts.h` | SkOpts 系统主头文件 |
| `src/core/SkOpts.cpp` | 运行时初始化和默认实现 |
| `src/opts/SkOpts_SetTarget.h` | 根据目标设置编译器标志 |
| `src/opts/SkOpts_RestoreTarget.h` | 恢复编译器设置 |
| `src/opts/SkOpts_hsw.cpp` | Haswell (AVX2) 优化实现 |
| `src/opts/SkOpts_skx.cpp` | Skylake-X (AVX512) 优化实现 |
| `src/opts/SkOpts_lasx.cpp` | LoongArch LASX 优化实现 |
| `src/opts/SkRasterPipeline_opts.h` | 光栅化管线优化（被多次编译） |
| `src/core/SkCpu.h` | 运行时 CPU 特性检测 |
| `BUILD.gn` | GN 构建文件，设置编译标志 |
| `CMakeLists.txt` | CMake 构建文件（如果使用） |

### 构建系统集成示例

```gn
# BUILD.gn 简化示例
if (is_x86) {
  source_set("opts_avx") {
    sources = [ "src/opts/SkOpts_avx.cpp" ]
    defines = [ "SK_OPTS_TARGET=0x02" ]  # SK_OPTS_TARGET_AVX
    cflags = [ "-mavx" ]
  }

  source_set("opts_hsw") {
    sources = [ "src/opts/SkOpts_hsw.cpp" ]
    defines = [ "SK_OPTS_TARGET=0x04" ]  # SK_OPTS_TARGET_HSW
    cflags = [ "-mavx2", "-mfma" ]
  }
}
```

## 扩展性考虑

### 当前值分配

```
0x00 - DEFAULT
0x01 - SSSE3
0x02 - AVX
0x04 - HSW
0x08 - LASX
0x10 - (可用于 SKX)
0x20 - (可用于 ARM NEON)
0x40 - (保留)
0x80 - (保留)
```

### 未来扩展方向

1. **ARM 支持**: 可能添加 `SK_OPTS_TARGET_NEON` (0x20)
2. **AVX512 变体**: 不同的 AVX512 子集（VNNI, BF16 等）
3. **新架构**: RISC-V Vector Extension, WebAssembly SIMD
4. **分层优化**: 同一架构的多个优化级别（如 AVX512 fast/slow）

### 潜在改进

1. **字符串化宏**: 便于调试和日志
   ```cpp
   #define SK_OPTS_TARGET_NAME(x) \
       ((x)==SK_OPTS_TARGET_HSW ? "HSW" : ...)
   ```

2. **编译时断言**: 确保值不冲突
   ```cpp
   static_assert((SK_OPTS_TARGET_HSW & SK_OPTS_TARGET_AVX) == 0);
   ```

3. **功能位检测**: 更细粒度的特性（FMA, BMI2 等）
   ```cpp
   #define SK_OPTS_FEATURE_FMA 0x100
   ```

这些改进可以增强系统的可维护性和扩展性，但当前简洁的设计已经满足 Skia 的需求。
