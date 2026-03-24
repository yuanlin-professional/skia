# GrMtlPipelineState

> 源文件
> - src/gpu/ganesh/mtl/GrMtlPipelineState.h
> - src/gpu/ganesh/mtl/GrMtlPipelineState.mm

## 概述

`GrMtlPipelineState` 封装 Metal 渲染管线状态对象（`MTLRenderPipelineState`）及相关 Ganesh 元数据，是 Metal 后端渲染执行的核心类。该类管理 Uniform 缓冲区、纹理采样器绑定、深度模板状态、混合常量设置，以及渲染目标状态跟踪。在每次绘制调用前，通过 `setData()`、`setTextures()` 和 `setDrawState()` 配置管线参数，然后调用 `bindTextures()` 和 `bindUniforms()` 绑定资源到编码器，完成 GPU 绘制准备。

## 架构位置

- **模块层级**：`src/gpu/ganesh/mtl/` - Ganesh Metal 后端
- **作用**：渲染管线状态封装和参数管理
- **使用者**：`GrMtlOpsRenderPass`（渲染通道）
- **生命周期**：由 `GrMtlPipelineStateBuilder` 创建，由 `GrMtlResourceProvider` 缓存

## 主要类与结构体

### GrMtlPipelineState

```cpp
class GrMtlPipelineState
```

**核心数据成员**：
- `sk_sp<GrMtlRenderPipeline> fPipeline` - Metal 渲染管线对象
- `GrMtlPipelineStateDataManager fDataManager` - Uniform 数据管理器
- `std::unique_ptr<GrGeometryProcessor::ProgramImpl> fGeomProc` - 几何处理器实现
- `std::unique_ptr<GrXferProcessor::ProgramImpl> fXferProc` - 传输处理器实现
- `std::vector<std::unique_ptr<GrFragmentProcessor::ProgramImpl>> fFPImpls` - 片段处理器实现数组
- `SkSTArray<4, SamplerBindings> fSamplerBindings` - 采样器绑定数组
- `RenderTargetState fRenderTargetState` - 渲染目标状态跟踪

### RenderTargetState

```cpp
struct RenderTargetState {
    SkISize fRenderTargetSize;
    GrSurfaceOrigin fRenderTargetOrigin;
};
```

跟踪渲染目标尺寸和原点，用于坐标变换和脏检查。

### SamplerBindings

```cpp
struct SamplerBindings {
    GrMtlSampler* fSampler;
    id<MTLTexture> fTexture;
};
```

存储纹理和采样器对的绑定信息。

## 公共 API 函数

### setData

```cpp
void setData(GrMtlFramebuffer* framebuffer, const GrProgramInfo& programInfo)
```

设置管线数据，包括 Uniform 值、渲染目标状态、处理器参数。

### setTextures

```cpp
void setTextures(const GrGeometryProcessor&, const GrPipeline&,
                 const GrSurfaceProxy* const geomProcTextures[])
```

设置几何处理器和片段处理器的纹理绑定。

### bindTextures

```cpp
void bindTextures(GrMtlRenderCommandEncoder* renderCmdEncoder)
```

将纹理和采样器绑定到 Metal 渲染命令编码器。

### setDrawState

```cpp
void setDrawState(GrMtlRenderCommandEncoder*, const skgpu::Swizzle& writeSwizzle,
                  const GrXferProcessor&)
```

设置绘制状态，包括混合常量和深度模板状态。

### SetDynamicScissorRectState

```cpp
static void SetDynamicScissorRectState(GrMtlRenderCommandEncoder*,
                                       SkISize colorAttachmentDimensions,
                                       GrSurfaceOrigin rtOrigin,
                                       SkIRect scissorRect)
```

设置动态裁剪矩形，考虑原点翻转。

## 内部实现细节

### setRenderTargetState

根据渲染目标尺寸和原点更新内部状态，脏检查避免重复设置，计算 RT 调整矩阵上传到 Uniform。

### bindUniforms

将 Uniform 缓冲区绑定到顶点和片段着色器的绑定点 0。

### setBlendConstants

根据写入 Swizzle 和传输处理器设置混合常量颜色。

### setDepthStencilState

设置深度比较函数、深度写入掩码、模板测试和操作。

## 设计模式与设计决策

### 状态缓存

`RenderTargetState` 跟踪当前状态，避免重复设置相同参数，减少 Metal API 调用。

### 延迟绑定

纹理和 Uniform 先设置到内部缓冲区，在绘制前统一绑定，支持批处理优化。

### 分离设置和绑定

`setTextures()` 准备绑定信息，`bindTextures()` 执行绑定，解耦逻辑便于复用。

## 性能考量

### 状态脏检查

避免重复设置渲染目标状态，减少 Uniform 上传和坐标变换计算。

### 批量绑定

一次性绑定所有纹理和采样器，减少编码器调用开销。

### Uniform 缓冲区重用

`GrMtlPipelineStateDataManager` 复用缓冲区，避免每帧分配。

## 相关文件

- `src/gpu/ganesh/mtl/GrMtlPipeline.h` - Metal 管线封装
- `src/gpu/ganesh/mtl/GrMtlPipelineStateDataManager.h` - Uniform 管理
- `src/gpu/ganesh/mtl/GrMtlPipelineStateBuilder.h` - 管线构建器
- `src/gpu/ganesh/mtl/GrMtlOpsRenderPass.h` - 渲染通道
