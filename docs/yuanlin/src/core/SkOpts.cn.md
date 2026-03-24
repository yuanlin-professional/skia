# SkOpts

> 源文件: src/core/SkOpts.h, src/core/SkOpts.cpp

## 概述

`SkOpts` (Skia Optimizations) 是 Skia 的运行时优化机制，提供了一套基于 CPU 特性的函数动态选择系统。该模块允许 Skia 在编译时包含多个函数实现版本（针对不同的 CPU 指令集优化），并在运行时根据检测到的 CPU 特性动态选择最优实现。这种机制使 Skia 能够在保持广泛兼容性的同时，充分利用现代 CPU 的高级指令集（如 AVX2、AVX512 等）来获得最佳性能。

该模块主要用于优化 `SkRasterPipeline`（光栅化管线）的执行效率，通过 SIMD 指令集加速图像处理操作。

## 架构位置

`SkOpts` 位于 Skia 核心层的底层基础设施中，是性能优化的关键组件：

- **所属模块**: `src/core/` - Skia 核心实现
- **依赖层级**: 最底层的性能优化基础设施
- **调用时机**: 通过 `SkGraphics::Init()` 在 Skia 初始化阶段调用
- **优化范围**: 主要针对 `SkRasterPipeline` 的高精度和低精度操作

## 主要类与结构体

### SkOpts 命名空间

SkOpts 是一个命名空间，不是类，包含全局函数指针和初始化函数。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `ops_highp` | `StageFn[]` | 高精度光栅化管线操作函数指针数组 |
| `ops_lowp` | `StageFn[]` | 低精度光栅化管线操作函数指针数组 |
| `just_return_highp` | `StageFn` | 高精度管线空操作函数指针 |
| `just_return_lowp` | `StageFn` | 低精度管线空操作函数指针 |
| `start_pipeline_highp` | 函数指针 | 启动高精度管线的函数指针 |
| `start_pipeline_lowp` | 函数指针 | 启动低精度管线的函数指针 |
| `raster_pipeline_lowp_stride` | `size_t` | 低精度管线的向量步幅 |
| `raster_pipeline_highp_stride` | `size_t` | 高精度管线的向量步幅 |

## 公共 API 函数

### void Init()

```cpp
void Init()
```

**功能**: 初始化 SkOpts 系统，根据当前 CPU 特性替换函数指针。

**特性**:
- 线程安全且幂等（可多次调用）
- 由 `SkGraphics::Init()` 自动调用
- 使用静态变量确保只初始化一次

**工作流程**:
1. 检测 CPU 支持的指令集（通过 `SkCpu::Supports()`）
2. 根据支持的指令集调用相应的 `Init_xxx()` 函数
3. 替换全局函数指针为优化版本

## 内部实现细节

### 编译时机制

1. **默认实现**: `SkOpts.cpp` 使用基础指令集编译（如 SSE2），生成默认实现
2. **特化实现**: `src/opts/` 下的 `.cpp` 文件使用特定编译标志编译：
   - `SkOpts_hsw.cpp`: Haswell (AVX2) 优化
   - `SkOpts_skx.cpp`: Skylake-X (AVX512) 优化
   - `SkOpts_lasx.cpp`: LoongArch LASX 优化

### 运行时选择逻辑

```cpp
static bool init() {
#if defined(SK_CPU_X86)
    #if SK_CPU_SSE_LEVEL < SK_CPU_SSE_LEVEL_AVX2
        if (SkCpu::Supports(SkCpu::HSW)) { Init_hsw(); }
    #endif
    #if defined(SK_ENABLE_AVX512_OPTS)
        if (SkCpu::Supports(SkCpu::SKX)) { Init_skx(); }
    #endif
#elif defined(SK_CPU_LOONGARCH)
    if (SkCpu::Supports(SkCpu::LOONGARCH_ASX)) { Init_lasx(); }
#endif
    return true;
}
```

### CPU 架构支持

| 架构 | 基础指令集 | 高级优化 | 条件编译宏 |
|------|-----------|---------|-----------|
| x86/x86-64 | SSE2 | AVX2 (HSW), AVX512 (SKX) | `SK_CPU_X86` |
| LoongArch | LSX | LASX | `SK_CPU_LOONGARCH` |
| ARM | NEON | (未在此代码显示) | `SK_CPU_ARM` |

### 优化禁用机制

当定义 `SK_ENABLE_OPTIMIZE_SIZE` 时，所有 `Init_xxx()` 函数调用被省略，仅使用默认实现以减小代码体积。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `src/core/SkCpu.h` | CPU 特性检测 |
| `src/core/SkOptsTargets.h` | 定义优化目标常量 |
| `src/core/SkRasterPipelineOpList.h` | 光栅化管线操作列表 |
| `src/opts/SkOpts_SetTarget.h` | 设置编译目标宏 |
| `src/opts/SkRasterPipeline_opts.h` | 光栅化管线优化实现 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `SkGraphics` | 初始化时调用 `SkOpts::Init()` |
| `SkRasterPipeline` | 使用 `ops_highp/lowp` 和相关函数指针 |
| 所有绘图操作 | 间接依赖（通过 `SkRasterPipeline`） |

## 设计模式与设计决策

### 1. 函数指针表模式

通过函数指针数组实现运行时多态，避免虚函数调用开销：

```cpp
StageFn ops_highp[kNumRasterPipelineHighpOps];
```

**优势**:
- 零运行时开销（相比虚函数）
- 支持全局替换
- 编译时类型安全

### 2. 静态初始化单例模式

```cpp
void Init() {
    [[maybe_unused]] static bool gInitialized = init();
}
```

**特性**:
- 线程安全（C++11 保证静态局部变量初始化的线程安全）
- 幂等性（多次调用无副作用）
- 延迟初始化

### 3. 命名空间隔离策略

不同优化版本使用独立命名空间（`sse2::`, `hsw::`, `skx::`），避免符号冲突。

### 4. 渐进式优化

CPU 指令集是超集关系，支持多级初始化：
- 基础 CPU 只初始化默认实现
- 支持 AVX2 的 CPU 会替换为 AVX2 实现
- 支持 AVX512 的 CPU 会再次替换为 AVX512 实现

## 性能考量

### 1. 指令集加速

- **SSE2**: 基础 128 位 SIMD，4 路并行浮点运算
- **AVX2**: 256 位 SIMD，8 路并行浮点运算（理论 2 倍性能）
- **AVX512**: 512 位 SIMD，16 路并行浮点运算（理论 4 倍性能）

### 2. 内存对齐

`raster_pipeline_lowp_stride` 和 `raster_pipeline_highp_stride` 确保数据按 SIMD 宽度对齐，避免非对齐访问的性能损失。

### 3. 编译优化

每个特化版本使用特定编译标志（如 `-mavx2`, `-mavx512f`），使编译器能够：
- 生成特定 CPU 指令
- 进行向量化优化
- 利用新指令的低延迟特性

### 4. 代码体积权衡

优化会增加代码体积（多个版本并存），通过 `SK_ENABLE_OPTIMIZE_SIZE` 提供关闭选项。

### 5. 热路径优化

光栅化管线是 Skia 的最热路径，SkOpts 的优化直接影响整体性能：
- 图像混合运算
- 颜色空间转换
- 滤镜效果
- 文本渲染

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkCpu.h` | CPU 特性检测接口 |
| `src/core/SkOptsTargets.h` | 优化目标定义 |
| `src/core/SkRasterPipeline.h` | 光栅化管线主接口 |
| `src/opts/SkOpts_hsw.cpp` | AVX2 (Haswell) 优化实现 |
| `src/opts/SkOpts_skx.cpp` | AVX512 (Skylake-X) 优化实现 |
| `src/opts/SkOpts_lasx.cpp` | LoongArch LASX 优化实现 |
| `src/opts/SkRasterPipeline_opts.h` | 管线操作的实际实现 |
| `src/opts/SkOpts_SetTarget.h` | 设置编译目标的宏定义 |
| `src/opts/SkOpts_RestoreTarget.h` | 恢复编译目标的宏定义 |
| `include/core/SkGraphics.h` | Skia 全局初始化接口 |
