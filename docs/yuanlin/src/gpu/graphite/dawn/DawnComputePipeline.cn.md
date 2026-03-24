# DawnComputePipeline

> 源文件:
> - `src/gpu/graphite/dawn/DawnComputePipeline.h`
> - `src/gpu/graphite/dawn/DawnComputePipeline.cpp`

## 概述

`DawnComputePipeline` 是 Skia Graphite 渲染引擎 Dawn (WebGPU) 后端的计算管线实现。它继承自 `ComputePipeline` 基类，封装了 `wgpu::ComputePipeline` 和对应的 `wgpu::BindGroupLayout` 的创建与管理。计算管线用于在 GPU 上执行通用计算任务，着色器代码支持原生 WGSL 和从 SkSL 编译两种来源。

## 架构位置

```
Graphite 渲染引擎
  └── ComputePipeline (平台无关基类)
        └── DawnComputePipeline (Dawn/WebGPU 后端)
              ├── wgpu::ComputePipeline (底层计算管线)
              └── wgpu::BindGroupLayout (资源绑定布局)
```

计算管线由 `DawnResourceProvider::createComputePipeline()` 创建。

## 主要类与结构体

### `DawnComputePipeline`
- 继承自 `ComputePipeline`，封装 Dawn 后端的计算管线。
- 持有 `fPipeline`（`wgpu::ComputePipeline`）和 `fGroupLayout`（`wgpu::BindGroupLayout`）。
- 所有计算资源分配到单个绑定组（索引 0）。

### `ShaderInfo`（匿名命名空间内部结构体）
- 包含编译后的着色器模块 `fModule` 和入口点名称 `fEntryPoint`。
- `isValid()` 检查着色器模块是否有效。

## 公共 API 函数

### 工厂方法
- **`static Make(const DawnSharedContext*, const ComputePipelineDesc&) -> sk_sp<DawnComputePipeline>`**：创建计算管线。流程：
  1. 编译着色器模块（原生 WGSL 或 SkSL -> WGSL）。
  2. 根据 `ComputeStep` 的资源描述构建绑定组布局。
  3. 创建管线布局和计算管线。
  4. 使用 `DawnErrorChecker` 检查创建过程中的错误。

### 访问器
- **`dawnComputePipeline()`**：返回底层 `wgpu::ComputePipeline` 引用。
- **`dawnGroupLayout()`**：返回绑定组布局引用。

## 内部实现细节

### 着色器编译
`compile_shader_module()` 支持两种着色器来源：
1. **原生 WGSL**：如果 `ComputeStep::supportsNativeShader()` 为真，直接获取 WGSL 源代码并编译。入口点使用步骤提供的名称。
2. **SkSL 编译**：调用 `BuildComputeSkSL()` 构建 SkSL 代码，通过 `SkSLToWGSL()` 转换为 WGSL，然后编译。入口点固定为 `"main"`。

### 资源绑定布局构建
根据 `ComputeStep::resources()` 列表构建绑定组布局条目：
- **`kUniformBuffer`** -> `wgpu::BufferBindingType::Uniform`
- **`kStorageBuffer` / `kIndirectBuffer`** -> `wgpu::BufferBindingType::Storage`
- **`kReadOnlyStorageBuffer`** -> `wgpu::BufferBindingType::ReadOnlyStorage`
- **`kReadOnlyTexture`** -> 2D 浮点纹理
- **`kWriteOnlyStorageTexture`** -> 2D 只写存储纹理，格式由 `getDefaultStorageTextureInfo()` 决定
- **`kSampledTexture`** -> 采样器 + 纹理（占用 2 个绑定点）

资源按声明顺序分配递增的绑定索引，全部位于绑定组 0。

### 错误检查
使用 `DawnErrorChecker` 在管线创建前后进行错误作用域检查。如果检测到错误则返回空指针。

## 依赖关系

- **基类**: `ComputePipeline`
- **Dawn 后端类**: `DawnSharedContext`、`DawnCaps`、`DawnErrorChecker`
- **Graphite 核心**: `ComputePipelineDesc`、`ComputeStep`、`Caps`、`ContextUtils`
- **着色器编译**: `SkSLToBackend`（SkSL -> WGSL）、`DawnGraphiteUtils`（WGSL 编译）
- **WebGPU API**: `wgpu::ComputePipeline`、`wgpu::BindGroupLayout`、`wgpu::PipelineLayout`

## 设计模式与设计决策

1. **工厂方法模式**：通过静态 `Make()` 函数创建实例，封装复杂的构建流程。
2. **单绑定组设计**：所有计算资源统一放在绑定组 0，简化了绑定管理。这与图形管线使用多绑定组的设计不同。
3. **双着色器路径**：支持原生 WGSL 和 SkSL 编译两种路径，前者适合手写优化的计算着色器，后者适合自动生成。
4. **错误检查包裹**：条件性使用 `DawnErrorChecker` 包裹管线创建调用，在开发和调试时捕获 Dawn 验证错误。

## 性能考量

- **同步创建**：与图形管线不同，计算管线始终使用同步创建，不支持异步编译。
- **着色器精度**：根据设备是否支持半精度决定 `fForceHighPrecision` 设置，在精度和性能之间权衡。
- **资源绑定计数优化**：采样纹理需要 2 个绑定点（采样器 + 纹理），预计算总数以优化 `reserve()` 调用。

## 相关文件

- `src/gpu/graphite/ComputePipeline.h` - 基类定义
- `src/gpu/graphite/ComputePipelineDesc.h` - 计算管线描述
- `src/gpu/graphite/dawn/DawnSharedContext.h` - Dawn 共享上下文
- `src/gpu/graphite/dawn/DawnErrorChecker.h` - 错误检查器
- `src/gpu/graphite/dawn/DawnGraphiteUtils.h` - Dawn WGSL 编译工具
- `src/gpu/SkSLToBackend.h` - SkSL 到 WGSL 转换
- `src/gpu/graphite/ContextUtils.h` - BuildComputeSkSL
