# SkOpts_hsw

> 源文件: `src/opts/SkOpts_hsw.cpp`

## 概述

`SkOpts_hsw.cpp` 是 Skia 图形库中针对 Intel Haswell（HSW）微架构及其 AVX2 指令集的光栅化管线优化初始化文件。该文件负责在运行时检测到 CPU 支持 AVX2（以及 HSW 架构附带的 FMA、BMI1/BMI2 等指令集）时，将光栅化管线（Raster Pipeline）的各阶段函数指针替换为使用 AVX2 向量化指令优化后的实现。

Haswell 是 Intel 于 2013 年推出的处理器微架构，引入了 AVX2 指令集，将整数 SIMD 操作从 128 位扩展到 256 位。这使得 Skia 在支持 AVX2 的 CPU 上能够一次处理更多像素数据，显著提升渲染吞吐量。

## 架构位置

该文件位于 Skia 的 `src/opts/` 目录下，是 **SkOpts 运行时优化分发机制** 的关键组件之一。在 x86/x64 平台上，它通常是最重要的优化层级之一，因为 AVX2 在当前主流桌面和服务器 CPU 中广泛支持。

```
SkGraphics::Init()
  -> SkOpts::Init()
       -> 检测 CPU 特性
       -> 如果支持 HSW 指令集:
            SkOpts::Init_hsw()     <-- 本文件
                -> 替换 SkOpts 命名空间中的函数指针为 hsw:: 版本
       -> 如果支持 SKX 指令集:
            SkOpts::Init_skx()
                -> 在 HSW 基础上进一步替换为 AVX-512 版本
```

在 SkOpts 的分层优化体系中，HSW 优化覆盖了 SSE2 默认实现，而如果 CPU 还支持 AVX-512（SKX），则会进一步覆盖 HSW 的实现。

## 主要类与结构体

本文件不定义新的类或结构体。它在 `SkOpts` 命名空间内工作，操作的是该命名空间中预先声明的全局函数指针变量。

### 关键命名空间

- **`SkOpts`**: Skia 全局优化函数指针命名空间
- **`hsw`**（通过 `#define SK_OPTS_NS hsw` 定义）: 包含所有使用 AVX2 指令集编译的优化函数实现

## 公共 API 函数

### `SkOpts::Init_hsw()`

```cpp
void Init_hsw();
```

HSW/AVX2 优化的初始化函数。当 `SkOpts::Init()` 检测到 CPU 支持 HSW 指令集时调用此函数。它将以下函数指针更新为 AVX2 优化版本：

| 函数指针 | 说明 |
|---------|------|
| `raster_pipeline_lowp_stride` | 低精度管线每次迭代处理的像素步幅 |
| `raster_pipeline_highp_stride` | 高精度管线每次迭代处理的像素步幅 |
| `ops_highp[]` | 高精度管线所有阶段操作的函数指针数组 |
| `ops_lowp[]` | 低精度管线所有阶段操作的函数指针数组 |
| `just_return_highp` / `just_return_lowp` | 管线阶段返回函数 |
| `start_pipeline_highp` / `start_pipeline_lowp` | 管线启动入口函数 |

## 内部实现细节

### 宏展开注册机制

与所有 `SkOpts_*.cpp` 文件一致，本文件使用 X-宏（X-Macro）模式批量注册函数指针：

```cpp
#define M(st) ops_highp[(int)SkRasterPipelineOp::st] = (StageFn)SK_OPTS_NS::st;
    SK_RASTER_PIPELINE_OPS_ALL(M)
    just_return_highp = (StageFn)SK_OPTS_NS::just_return;
    start_pipeline_highp = SK_OPTS_NS::start_pipeline;
#undef M
```

高精度管线使用 `SK_RASTER_PIPELINE_OPS_ALL` 注册所有阶段，低精度管线使用 `SK_RASTER_PIPELINE_OPS_LOWP` 注册其支持的阶段子集。

### 编译配置

- 该文件在编译时使用 `-mavx2 -mfma -mbmi -mbmi2` 等编译标志，使编译器能够生成 AVX2 指令
- 整个文件被 `#if !defined(SK_ENABLE_OPTIMIZE_SIZE)` 包裹，在尺寸优化模式下不会编译
- `#define SK_OPTS_NS hsw` 让 `SkRasterPipeline_opts.h` 中的所有实现生成在 `hsw` 命名空间下

### SkRasterPipeline_opts.h 的复用

核心实现代码位于 `SkRasterPipeline_opts.h`，它是一个被多次包含的头文件。每次包含时，`SK_OPTS_NS` 宏的值不同（如 `sse2`、`hsw`、`skx`、`lasx`），从而在不同的命名空间中生成针对不同指令集的实现。编译器会根据当前的编译标志选择合适的内建函数和向量宽度。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `src/core/SkOpts.h` | 声明 SkOpts 命名空间及其全局函数指针 |
| `src/opts/SkRasterPipeline_opts.h` | 光栅化管线阶段的通用实现（在编译时根据 `SK_OPTS_NS` 特化） |
| `src/core/SkRasterPipelineOpList.h` | 管线阶段枚举宏 `SK_RASTER_PIPELINE_OPS_ALL` 和 `SK_RASTER_PIPELINE_OPS_LOWP` |
| AVX2/FMA 指令集 | 编译时需要目标平台支持 AVX2 |

## 设计模式与设计决策

### 运行时分发模式

SkOpts 采用的是经典的 **运行时 CPU 特性分发**（Runtime CPU Dispatch）模式：

1. **编译期多版本生成**: 同一套 `SkRasterPipeline_opts.h` 代码被分别以 SSE2、HSW、SKX 等编译标志编译，产生不同的优化版本
2. **运行时函数指针替换**: 根据 `cpuid` 检测到的 CPU 能力，选择性调用 `Init_hsw()` 等函数替换默认实现
3. **零开销抽象**: 一旦初始化完成，后续调用通过函数指针直接跳转到优化版本，没有额外的分支判断开销

### 渐进式覆盖设计

SkOpts 的初始化是 **渐进式** 的：先加载基线（SSE2），然后逐步用更高级的优化版本覆盖。这保证了即使覆盖过程中断（例如某个高级优化未编译），系统仍然有完整的可用实现。

### HSW 作为甜蜜点

在当前 x86 生态中，HSW/AVX2 被认为是一个 "甜蜜点"——绝大多数现代 x86 CPU 都支持，且相比 SSE2 有显著的性能提升。因此 `SkOpts_hsw.cpp` 是 x86 平台上最常被激活的优化文件。

## 性能考量

- **AVX2 256 位向量宽度**: 相比 SSE2 的 128 位，AVX2 将整数 SIMD 宽度翻倍至 256 位，理论上可提供 2 倍的数据吞吐量
- **步幅翻倍**: HSW 版本的 `raster_pipeline_lowp_stride` 和 `raster_pipeline_highp_stride` 通常是 SSE2 版本的 2 倍
- **FMA 融合乘加**: HSW 同时支持 FMA 指令集，允许浮点乘法和加法在单条指令中完成，减少延迟和指令数
- **AVX-SSE 转换惩罚**: 需要注意的是，混合使用 AVX 和传统 SSE 指令可能导致性能惩罚（vzeroupper 问题），SkRasterPipeline_opts.h 的实现需要避免这种情况
- **尺寸与性能权衡**: 通过 `SK_ENABLE_OPTIMIZE_SIZE` 可以关闭 HSW 优化以减小二进制体积，适用于对体积敏感的嵌入式场景

## 相关文件

- `src/opts/SkOpts_lasx.cpp` - 龙芯 LASX 架构的类似优化初始化
- `src/opts/SkOpts_skx.cpp` - Intel Skylake-X（AVX-512）优化初始化
- `src/opts/SkRasterPipeline_opts.h` - 光栅化管线阶段的实际实现代码
- `src/core/SkOpts.h` - SkOpts 命名空间声明和文档
- `src/core/SkOpts.cpp` - SkOpts 默认实现与 Init() 入口
- `src/core/SkRasterPipelineOpList.h` - 管线阶段枚举宏定义
- `src/core/SkCpu.h` / `src/core/SkCpu.cpp` - CPU 特性检测
