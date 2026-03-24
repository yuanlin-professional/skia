# DawnGraphicsPipeline

> 源文件:
> - `src/gpu/graphite/dawn/DawnGraphicsPipeline.h`
> - `src/gpu/graphite/dawn/DawnGraphicsPipeline.cpp`

## 概述

`DawnGraphicsPipeline` 是 Skia Graphite 渲染引擎 Dawn (WebGPU) 后端的图形管线实现。它继承自 `GraphicsPipeline` 基类，封装了 `wgpu::RenderPipeline` 对象的创建、异步编译和生命周期管理。该类负责将 Skia 的着色器描述、混合状态、深度模板状态、顶点布局等转换为 Dawn/WebGPU 的管线描述符，并支持同步和异步两种管线创建模式。

## 架构位置

```
Graphite 渲染引擎
  └── GraphicsPipeline (平台无关基类)
        └── DawnGraphicsPipeline (Dawn/WebGPU 后端)
              ├── AsyncPipelineCreation (异步管线创建状态)
              ├── BindGroupLayouts (绑定组布局数组)
              └── ImmutableSamplers (不可变采样器引用)
```

管线由 `DawnSharedContext::createGraphicsPipeline()` 委托创建，着色器代码由 `ShaderInfo` 生成 SkSL 后通过 `SkSLToWGSL` 转换为 WGSL。

## 主要类与结构体

### `DawnGraphicsPipeline`
- 继承自 `GraphicsPipeline`，是 Dawn 后端的渲染管线封装。
- 定义了关键的绑定组和缓冲区索引常量：
  - `kUniformBufferBindGroupIndex = 0`：统一缓冲区绑定组索引。
  - `kTextureBindGroupIndex = 1`：纹理绑定组索引。
  - `kBindGroupCount = 2`：总绑定组数。
  - `kIntrinsicUniformBufferIndex = 0`、`kCombinedUniformIndex = 1`、`kGradientBufferIndex = 2`：统一缓冲区内的绑定点索引。
  - `kNumUniformBuffers = 3`：统一缓冲区数量。
  - `kIntrinsicUniformSize = 32`：内部常量大小（字节）。
  - `kStaticDataBufferIndex = 0`、`kAppendDataBufferIndex = 1`：顶点缓冲区索引。

### `AsyncPipelineCreationBase`
- 异步管线创建的基础数据结构。
- 包含 `wgpu::RenderPipeline`、错误消息、原子完成标志。
- 在 `SK_HISTOGRAMS_ENABLED` 模式下记录创建开始时间、是否为预编译、是否异步，用于性能直方图统计。

### `DawnGraphicsPipeline::AsyncPipelineCreation`
- 继承自 `AsyncPipelineCreationBase`。
- 在非 Emscripten 环境下额外持有 `wgpu::Future`，用于异步管线创建的等待机制。
- 在 Emscripten 环境下不使用异步编译。

## 公共 API 函数

### 工厂方法
- **`static Make(const DawnSharedContext*, const RuntimeEffectDictionary*, const UniqueKey&, const GraphicsPipelineDesc&, const RenderPassDesc&, SkEnumBitMask<PipelineCreationFlags>, uint32_t) -> sk_sp<DawnGraphicsPipeline>`**：创建图形管线的核心方法。流程包括：
  1. 从 `ShaderInfo` 生成 SkSL 着色器代码。
  2. 通过 `SkSLToWGSL` 将 SkSL 转换为 WGSL。
  3. 编译 WGSL 为 `wgpu::ShaderModule`。
  4. 配置混合、深度模板、顶点、图元等管线状态。
  5. 构建绑定组布局和管线布局。
  6. 根据条件选择同步或异步创建管线。

### 状态查询
- **`dawnRenderPipeline()`**：返回底层 `wgpu::RenderPipeline`。若管线正在异步创建中，会阻塞等待完成。
- **`didAsyncCompilationFail()`**：检查异步编译是否失败，返回错误消息。
- **`stencilReferenceValue()`**：返回模板测试参考值。
- **`primitiveType()`**：返回图元类型。
- **`dawnGroupLayouts()`**：返回绑定组布局数组。
- **`immutableSampler(int32_t index)`**：返回指定索引的不可变采样器（如果有）。

## 内部实现细节

### 着色器编译流程
1. `ShaderInfo::Make()` 根据渲染步骤和绘制参数生成 SkSL 着色器代码。
2. `SkSLToWGSL()` 将 SkSL 转换为 WGSL 代码。
3. `DawnCompileWGSLShaderModule()` 将 WGSL 编译为 `wgpu::ShaderModule`。
4. 如果没有片段着色器（仅写入深度缓冲区），使用 `DawnSharedContext` 提供的 noop 片段着色器。

### 顶点属性转换
`attribute_type_to_dawn()` 将 Skia 的 `VertexAttribType` 映射到 `wgpu::VertexFormat`。使用两个顶点缓冲区：
- **静态数据缓冲区**（索引 0）：包含渲染步骤的静态顶点属性，步进模式为 `Vertex`。
- **追加数据缓冲区**（索引 1）：包含渲染步骤的追加属性，步进模式根据 `appendsVertices()` 为 `Vertex` 或 `Instance`。

### 混合状态
混合系数转换支持双源混合（Dual Source Blending），通过 `caps.shaderCaps()->fDualSourceBlendingSupport` 判断。在 Emscripten 环境下，双源混合系数回退为零。Alpha 通道的混合系数需要特殊处理：将源颜色系数转换为对应的 Alpha 系数。

### 绑定组布局构建
- **绑定组 0**（统一缓冲区）：复用 `DawnSharedContext` 预创建的布局。
- **绑定组 1**（纹理+采样器）：
  - 单纹理+动态采样器的常见情况复用共享布局。
  - 多纹理或使用不可变采样器时，动态创建自定义布局。
  - 不可变采样器通过 `wgpu::StaticSamplerBindingLayout` 链式描述符绑定。

### 异步管线创建
- 非预编译且 `caps.useAsyncPipelineCreation()` 为真时使用 `CreateRenderPipelineAsync`。
- 异步回调中设置完成标志和结果。
- `dawnRenderPipeline()` 在管线未完成时通过 `instance.WaitAny()` 阻塞等待。
- 预编译始终使用同步创建。
- Emscripten 环境不支持异步创建。

### MSAA Load Resolve 支持
在非 Emscripten 环境下，如果渲染通道需要从解析纹理加载 MSAA 数据，管线需要启用 `DawnLoadResolveTexture` 功能扩展。

### 性能直方图
在 `SK_HISTOGRAMS_ENABLED` 模式下，管线创建时间按三种类别记录：
- `Graphite.PipelineCreationTimes.Precompile`
- `Graphite.PipelineCreationTimes.Asynchronous`
- `Graphite.PipelineCreationTimes.Synchronous`

## 依赖关系

- **基类**: `GraphicsPipeline`
- **Dawn 后端类**: `DawnSharedContext`、`DawnCaps`、`DawnSampler`、`DawnResourceProvider`、`DawnErrorChecker`
- **Graphite 核心**: `ShaderInfo`、`GraphicsPipelineDesc`、`RenderPassDesc`、`RendererProvider`、`Attribute`、`ContextUtils`
- **着色器编译**: `SkSLToBackend`（SkSL -> WGSL 转换）、`SkSLCompiler`
- **WebGPU API**: `wgpu::Device`、`wgpu::RenderPipeline`、`wgpu::ShaderModule`、`wgpu::BindGroupLayout` 等

## 设计模式与设计决策

1. **异步创建模式**：支持同步和异步两种管线创建路径。异步创建通过 `wgpu::Future` 和 `WaitAny` 实现延迟等待，允许管线在后台编译的同时继续其他工作。

2. **延迟阻塞**：`dawnRenderPipeline()` 实现了"尽量晚等待"的策略，只在真正需要使用管线时才阻塞等待异步编译完成。

3. **不可变采样器管理**：通过持有 `sk_sp<DawnSampler>` 引用确保不可变采样器在管线生命周期内保持有效，避免悬挂引用。

4. **平台适配**：广泛使用 `__EMSCRIPTEN__` 预处理宏适配 WebAssembly 和原生 Dawn 环境的 API 差异。

5. **常量定义集中化**：所有绑定组索引和缓冲区索引以 `inline static constexpr` 定义在类头部，供 `DawnResourceProvider` 和 `DawnCommandBuffer` 等类引用。

## 性能考量

- **异步管线编译**：避免管线创建阻塞主线程，特别在首次渲染时减少卡顿。
- **预编译支持**：预编译路径使用同步创建，在后台线程提前准备管线。
- **绑定组布局复用**：常见的单纹理场景复用共享布局，减少布局创建开销。
- **着色器精度控制**：`fForceHighPrecision` 根据设备能力决定是否强制高精度，在低端设备上可能影响性能。
- **管线创建时间统计**：内置直方图记录机制，可用于分析和优化管线创建瓶颈。

## 相关文件

- `src/gpu/graphite/GraphicsPipeline.h` - 基类定义
- `src/gpu/graphite/dawn/DawnSharedContext.h` - Dawn 共享上下文
- `src/gpu/graphite/dawn/DawnCaps.h` - Dawn 能力查询
- `src/gpu/graphite/dawn/DawnSampler.h` - Dawn 采样器
- `src/gpu/graphite/dawn/DawnErrorChecker.h` - 错误检查器
- `src/gpu/graphite/dawn/DawnAsyncWait.h` - 异步等待辅助
- `src/gpu/graphite/ShaderInfo.h` - 着色器信息生成
- `src/gpu/graphite/GraphicsPipelineDesc.h` - 管线描述
- `src/gpu/graphite/RenderPassDesc.h` - 渲染通道描述
- `src/gpu/SkSLToBackend.h` - SkSL 到 WGSL 转换
