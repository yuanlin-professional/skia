# GrMtlOpsRenderPass

> 源文件
> - `src/gpu/ganesh/mtl/GrMtlOpsRenderPass.h`
> - `src/gpu/ganesh/mtl/GrMtlOpsRenderPass.mm`

## 概述

`GrMtlOpsRenderPass` 是 Ganesh 图形后端中 Metal 实现的操作渲染通道类,负责执行图形操作(Ops)的实际渲染。该类作为渲染命令的提交层,协调管道状态绑定、顶点缓冲绑定、纹理绑定以及绘制调用等核心渲染操作。它管理 Metal 渲染命令编码器的生命周期,处理 MSAA resolve、裁剪矩形设置、清除操作等复杂场景,是连接 Skia 高层绘制操作与 Metal 底层渲染命令的关键桥梁。

## 架构位置

`GrMtlOpsRenderPass` 位于 Skia 图形库的 GPU 后端渲染通道层次结构中:

```
Skia 图形库
└── GPU 后端 (src/gpu)
    └── Ganesh 渲染引擎 (ganesh)
        ├── GrOpsRenderPass (渲染通道抽象基类)
        │   └── GrMtlOpsRenderPass (Metal 渲染通道) ← 当前类
        └── Metal 后端实现 (mtl)
            ├── GrMtlGpu (GPU 接口)
            ├── GrMtlRenderCommandEncoder (渲染编码器)
            ├── GrMtlPipelineState (管道状态)
            └── GrMtlFramebuffer (帧缓冲对象)
```

该类是 Metal 后端执行渲染操作的核心组件。

## 主要类与结构体

### GrMtlOpsRenderPass 类

Metal 操作渲染通道实现。

**继承关系:**
- 继承: `GrOpsRenderPass` (渲染通道抽象基类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGpu` | `GrMtlGpu*` | Metal GPU 对象指针 |
| `fFramebuffer` | `sk_sp<GrMtlFramebuffer>` | 帧缓冲对象 |
| `fActiveRenderCmdEncoder` | `GrMtlRenderCommandEncoder*` | 活动渲染命令编码器 |
| `fActivePipelineState` | `GrMtlPipelineState*` | 活动管道状态 |
| `fActivePrimitiveType` | `MTLPrimitiveType` | 活动图元类型 |
| `fRenderPassDesc` | `MTLRenderPassDescriptor*` | 渲染通道描述符 |
| `fBounds` | `SkRect` | 渲染边界累积 |
| `fCurrentVertexStride` | `size_t` | 当前顶点步长 |
| `fDebugGroupActive` | `bool` | 调试组是否活跃(调试构建) |

## 公共 API 函数

### 构造与生命周期

```cpp
GrMtlOpsRenderPass(
    GrMtlGpu* gpu,
    GrRenderTarget* rt,
    sk_sp<GrMtlFramebuffer> framebuffer,
    GrSurfaceOrigin origin,
    const LoadAndStoreInfo& colorInfo,
    const StencilLoadAndStoreInfo& stencilInfo)
```
构造函数,初始化渲染通道并设置加载/存储操作。

```cpp
void submit()
```
提交渲染通道,完成命令编码并提交到 GPU。

### 初始化

```cpp
void initRenderState(GrMtlRenderCommandEncoder* encoder)
```
初始化渲染编码器的基本状态(视口、绕序等)。

### 内联上传

```cpp
void inlineUpload(GrOpFlushState* state, GrDeferredTextureUploadFn& upload) override
```
执行延迟纹理上传,用于动态更新纹理数据。

## 内部实现细节

### 渲染通道设置

`setupRenderPass()` 配置 Metal 渲染通道描述符:

```objc
// 配置颜色附件
auto colorAttachment = fRenderPassDesc.colorAttachments[0];
colorAttachment.texture = fFramebuffer->colorAttachment()->mtlTexture();
colorAttachment.clearColor = MTLClearColorMake(...);
colorAttachment.loadAction = mtlLoadAction[colorInfo.fLoadOp];
colorAttachment.storeAction = mtlStoreAction[colorInfo.fStoreOp];

// 配置模板附件
auto mtlStencil = fRenderPassDesc.stencilAttachment;
mtlStencil.texture = fFramebuffer->stencilAttachment()->mtlTexture();
mtlStencil.loadAction = mtlLoadAction[stencilInfo.fLoadOp];
mtlStencil.storeAction = mtlStoreAction[stencilInfo.fStoreOp];
```

### 加载/存储操作映射

使用静态查找表高效转换操作类型:

```cpp
// 加载操作映射
const static MTLLoadAction mtlLoadAction[] {
    MTLLoadActionLoad,      // kLoad
    MTLLoadActionClear,     // kClear
    MTLLoadActionDontCare   // kDiscard
};

// 存储操作映射
const static MTLStoreAction mtlStoreAction[] {
    MTLStoreActionStore,    // kStore
    MTLStoreActionDontCare  // kDiscard
};
```

### 管道绑定流程

`onBindPipeline()` 实现管道状态绑定:

1. **生成程序描述符**:
   ```cpp
   GrProgramDesc desc = caps.makeDesc(fRenderTarget, programInfo, flags);
   ```

2. **查找或创建管道状态**:
   ```cpp
   fActivePipelineState = fGpu->resourceProvider()
       .findOrCreateCompatiblePipelineState(desc, programInfo);
   ```

3. **设置管道数据**:
   ```cpp
   fActivePipelineState->setData(fFramebuffer.get(), programInfo);
   ```

4. **创建或复用渲染编码器**:
   ```cpp
   if (!fActiveRenderCmdEncoder) {
       this->setupRenderCommandEncoder(fActivePipelineState);
   }
   ```

5. **绑定管道状态对象**:
   ```cpp
   fActiveRenderCmdEncoder->setRenderPipelineState(
       fActivePipelineState->pipeline()->mtlPipelineState());
   ```

6. **配置渲染状态**:
   ```cpp
   fActivePipelineState->setDrawState(fActiveRenderCmdEncoder, ...);
   ```

### 图元类型转换

`gr_to_mtl_primitive()` 将 Skia 图元类型映射到 Metal:

| Skia 类型 | Metal 类型 |
|-----------|-----------|
| `kTriangles` | `MTLPrimitiveTypeTriangle` |
| `kTriangleStrip` | `MTLPrimitiveTypeTriangleStrip` |
| `kPoints` | `MTLPrimitiveTypePoint` |
| `kLines` | `MTLPrimitiveTypeLine` |
| `kLineStrip` | `MTLPrimitiveTypeLineStrip` |

使用静态数组实现 O(1) 转换。

### 裁剪矩形设置

`onSetScissorRect()` 动态更新裁剪矩形:

```cpp
GrMtlPipelineState::SetDynamicScissorRectState(
    fActiveRenderCmdEncoder,
    fFramebuffer->colorAttachment()->dimensions(),
    fOrigin,
    scissor);
```

处理表面原点(origin)差异,确保裁剪坐标正确。

### 纹理绑定

`onBindTextures()` 绑定几何处理器和管线纹理:

```cpp
fActivePipelineState->setTextures(geomProc, pipeline, geomProcTextures);
fActivePipelineState->bindTextures(fActiveRenderCmdEncoder);
```

### 缓冲区绑定

`onBindBuffers()` 管理索引、实例和顶点缓冲:

```cpp
void onBindBuffers(
    sk_sp<const GrBuffer> indexBuffer,
    sk_sp<const GrBuffer> instanceBuffer,
    sk_sp<const GrBuffer> vertexBuffer,
    GrPrimitiveRestart primitiveRestart)
```

### 绘制命令

支持多种绘制模式:

- **`onDraw()`**: 简单顶点绘制
- **`onDrawIndexed()`**: 索引绘制
- **`onDrawInstanced()`**: 实例化绘制
- **`onDrawIndexedInstanced()`**: 索引实例化绘制
- **`onDrawIndirect()`**: 间接绘制
- **`onDrawIndexedIndirect()`**: 索引间接绘制

### 清除操作

**颜色清除** (`onClear()`):

```cpp
auto colorAttachment = fRenderPassDesc.colorAttachments[0];
colorAttachment.clearColor = MTLClearColorMake(color[0], ...);
colorAttachment.loadAction = MTLLoadActionClear;
this->setupRenderCommandEncoder(nullptr);
```

**模板清除** (`onClearStencilClip()`):

```cpp
auto stencilAttachment = fRenderPassDesc.stencilAttachment;
stencilAttachment.clearStencil = insideStencilMask ? (1 << (bitCount - 1)) : 0;
stencilAttachment.loadAction = MTLLoadActionClear;
```

### MSAA Resolve 处理

`setupResolve()` 配置 MSAA resolve:

```objc
if (resolveAttachment) {
    colorAttachment.resolveTexture = resolve->mtlTexture();
    colorAttachment.storeAction = MTLStoreActionMultisampleResolve;

    if (colorAttachment.loadAction == MTLLoadActionLoad) {
        // 从 resolve 纹理加载到 MSAA 纹理
        fActiveRenderCmdEncoder = fGpu->loadMSAAFromResolve(...);
    }
}
```

支持双向 MSAA 数据传输:
- **Resolve**: MSAA → 单采样(通过 storeAction)
- **Load**: 单采样 → MSAA(通过 `loadMSAAFromResolve`)

### 线框模式支持

根据管线设置或全局模式启用线框:

```cpp
if (gpu()->caps()->wireframeMode() || programInfo.pipeline().isWireframe()) {
    fActiveRenderCmdEncoder->setTriangleFillMode(MTLTriangleFillModeLines);
} else {
    fActiveRenderCmdEncoder->setTriangleFillMode(MTLTriangleFillModeFill);
}
```

### 边界追踪

累积绘制边界用于优化:

```cpp
fBounds.join(drawBounds);  // 每次绘制更新边界
```

提交时传递给 GPU 用于优化间接命令缓冲执行。

### 延迟纹理上传

`inlineUpload()` 在渲染通道中插入纹理上传:

```cpp
state->doUpload(upload);  // 执行上传

// 处理 MSAA 场景
if (!this->setupResolve()) {
    this->setupRenderCommandEncoder(nullptr);
}
```

确保上传后正确恢复渲染状态。

### 调试组支持

调试构建中使用 Metal 调试组:

```objc
#ifdef SK_ENABLE_MTL_DEBUG_INFO
    fActiveRenderCmdEncoder->pushDebugGroup(@"bindAndDraw");
    fDebugGroupActive = true;
    // ...
    fActiveRenderCmdEncoder->popDebugGroup();
#endif
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrOpsRenderPass` | 渲染通道抽象基类 |
| `GrMtlGpu` | Metal GPU 接口 |
| `GrMtlFramebuffer` | 帧缓冲对象 |
| `GrMtlRenderCommandEncoder` | 渲染命令编码器 |
| `GrMtlPipelineState` | 管道状态 |
| `GrMtlBuffer` | 缓冲对象 |
| `GrRenderTarget` | 渲染目标 |
| `GrProgramInfo` | 程序信息 |
| `GrOpFlushState` | 操作刷新状态 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| `GrMtlGpu` | 创建和管理渲染通道 |
| `GrDrawOpAtlas` | 使用渲染通道绘制图集 |

## 设计模式与设计决策

### 1. 模板方法模式

继承 `GrOpsRenderPass` 并实现所有虚函数:

```cpp
bool onBindPipeline(...) override;
void onDraw(...) override;
void onDrawIndexed(...) override;
```

### 2. 延迟初始化

渲染编码器延迟创建:

```cpp
if (!fActiveRenderCmdEncoder) {
    this->setupRenderCommandEncoder(...);
}
```

避免空通道的副作用。

### 3. 状态缓存

缓存活动管道状态和图元类型,避免重复设置:

```cpp
fActivePipelineState = ...;
fActivePrimitiveType = ...;
```

### 4. 策略模式

根据 resolve 需求选择不同策略:
- 无 resolve: 标准渲染
- 有 resolve: 配置 resolve 附件
- Load + resolve: 从 resolve 加载到 MSAA

### 5. 命令模式

每个 `onDraw*` 方法封装特定绘制命令。

### 6. 边界累积

渲染边界逐步累积,支持优化:

```cpp
fBounds.join(drawBounds);
```

## 性能考量

### 1. 延迟编码器创建

避免创建空编码器,减少 GPU 命令开销。

### 2. 状态缓存

缓存活动管道避免重复查找和绑定。

### 3. 静态查找表

操作类型转换使用静态数组,O(1) 查找。

### 4. MSAA 优化

智能处理 MSAA resolve:
- 仅在需要时 resolve
- 支持无存储 resolve(memoryless 附件)
- 双向数据传输

### 5. 推送常量

小数据通过推送常量避免缓冲区分配。

### 6. 边界追踪

提供精确边界信息用于间接命令优化。

### 7. 调试组控制

调试组仅在调试构建启用,生产环境无开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrOpsRenderPass.h` | 继承关系 | 渲染通道抽象基类 |
| `src/gpu/ganesh/mtl/GrMtlGpu.h/mm` | 使用关系 | GPU 接口 |
| `src/gpu/ganesh/mtl/GrMtlFramebuffer.h/mm` | 使用关系 | 帧缓冲对象 |
| `src/gpu/ganesh/mtl/GrMtlRenderCommandEncoder.h` | 使用关系 | 渲染编码器 |
| `src/gpu/ganesh/mtl/GrMtlPipelineState.h/mm` | 使用关系 | 管道状态 |
| `src/gpu/ganesh/mtl/GrMtlBuffer.h/mm` | 使用关系 | 缓冲对象 |
| `src/gpu/ganesh/GrRenderTarget.h` | 使用关系 | 渲染目标 |
| `src/gpu/ganesh/GrProgramInfo.h` | 使用关系 | 程序信息 |
