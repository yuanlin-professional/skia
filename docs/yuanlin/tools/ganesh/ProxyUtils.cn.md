# ProxyUtils

> 源文件：tools/ganesh/ProxyUtils.h, tools/ganesh/ProxyUtils.cpp

## 概述

ProxyUtils 是 Skia Ganesh 测试工具集中的实用工具模块，提供了一组用于处理纹理代理（Texture Proxy）和程序信息（Program Info）的辅助函数。该模块的主要职责是简化测试代码中常见的 GPU 资源创建和管理操作，特别是在需要从原始像素数据创建纹理或从图像获取底层纹理代理时。

ProxyUtils 封装了 Ganesh 内部的复杂细节，为测试代码提供了简洁易用的接口。它处理了诸如格式选择、swizzle 配置、内存分配和数据上传等底层操作，使测试开发人员能够专注于测试逻辑而非 GPU 资源管理的细节。

该模块特别适用于单元测试、集成测试和性能基准测试场景，在这些场景中需要快速创建可预测的 GPU 纹理资源或构建简单的渲染程序配置。

## 架构位置

ProxyUtils 位于 Skia 测试工具层级的 `tools/ganesh/` 目录下，与其他 Ganesh 测试工具并列：

- **上层调用者**：
  - 各种 Ganesh GPU 单元测试
  - 效果处理器测试（FP tests）
  - 纹理操作测试
  - 渲染管线测试

- **同级组件**：
  - TestOps - 测试用绘制操作
  - TestContext - 测试上下文管理
  - MemoryCache - 内存缓存测试工具

- **下层依赖**：
  - `src/gpu/ganesh/GrProxyProvider.h` - 代理提供者
  - `src/gpu/ganesh/GrDirectContext.h` - 直接上下文
  - `src/gpu/ganesh/SurfaceContext.h` - 表面上下文
  - `src/gpu/ganesh/GrProgramInfo.h` - 程序信息
  - `src/gpu/ganesh/ops/GrSimpleMeshDrawOpHelper.h` - 网格绘制辅助工具

ProxyUtils 作为桥接层，将高层测试需求转换为低层 Ganesh API 调用。

## 主要类与结构体

ProxyUtils 采用纯函数式设计，不定义任何类或结构体，所有功能通过独立的工具函数提供。这些函数都位于 `sk_gpu_test` 命名空间中，清晰地标识它们是测试专用工具。

### 函数原型

```cpp
namespace sk_gpu_test {

// 从图像获取纹理代理
GrTextureProxy* GetTextureImageProxy(SkImage*, GrRecordingContext*);

// 从像素数据创建纹理代理视图
GrSurfaceProxyView MakeTextureProxyViewFromData(GrDirectContext*,
                                                GrRenderable,
                                                GrSurfaceOrigin,
                                                GrCPixmap pixmap);

// 创建程序信息（仅在 SK_GANESH 定义时可用）
GrProgramInfo* CreateProgramInfo(const GrCaps*,
                                 SkArenaAlloc*,
                                 const GrSurfaceProxyView& writeView,
                                 bool usesMSAASurface,
                                 GrAppliedClip&&,
                                 const GrDstProxyView&,
                                 GrGeometryProcessor*,
                                 SkBlendMode,
                                 GrPrimitiveType,
                                 GrXferBarrierFlags renderPassXferBarriers,
                                 GrLoadOp colorLoadOp,
                                 GrPipeline::InputFlags flags,
                                 const GrUserStencilSettings* stencil);

}  // namespace sk_gpu_test
```

## 公共 API 函数

### GetTextureImageProxy

```cpp
GrTextureProxy* GetTextureImageProxy(SkImage* image, GrRecordingContext* rContext);
```

从 SkImage 对象中提取底层的纹理代理。这个函数处理了多种边界情况和上下文验证。

**参数说明**：
- `image` - 要提取纹理代理的图像对象
- `rContext` - 录制上下文，如果为空则尝试使用图像自带的上下文

**返回值**：
- 成功时返回指向纹理代理的指针
- 失败时返回 `nullptr`（图像非 Ganesh 后端、是 YUVA 格式、上下文不匹配等）

**使用场景**：
- 验证图像是否由 GPU 纹理支持
- 获取图像的底层纹理属性
- 在测试中访问图像的内部纹理状态

**实现要点**：
1. 检查图像是否为 Ganesh 后端且非 YUVA 格式
2. 如果未提供上下文，尝试从图像获取
3. 通过 `skgpu::ganesh::AsView` 获取表面视图
4. 验证代理类型并返回纹理代理

### MakeTextureProxyViewFromData

```cpp
GrSurfaceProxyView MakeTextureProxyViewFromData(GrDirectContext* dContext,
                                                GrRenderable renderable,
                                                GrSurfaceOrigin origin,
                                                GrCPixmap pixmap);
```

从原始像素数据创建纹理代理视图。这是测试中最常用的函数之一，用于快速创建测试纹理。

**参数说明**：
- `dContext` - 直接上下文（需要直接上下文以执行像素上传）
- `renderable` - 纹理是否可渲染（`GrRenderable::kYes` 或 `GrRenderable::kNo`）
- `origin` - 表面原点（`kTopLeft_GrSurfaceOrigin` 或 `kBottomLeft_GrSurfaceOrigin`）
- `pixmap` - 包含像素数据、尺寸和颜色信息的 GrCPixmap 对象

**返回值**：
- 成功时返回完整配置的 `GrSurfaceProxyView` 对象
- 失败时返回空视图（上下文已放弃、格式不支持、内存不足等）

**创建流程**：
1. 检查上下文有效性
2. 根据颜色类型和可渲染性选择默认后端格式
3. 确定适当的读取 swizzle
4. 创建纹理代理（精确大小、预算内、不使用 mipmap）
5. 创建表面上下文
6. 将像素数据写入纹理
7. 返回表面视图

### CreateProgramInfo

```cpp
GrProgramInfo* CreateProgramInfo(const GrCaps* caps,
                                 SkArenaAlloc* arena,
                                 const GrSurfaceProxyView& writeView,
                                 bool usesMSAASurface,
                                 GrAppliedClip&& appliedClip,
                                 const GrDstProxyView& dstProxyView,
                                 GrGeometryProcessor* geomProc,
                                 SkBlendMode blendMode,
                                 GrPrimitiveType primitiveType,
                                 GrXferBarrierFlags renderPassXferBarriers,
                                 GrLoadOp colorLoadOp,
                                 GrPipeline::InputFlags flags = GrPipeline::InputFlags::kNone,
                                 const GrUserStencilSettings* stencil = &GrUserStencilSettings::kUnused);
```

创建用于测试的 GPU 程序信息对象。这个函数封装了创建简单渲染程序所需的复杂配置。

**参数说明**（主要参数）：
- `caps` - GPU 能力对象，定义硬件和驱动特性
- `arena` - 竞技场分配器，用于程序信息的内存分配
- `writeView` - 写入目标的表面视图
- `usesMSAASurface` - 是否使用多重采样抗锯齿
- `geomProc` - 几何处理器，定义顶点属性和着色器
- `blendMode` - 混合模式（如 SrcOver、Multiply 等）
- `primitiveType` - 图元类型（三角形、三角形带、线段等）

**实现细节**：
- 创建基于混合模式的处理器集合
- 使用不透明黑色作为分析颜色
- 执行处理器最终化分析
- 断言不需要目标纹理（简化测试场景）
- 调用 `GrSimpleMeshDrawOpHelper::CreateProgramInfo` 完成创建

**使用场景**：
- 在不创建完整绘制操作的情况下测试程序创建
- 验证着色器编译和链接
- 测试特定几何处理器和混合模式组合

## 内部实现细节

### 上下文验证逻辑

`GetTextureImageProxy` 实现了多层上下文验证：

```cpp
if (!as_IB(image)->isGaneshBacked() || as_IB(image)->isYUVA()) {
    return nullptr;  // 非 Ganesh 后端或 YUVA 格式
}

if (!rContext) {
    GrImageContext* iContext = as_IB(image)->context();
    SkASSERT(iContext);
    rContext = iContext->priv().asRecordingContext();
    if (!rContext) {
        return nullptr;  // 无法获取录制上下文
    }
}
```

这种验证确保只有兼容的图像和上下文组合才能成功提取纹理代理。

### 格式和 Swizzle 选择

`MakeTextureProxyViewFromData` 中的格式选择考虑了多个因素：

```cpp
const GrBackendFormat format = caps->getDefaultBackendFormat(pixmap.colorType(), renderable);
if (!format.isValid()) {
    return {};  // 硬件不支持该颜色类型
}
skgpu::Swizzle swizzle = caps->getReadSwizzle(format, pixmap.colorType());
```

- **后端格式**：根据颜色类型和可渲染性选择最佳 GPU 格式（如 RGBA8、RGBA16F）
- **Swizzle**：处理通道顺序差异（如 RGBA vs BGRA），确保跨平台一致性

### 代理创建参数

纹理代理的创建使用了测试友好的参数配置：

```cpp
proxy = proxyProvider->createProxy(
    format,
    pixmap.dimensions(),
    renderable,
    /*sample count*/ 1,           // 单采样
    skgpu::Mipmapped::kNo,          // 不使用 mipmap
    SkBackingFit::kExact,           // 精确尺寸
    skgpu::Budgeted::kYes,          // 计入内存预算
    GrProtected::kNo,               // 非保护内存
    /*label=*/"TextureProxyViewFromData");
```

这些参数平衡了简单性和功能性，适合大多数测试场景。

### 像素数据上传

通过表面上下文执行像素上传：

```cpp
auto sContext = dContext->priv().makeSC(std::move(view), pixmap.colorInfo());
if (!sContext->writePixels(dContext, pixmap, {0, 0})) {
    return {};  // 上传失败
}
```

表面上下文处理了格式转换、内存布局和 GPU 传输等复杂操作。

### 处理器分析

`CreateProgramInfo` 执行处理器集合的完整分析：

```cpp
GrProcessorSet processors = GrProcessorSet(blendMode);
SkPMColor4f analysisColor = { 0, 0, 0, 1 };  // 不透明黑色

SkDEBUGCODE(auto analysis =) processors.finalize(
    analysisColor,
    GrProcessorAnalysisCoverage::kSingleChannel,
    &appliedClip,
    stencilSettings,
    *caps,
    GrClampType::kAuto,
    &analysisColor);

SkASSERT(!analysis.requiresDstTexture());
```

分析步骤确定：
- 最终的输出颜色特性
- 是否需要目标纹理（用于高级混合）
- 覆盖率类型（单通道、全覆盖等）

测试场景中断言不需要目标纹理，简化了测试配置。

## 依赖关系

### 核心 Ganesh 依赖

- **GrDirectContext**：提供 GPU 设备访问和资源管理
- **GrProxyProvider**：创建和管理表面代理
- **GrTextureProxy**：纹理资源的延迟表示
- **SurfaceContext**：表面的高级操作接口

### 图像处理依赖

- **SkImage_Base**：访问 SkImage 的内部实现
- **GrImageUtils**：Ganesh 图像工具函数
- **SkGr**：Skia 核心与 Ganesh 的桥接层

### 着色器和程序依赖

- **GrProgramInfo**：封装完整的 GPU 程序配置
- **GrGeometryProcessor**：定义顶点处理逻辑
- **GrProcessorSet**：管理片段处理器集合
- **GrSimpleMeshDrawOpHelper**：简化程序信息创建

### 数据结构依赖

- **GrPixmap/GrCPixmap**：GPU 像素图像数据表示
- **GrImageInfo**：图像元数据（尺寸、颜色类型等）
- **GrBackendFormat**：后端特定的纹理格式

## 设计模式与设计决策

### 纯函数式接口

ProxyUtils 采用纯函数而非类封装，这种设计：
- **简单性**：每个函数执行单一明确的任务
- **无状态**：函数之间无依赖，易于理解和测试
- **可组合性**：可以灵活组合调用以实现复杂场景

### 命名空间隔离

所有函数位于 `sk_gpu_test` 命名空间中：
```cpp
namespace sk_gpu_test {
    // 所有工具函数
}
```

这清晰地表明这些是测试专用工具，不应在生产代码中使用。

### 错误处理策略

函数采用返回空值/nullptr 的错误处理方式，而非抛出异常：
- `GetTextureImageProxy` 失败时返回 `nullptr`
- `MakeTextureProxyViewFromData` 失败时返回空的 `GrSurfaceProxyView`

这种设计符合 Skia 的错误处理惯例，便于测试代码检查和处理失败情况。

### 条件编译

`CreateProgramInfo` 使用条件编译保护：
```cpp
#if defined(SK_GANESH)
GrProgramInfo* CreateProgramInfo(...) { ... }
#endif
```

这允许在不构建 Ganesh 后端时排除该功能，减少二进制大小和编译时间。

### 默认参数简化

`CreateProgramInfo` 为不常变的参数提供了默认值：
```cpp
GrPipeline::InputFlags flags = GrPipeline::InputFlags::kNone,
const GrUserStencilSettings* stencil = &GrUserStencilSettings::kUnused
```

这使得大多数测试调用可以省略这些参数，提高了代码可读性。

### 资源管理决策

纹理创建时的关键决策：
- **预算内分配**：`skgpu::Budgeted::kYes` - 允许 Ganesh 管理内存压力
- **精确尺寸**：`SkBackingFit::kExact` - 避免过度分配
- **单采样**：适合大多数测试场景
- **无 mipmap**：简化创建流程，加速测试执行

## 性能考量

### 内存分配优化

`CreateProgramInfo` 使用竞技场分配器（Arena Allocator）：
```cpp
GrProgramInfo* CreateProgramInfo(const GrCaps* caps,
                                 SkArenaAlloc* arena, ...)
```

竞技场分配器提供：
- **批量分配**：减少内存分配次数
- **缓存友好**：连续内存布局提高缓存命中率
- **快速释放**：整个竞技场一次性释放

### 避免不必要的复制

`MakeTextureProxyViewFromData` 的实现最小化了数据复制：
1. 直接创建目标尺寸的纹理
2. 通过 `writePixels` 直接上传数据到 GPU
3. 返回视图而非复制代理对象

### 格式查询缓存

`getDefaultBackendFormat` 和 `getReadSwizzle` 的结果通常被 `GrCaps` 缓存，避免重复计算。

### 测试友好的权衡

作为测试工具，ProxyUtils 优先考虑简单性和可预测性，而非极致性能：
- 不实现代理共享或重用
- 不使用 mipmap（即使可能提高渲染性能）
- 使用同步像素上传（避免并发复杂性）

这些权衡在测试场景中是合理的，因为测试通常处理小纹理且关注正确性而非性能。

## 相关文件

### 同目录测试工具
- `tools/ganesh/TestOps.h/cpp` - 测试用绘制操作
- `tools/ganesh/TestContext.h/cpp` - 测试上下文管理
- `tools/ganesh/MemoryCache.h/cpp` - 内存缓存测试工具

### Ganesh 核心组件
- `src/gpu/ganesh/GrProxyProvider.h` - 代理提供者实现
- `src/gpu/ganesh/GrDirectContext.h` - 直接上下文接口
- `src/gpu/ganesh/SurfaceContext.h` - 表面上下文操作
- `src/gpu/ganesh/GrTextureProxy.h` - 纹理代理定义

### 程序和着色器
- `src/gpu/ganesh/GrProgramInfo.h` - 程序信息封装
- `src/gpu/ganesh/GrGeometryProcessor.h` - 几何处理器接口
- `src/gpu/ganesh/ops/GrSimpleMeshDrawOpHelper.h` - 网格绘制辅助

### 图像处理
- `src/image/SkImage_Base.h` - SkImage 内部接口
- `src/gpu/ganesh/image/GrImageUtils.h` - Ganesh 图像工具
- `src/gpu/ganesh/SkGr.h` - Skia 与 Ganesh 桥接层

### 数据表示
- `src/gpu/ganesh/GrPixmap.h` - GPU 像素图像
- `src/gpu/ganesh/GrImageInfo.h` - 图像元数据
- `include/gpu/ganesh/GrBackendSurface.h` - 后端表面定义
