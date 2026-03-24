# SkOpts_skx

> 源文件: `src/opts/SkOpts_skx.cpp`

## 概述

`SkOpts_skx.cpp` 是 Skia 优化系统中针对 Intel SKX（Skylake-X / Skylake Server）微架构的光栅化管线（Raster Pipeline）初始化模块。它将 SKX 指令集（包括 AVX-512 等高级 SIMD 指令）优化过的光栅化管线阶段函数注册到全局函数指针表中，使 Skia 在检测到 SKX 级别 CPU 时能够自动使用这些更高效的实现。

该文件仅在未定义 `SK_ENABLE_OPTIMIZE_SIZE` 时编译，因为光栅化管线的多指令集版本会显著增加二进制体积。

## 架构位置

在 Skia 的运行时优化分发架构中，`SkOpts_skx.cpp` 的位置如下：

```
SkOpts::Init()  (运行时 CPU 特性检测)
    |
    +-- Init_skx()  <-- 本文件提供
    +-- Init_hsw()
    +-- Init_ssse3()
    +-- Init_avx()
    |
SkOpts 全局函数指针表 (SkOpts.h)
    |
SkRasterPipeline (光栅化管线执行引擎)
```

当 Skia 在运行时检测到 CPU 支持 SKX 指令集时，会调用 `SkOpts::Init_skx()` 将光栅化管线的各阶段函数指针替换为 SKX 优化版本。

## 主要类与结构体

该文件不定义新的类或结构体。它在 `SkOpts` 命名空间中定义了一个初始化函数。

## 公共 API 函数

### `SkOpts::Init_skx()`

```cpp
namespace SkOpts {
    void Init_skx();
}
```

- **功能**: 将光栅化管线的全局函数指针初始化为 SKX 优化版本。
- **调用时机**: 在 Skia 初始化阶段，由 `SkOpts::Init()` 在检测到 CPU 支持 SKX 指令集后调用。
- **操作内容**:
  1. 设置 `raster_pipeline_lowp_stride` 和 `raster_pipeline_highp_stride`（低精度和高精度管线的向量宽度/步幅）。
  2. 通过 `SK_RASTER_PIPELINE_OPS_ALL` 宏，将所有高精度（highp）管线阶段的函数指针设置为 `skx` 命名空间中的实现。
  3. 通过 `SK_RASTER_PIPELINE_OPS_LOWP` 宏，将所有低精度（lowp）管线阶段的函数指针设置为 `skx::lowp` 命名空间中的实现。
  4. 设置 `just_return_highp`、`start_pipeline_highp`、`just_return_lowp`、`start_pipeline_lowp` 等管线控制函数。

## 内部实现细节

### 命名空间硬编码

文件开头通过 `#define SK_OPTS_NS skx` 直接硬编码命名空间为 `skx`，而不是通过 `SkOpts_SetTarget.h` 机制设置。这是因为本文件本身就是专门为 SKX 指令集编译的编译单元，编译器选项（如 `-march=skylake-avx512`）应在构建系统层面指定。

### 宏展开机制

```cpp
#define M(st) ops_highp[(int)SkRasterPipelineOp::st] = (StageFn)SK_OPTS_NS::st;
    SK_RASTER_PIPELINE_OPS_ALL(M)
```

使用 X-Macro 模式，`SK_RASTER_PIPELINE_OPS_ALL` 宏包含了所有光栅化管线阶段的名称列表，通过宏 `M` 的展开，逐一将每个阶段函数指针设置为 `skx` 命名空间中的对应函数。

### 高精度/低精度管线

光栅化管线分为两种精度模式：
- **highp（高精度）**: 使用 32 位浮点数处理每个颜色通道，精度高但较慢。
- **lowp（低精度）**: 使用 8 位或 16 位整数处理颜色，精度稍低但速度更快。

SKX 的向量宽度更大（AVX-512 提供 512 位寄存器），因此 `stride` 值更大，每次迭代能处理更多像素。

## 依赖关系

- `src/core/SkOpts.h` - 全局函数指针表和 `SkRasterPipelineOp` 枚举
- `src/opts/SkRasterPipeline_opts.h` - 光栅化管线各阶段的实际优化实现（在 `skx` 命名空间中编译）

## 设计模式与设计决策

### 运行时分发
遵循 Skia 的 SkOpts 运行时分发模式：编译多个指令集版本，在启动时根据 CPU 能力选择最优版本写入全局函数指针表。

### 条件编译
通过 `SK_ENABLE_OPTIMIZE_SIZE` 宏控制编译。在追求最小二进制体积的场景下，可跳过 SKX 优化版本的编译。

## 性能考量

- SKX 指令集利用 AVX-512 的 512 位向量寄存器，单次操作可处理的像素数量是 AVX2（256 位）的两倍。
- `stride` 值的增大意味着光栅化管线的主循环迭代次数减半，对大面积填充操作有显著加速效果。
- 函数指针分发只在初始化时发生一次，运行时的间接调用开销可忽略不计。

## 相关文件

- `src/core/SkOpts.h` - 全局优化函数指针声明
- `src/core/SkOpts.cpp` - `SkOpts::Init()` 初始化入口
- `src/opts/SkRasterPipeline_opts.h` - 光栅化管线阶段的模板化实现
- `src/opts/SkOpts_SetTarget.h` - 编译目标设置（本文件未直接使用，但架构上相关）
- `src/opts/SkOpts_RestoreTarget.h` - 编译目标恢复
