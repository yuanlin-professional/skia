# SkOpts_lasx

> 源文件: `src/opts/SkOpts_lasx.cpp`

## 概述

`SkOpts_lasx.cpp` 是 Skia 图形库中针对龙芯（LoongArch）LASX（Loongson Advanced SIMD Extension）指令集的光栅化管线优化初始化文件。该文件负责在运行时检测到 LASX 指令集支持时，将光栅化管线（Raster Pipeline）的各阶段函数指针替换为利用 LASX 向量化指令优化后的实现版本。

LASX 是龙芯架构的高级 SIMD 扩展指令集，提供 256 位宽的向量寄存器和操作，类似于 x86 架构上的 AVX2 指令集。通过使用 LASX 优化的管线阶段，Skia 能够在龙芯处理器上显著提升图形渲染性能。

## 架构位置

该文件位于 Skia 的 `src/opts/` 目录下，属于 **SkOpts 运行时优化分发机制** 的一部分。其在整个架构中的位置如下：

```
SkGraphics::Init()
  -> SkOpts::Init()
       -> SkOpts::Init_lasx()     <-- 本文件
            -> 替换 SkOpts 命名空间中的函数指针
```

`SkOpts` 是 Skia 的一种运行时多态优化机制：在编译期生成多个不同 CPU 指令集优化版本的同一函数，然后在程序启动时根据实际 CPU 能力选择最佳版本。本文件是 LASX 架构特定的初始化入口。

## 主要类与结构体

本文件不定义新的类或结构体。它工作在 `SkOpts` 命名空间内，操作的是该命名空间中预先声明的全局函数指针变量。

### 关键命名空间

- **`SkOpts`**: Skia 优化函数指针的命名空间，包含光栅化管线各阶段的函数指针。
- **`lasx`**（通过 `SK_OPTS_NS` 宏定义）: 包含所有使用 LASX 指令集编译的优化函数实现。

## 公共 API 函数

### `SkOpts::Init_lasx()`

```cpp
void Init_lasx();
```

LASX 优化的初始化函数。该函数在运行时被 `SkOpts::Init()` 调用（当检测到 CPU 支持 LASX 指令集时），负责将以下函数指针更新为 LASX 优化版本：

- **`raster_pipeline_lowp_stride`**: 低精度管线每次处理的像素步幅
- **`raster_pipeline_highp_stride`**: 高精度管线每次处理的像素步幅
- **`ops_highp[]`**: 高精度管线所有阶段操作的函数指针数组（通过 `SK_RASTER_PIPELINE_OPS_ALL` 宏展开）
- **`ops_lowp[]`**: 低精度管线所有阶段操作的函数指针数组（通过 `SK_RASTER_PIPELINE_OPS_LOWP` 宏展开）
- **`just_return_highp` / `just_return_lowp`**: 管线返回函数
- **`start_pipeline_highp` / `start_pipeline_lowp`**: 管线启动函数

## 内部实现细节

### 宏展开机制

文件中使用了两个关键的宏展开模式来批量注册函数指针：

```cpp
#define M(st) ops_highp[(int)SkRasterPipelineOp::st] = (StageFn)SK_OPTS_NS::st;
    SK_RASTER_PIPELINE_OPS_ALL(M)
#undef M
```

`SK_RASTER_PIPELINE_OPS_ALL` 和 `SK_RASTER_PIPELINE_OPS_LOWP` 是在 `SkRasterPipelineOpList.h` 中定义的 X-宏（X-Macro），它们会展开为所有管线阶段的枚举值列表。通过将宏 `M` 传入，每个阶段都会自动生成一条函数指针赋值语句。

### 编译条件

整个文件内容被 `#if !defined(SK_ENABLE_OPTIMIZE_SIZE)` 包裹，这意味着当 Skia 以尺寸优化模式编译时（例如针对嵌入式设备），LASX 优化将被完全排除以减小二进制体积。

### SK_OPTS_NS 命名空间别名

`#define SK_OPTS_NS lasx` 将命名空间别名设置为 `lasx`，随后 `#include "src/opts/SkRasterPipeline_opts.h"` 会在该命名空间下生成所有使用 LASX 内建函数编译的管线阶段实现。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `src/core/SkOpts.h` | 声明 SkOpts 命名空间及其函数指针变量 |
| `src/opts/SkRasterPipeline_opts.h` | 光栅化管线各阶段的模板化实现（在 `lasx` 命名空间中编译） |
| `SkRasterPipelineOpList.h` | 定义 `SK_RASTER_PIPELINE_OPS_ALL` 和 `SK_RASTER_PIPELINE_OPS_LOWP` 宏 |
| LASX 指令集 | 编译时需要龙芯 LASX 指令集支持 |

## 设计模式与设计决策

### 运行时分发模式（Runtime Dispatch Pattern）

本文件是 Skia **运行时 CPU 特性分发** 设计模式的典型实现。该模式的核心思想是：

1. 在编译期，同一套管线阶段代码通过不同的编译标志生成多个优化版本
2. 在运行时，检测 CPU 实际支持的指令集，然后调用对应的 `Init_xxx()` 函数替换默认的函数指针

这种模式允许单一二进制文件同时支持多种 CPU 配置，无需为每种 CPU 单独构建。

### X-宏批量注册

使用 X-宏模式（`SK_RASTER_PIPELINE_OPS_ALL(M)`）确保所有管线阶段都被注册，避免遗漏。当新增管线阶段时，只需修改宏定义列表，所有架构的初始化代码都会自动更新。

### 高精度/低精度双管线

Skia 光栅化管线区分 `highp`（高精度，使用浮点运算）和 `lowp`（低精度，使用定点运算）两种模式。低精度模式在满足质量要求的前提下可以获得更高的吞吐量，因此两者都有独立的 LASX 优化版本。

## 性能考量

- **LASX 256 位向量宽度**: LASX 提供 256 位宽的向量寄存器，理论上可以比 128 位的 LSX 指令集提供 2 倍的数据并行度
- **步幅（stride）优化**: `raster_pipeline_lowp_stride` 和 `raster_pipeline_highp_stride` 决定了每次循环迭代处理的像素数量，LASX 版本通常设置更大的步幅以充分利用宽向量寄存器
- **尺寸优化权衡**: 通过 `SK_ENABLE_OPTIMIZE_SIZE` 宏可以在性能和二进制体积之间做出权衡

## 相关文件

- `src/opts/SkOpts_hsw.cpp` - 类似的 HSW（Haswell/AVX2）优化初始化文件
- `src/opts/SkOpts_skx.cpp` - SKX（Skylake-X/AVX-512）优化初始化文件
- `src/opts/SkRasterPipeline_opts.h` - 光栅化管线阶段的实际实现
- `src/core/SkOpts.h` - SkOpts 命名空间的声明
- `src/core/SkOpts.cpp` - SkOpts 默认实现和 Init() 入口
- `src/core/SkRasterPipelineOpList.h` - 管线阶段枚举宏定义
