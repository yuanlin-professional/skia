# GrVkOpsRenderPass

> 源文件
> - src/gpu/ganesh/vk/GrVkOpsRenderPass.h
> - src/gpu/ganesh/vk/GrVkOpsRenderPass.cpp

## 概述

`GrVkOpsRenderPass` 是 Skia 图形库中 Ganesh 渲染引擎针对 Vulkan 后端的渲染通道实现类。它继承自 `GrOpsRenderPass` 基类,负责管理 Vulkan 渲染通道的生命周期、绘制命令的记录和提交、管线状态绑定以及附件布局管理。该类是连接高层绘制操作与 Vulkan 命令缓冲区记录的关键桥梁。

`GrVkOpsRenderPass` 封装了 Vulkan 的 `VkRenderPass` 和 `VkFramebuffer`,处理颜色附件、解析附件、模板附件的加载和存储操作,支持 MSAA 可丢弃附件、输入附件、内联上传等高级特性。它还负责管理辅助命令缓冲区(secondary command buffer)的创建和提交。

## 架构位置

```
Skia 渲染架构
├── GrOpsTask (操作任务)
│   └── GrOpsRenderPass (抽象渲染通道)
│       └── GrVkOpsRenderPass (Vulkan 渲染通道实现) ← 当前类
│           ├── GrVkGpu (Vulkan GPU)
│           ├── GrVkFramebuffer (帧缓冲区)
│           ├── GrVkRenderPass (渲染通道)
│           ├── GrVkSecondaryCommandBuffer (辅助命令缓冲区)
│           ├── GrVkPipelineState (管线状态)
│           └── GrVkCommandBuffer (命令缓冲区)
```

`GrVkOpsRenderPass` 在 Ganesh 架构中处于渲染通道层,负责将高层的绘制操作(Ops)转换为 Vulkan 命令缓冲区中的具体命令。它管理渲染通道的开始和结束,协调各种 Vulkan 资源的使用。

## 主要类与结构体

### 继承关系
```
GrOpsRenderPass (基类 - 渲染通道抽象接口)
  ↑
GrVkOpsRenderPass (派生类 - Vulkan 实现)
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGpu` | `GrVkGpu*` | 指向 Vulkan GPU 对象的指针 |
| `fFramebuffer` | `sk_sp<GrVkFramebuffer>` | 当前使用的帧缓冲区 |
| `fCurrentSecondaryCommandBuffer` | `unique_ptr<GrVkSecondaryCommandBuffer>` | 当前辅助命令缓冲区 |
| `fCurrentRenderPass` | `const GrVkRenderPass*` | 当前渲染通道对象 |
| `fCurrentPipelineState` | `GrVkPipelineState*` | 当前绑定的管线状态 |
| `fCurrentPipelineBounds` | `SkIRect` | 当前管线的边界矩形 |
| `fBounds` | `SkIRect` | 渲染通道的边界矩形 |
| `fSelfDependencyFlags` | `SelfDependencyFlags` | 自依赖标志(用于输入附件) |
| `fLoadFromResolve` | `LoadFromResolve` | 是否从解析附件加载 |
| `fOverridePipelinesForResolveLoad` | `bool` | 是否需要覆盖管线以支持解析加载 |
| `fCurrentCBIsEmpty` | `bool` | 当前命令缓冲区是否为空 |
| `fIsActive` | `bool` (仅调试) | 渲染通道是否处于活动状态 |

## 公共 API 函数

### 生命周期管理

| 函数签名 | 功能说明 |
|---------|---------|
| `GrVkOpsRenderPass(GrVkGpu*)` | 构造函数,初始化 GPU 指针 |
| `~GrVkOpsRenderPass() override` | 析构函数,调用 reset() 清理资源 |
| `bool set(GrRenderTarget*, ...)` | 设置渲染通道参数并初始化 |
| `void reset()` | 重置渲染通道,释放所有资源 |
| `void submit()` | 提交渲染通道并结束记录 |

### 绘制命令

| 函数签名 | 功能说明 |
|---------|---------|
| `void onDraw(int vertexCount, int baseVertex) override` | 绘制顶点(非索引) |
| `void onDrawIndexed(...) override` | 绘制索引顶点 |
| `void onDrawInstanced(...) override` | 实例化绘制(非索引) |
| `void onDrawIndexedInstanced(...) override` | 实例化索引绘制 |
| `void onDrawIndirect(...) override` | 间接绘制命令 |
| `void onDrawIndexedIndirect(...) override` | 间接索引绘制命令 |

### 管线与资源绑定

| 函数签名 | 功能说明 |
|---------|---------|
| `bool onBindPipeline(const GrProgramInfo&, const SkRect&) override` | 绑定图形管线 |
| `bool onBindTextures(...) override` | 绑定纹理资源 |
| `void onBindBuffers(...) override` | 绑定顶点/索引缓冲区 |
| `void onSetScissorRect(const SkIRect&) override` | 设置裁剪矩形 |

### 清除操作

| 函数签名 | 功能说明 |
|---------|---------|
| `void onClear(const GrScissorState&, array<float, 4>) override` | 清除颜色附件 |
| `void onClearStencilClip(...) override` | 清除模板裁剪 |

### 高级特性

| 函数签名 | 功能说明 |
|---------|---------|
| `void inlineUpload(GrOpFlushState*, GrDeferredTextureUploadFn&) override` | 内联纹理上传 |
| `void onExecuteDrawable(unique_ptr<SkDrawable::GpuDrawHandler>) override` | 执行可绘制对象 |

## 内部实现细节

### 渲染通道初始化流程

```cpp
bool GrVkOpsRenderPass::set(
    GrRenderTarget* rt,
    sk_sp<GrVkFramebuffer> framebuffer,
    GrSurfaceOrigin origin,
    const SkIRect& bounds,
    const LoadAndStoreInfo& colorInfo,
    const StencilLoadAndStoreInfo& stencilInfo,
    const LoadAndStoreInfo& resolveInfo,
    SelfDependencyFlags selfDepFlags,
    LoadFromResolve loadFromResolve,
    const TArray<GrSurfaceProxy*, true>& sampledProxies) {

    // 1. 标记为活动状态
    fIsActive = true;

    // 2. 设置采样纹理的布局为 SHADER_READ_ONLY_OPTIMAL
    for (auto proxy : sampledProxies) {
        GrVkImage* texture = getTextureImage(proxy);
        texture->setImageLayout(fGpu, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, ...);
    }

    // 3. 存储帧缓冲区和边界
    fFramebuffer = std::move(framebuffer);
    fBounds = bounds;
    fSelfDependencyFlags = selfDepFlags;
    fLoadFromResolve = loadFromResolve;

    // 4. 初始化渲染通道
    if (wrapsSecondaryCommandBuffer()) {
        return initWrapped();  // 外部辅助命令缓冲区
    } else {
        return init(colorInfo, resolveInfo, stencilInfo);  // 正常初始化
    }
}
```

### 附件布局管理

`setAttachmentLayouts()` 在渲染通道开始前设置各附件的正确布局:

```cpp
void GrVkOpsRenderPass::setAttachmentLayouts(LoadFromResolve loadFromResolve) {
    // 1. 设置颜色附件布局
    if (fSelfDependencyFlags == SelfDependencyFlags::kForInputAttachment) {
        // 输入附件场景使用 GENERAL 布局
        fFramebuffer->colorAttachment()->setImageLayout(
            fGpu, VK_IMAGE_LAYOUT_GENERAL,
            VK_ACCESS_INPUT_ATTACHMENT_READ_BIT | VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
            VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
            false);
    } else {
        // 标准颜色附件使用 COLOR_ATTACHMENT_OPTIMAL
        fFramebuffer->colorAttachment()->setImageLayout(
            fGpu, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, ...);
    }

    // 2. 设置解析附件布局
    if (withResolve) {
        if (loadFromResolve == LoadFromResolve::kLoad) {
            // 需要从解析附件加载,使用 SHADER_READ_ONLY_OPTIMAL
            resolveAttachment->setImageLayout(
                fGpu, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, ...);
        } else {
            // 正常解析,使用 COLOR_ATTACHMENT_OPTIMAL
            resolveAttachment->setImageLayout(
                fGpu, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, ...);
        }
    }

    // 3. 设置模板附件布局
    if (withStencil) {
        stencilAttachment->setImageLayout(
            fGpu, VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL, ...);
    }
}
```

### 渲染区域粒度调整

Vulkan 要求渲染区域符合设备的粒度要求:

```cpp
void adjust_bounds_to_granularity(
    SkIRect* dstBounds,
    const SkIRect& srcBounds,
    const VkExtent2D& granularity,
    int maxWidth, int maxHeight) {

    // 调整宽度:起始位置向下取整,结束位置向上取整
    if (granularity.width > 1) {
        int rightAdj = srcBounds.fRight % granularity.width;
        if (rightAdj != 0) {
            rightAdj = granularity.width - rightAdj;
        }
        dstBounds->fRight = srcBounds.fRight + rightAdj;
        if (dstBounds->fRight > maxWidth) {
            dstBounds->fRight = maxWidth;
            dstBounds->fLeft = 0;
        } else {
            dstBounds->fLeft = srcBounds.fLeft - (srcBounds.fLeft % granularity.width);
        }
    }

    // 高度调整同理
    // ...
}
```

### MSAA 可丢弃附件处理

对于支持可丢弃 MSAA 的渲染目标,需要特殊处理加载/存储操作:

```cpp
// 在 beginRenderPass 中
if (loadFromResolve == LoadFromResolve::kLoad) {
    // 1. 先从解析附件加载到 MSAA 附件
    this->loadResolveIntoMSAA(adjustedBounds);

    // 2. 切换到主渲染子通道
    fGpu->currentCommandBuffer()->nexSubpass(fGpu, useSecondaryCommandBuffer);

    // 3. 更新解析附件布局为 COLOR_ATTACHMENT_OPTIMAL
    fFramebuffer->resolveAttachment()->updateImageLayout(
        VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL);
}
```

### 管线绑定与状态设置

```cpp
bool GrVkOpsRenderPass::onBindPipeline(
    const GrProgramInfo& programInfo,
    const SkRect& drawBounds) {

    // 1. 计算有效绘制边界
    SkRect rtRect = SkRect::Make(fBounds);
    if (rtRect.intersect(drawBounds)) {
        rtRect.roundOut(&fCurrentPipelineBounds);
    }

    // 2. 查找或创建兼容的管线状态
    VkRenderPass compatibleRenderPass = fCurrentRenderPass->vkRenderPass();
    fCurrentPipelineState = fGpu->resourceProvider()
        .findOrCreateCompatiblePipelineState(
            fRenderTarget, programInfo, compatibleRenderPass,
            fOverridePipelinesForResolveLoad);

    // 3. 绑定管线到命令缓冲区
    fCurrentPipelineState->bindPipeline(fGpu, currentCommandBuffer());

    // 4. 绑定 uniforms
    fCurrentPipelineState->setAndBindUniforms(
        fGpu, dimensions, programInfo, currentCommandBuffer());

    // 5. 设置动态状态
    GrVkPipeline::SetDynamicScissorRectState(...);
    GrVkPipeline::SetDynamicViewportState(...);
    GrVkPipeline::SetDynamicBlendConstantState(...);

    return true;
}
```

### 内联上传处理

内联上传需要临时中断渲染通道:

```cpp
void GrVkOpsRenderPass::inlineUpload(
    GrOpFlushState* state,
    GrDeferredTextureUploadFn& upload) {

    // 1. 结束当前辅助命令缓冲区
    if (fCurrentSecondaryCommandBuffer) {
        fCurrentSecondaryCommandBuffer->end(fGpu);
        fGpu->submitSecondaryCommandBuffer(
            std::move(fCurrentSecondaryCommandBuffer));
    }

    // 2. 结束当前渲染通道
    fGpu->endRenderPass(fRenderTarget, fOrigin, fBounds);

    // 3. 执行上传操作
    state->doUpload(upload, /*setLayoutToReadOnly=*/true);

    // 4. 创建新的渲染通道继续渲染
    this->addAdditionalRenderPass(/*mustUseSecondaryCB=*/false);
}
```

### 可绘制对象执行

```cpp
void GrVkOpsRenderPass::onExecuteDrawable(
    std::unique_ptr<SkDrawable::GpuDrawHandler> drawable) {

    // 1. 确保使用辅助命令缓冲区
    if (!fCurrentSecondaryCommandBuffer) {
        fGpu->endRenderPass(fRenderTarget, fOrigin, fBounds);
        this->addAdditionalRenderPass(/*mustUseSecondaryCB=*/true);
    }

    // 2. 准备可绘制信息
    GrVkDrawableInfo vkInfo;
    vkInfo.fSecondaryCommandBuffer =
        fCurrentSecondaryCommandBuffer->vkCommandBuffer();
    vkInfo.fCompatibleRenderPass = fCurrentRenderPass->vkRenderPass();
    vkInfo.fColorAttachmentIndex = ...;
    vkInfo.fFormat = fFramebuffer->colorAttachment()->imageFormat();

    // 3. 使状态失效(drawable 可能修改状态)
    currentCommandBuffer()->invalidateState();
    fCurrentCBIsEmpty = false;

    // 4. 执行绘制
    drawable->draw(GrBackendDrawableInfo(vkInfo));
    fGpu->addDrawable(std::move(drawable));
}
```

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖说明 |
|---------|---------|
| `GrOpsRenderPass` | 基类,定义渲染通道抽象接口 |
| `GrVkGpu` | Vulkan GPU,提供设备和命令缓冲区 |
| `GrVkFramebuffer` | 帧缓冲区,包含颜色/解析/模板附件 |
| `GrVkRenderPass` | Vulkan 渲染通道,定义附件配置 |
| `GrVkCommandBuffer` | 命令缓冲区,记录 GPU 命令 |
| `GrVkSecondaryCommandBuffer` | 辅助命令缓冲区 |
| `GrVkPipelineState` | 管线状态,包含着色器和管线配置 |
| `GrVkImage` | Vulkan 图像,用于附件 |
| `GrVkPipeline` | Vulkan 管线,提供动态状态设置 |
| `GrRenderTarget` | 渲染目标 |

### 被依赖的模块

| 模块名称 | 依赖说明 |
|---------|---------|
| `GrOpsTask` | 操作任务通过 GrVkOpsRenderPass 执行渲染 |
| `GrVkGpu` | GPU 通过 onGetOpsRenderPass() 获取渲染通道 |

## 设计模式与设计决策

### 1. 模板方法模式 (Template Method Pattern)

基类 `GrOpsRenderPass` 定义渲染流程模板,派生类实现具体的 Vulkan 操作:

```cpp
// 基类定义流程
class GrOpsRenderPass {
    void draw(...) { onDraw(...); }  // 模板方法
    virtual void onDraw(...) = 0;     // 子类实现
};

// 派生类实现 Vulkan 特定逻辑
class GrVkOpsRenderPass : public GrOpsRenderPass {
    void onDraw(...) override {
        currentCommandBuffer()->draw(...);
    }
};
```

### 2. 状态模式 (State Pattern)

通过成员变量跟踪渲染通道的状态:
- `fIsActive`: 是否处于活动记录状态
- `fCurrentCBIsEmpty`: 命令缓冲区是否为空
- `fCurrentPipelineState`: 当前绑定的管线状态

### 3. 适配器模式 (Adapter Pattern)

将 Skia 高层绘制操作适配到 Vulkan 命令缓冲区调用:

```cpp
void onDrawInstanced(...) override {
    // 适配: Skia 绘制 -> Vulkan 命令
    currentCommandBuffer()->draw(fGpu, vertexCount, instanceCount, ...);
}
```

### 4. 策略模式 (Strategy Pattern)

根据设备能力选择不同的命令缓冲区策略:

```cpp
if (fGpu->vkCaps().preferPrimaryOverSecondaryCommandBuffers()) {
    // 策略1: 使用主命令缓冲区
    // 直接记录到 fGpu->currentCommandBuffer()
} else {
    // 策略2: 使用辅助命令缓冲区
    fCurrentSecondaryCommandBuffer = createSecondaryCommandBuffer();
}
```

### 5. 对象池模式 (Object Pool Pattern)

`GrVkGpu` 缓存 `GrVkOpsRenderPass` 对象,避免频繁创建/销毁:

```cpp
std::unique_ptr<GrVkOpsRenderPass> fCachedOpsRenderPass;

GrOpsRenderPass* onGetOpsRenderPass(...) {
    if (!fCachedOpsRenderPass) {
        fCachedOpsRenderPass = std::make_unique<GrVkOpsRenderPass>(this);
    }
    fCachedOpsRenderPass->set(...);  // 重置并重用
    return fCachedOpsRenderPass.get();
}
```

### 6. 责任链模式 (Chain of Responsibility)

渲染通道可以在必要时分裂成多个子渲染通道(如内联上传):

```cpp
// 原始渲染通道
beginRenderPass() -> 记录命令 -> 内联上传
                                    ↓
                            endRenderPass()
                                    ↓
                         addAdditionalRenderPass()  // 新渲染通道
                                    ↓
                            继续记录命令 -> endRenderPass()
```

## 性能考量

### 1. 渲染通道合并

- **最小化渲染通道切换**: 尽可能在单个渲染通道内完成所有绘制,减少开销
- **延迟提交**: 只在必要时(如内联上传、可绘制对象)才结束渲染通道

### 2. 辅助命令缓冲区优化

- **并行记录**: 辅助命令缓冲区可在多线程中并行记录(尽管 Skia 当前未使用)
- **设备偏好**: 通过 `preferPrimaryOverSecondaryCommandBuffers()` 查询设备偏好,选择性能更好的路径

### 3. 动态状态利用

使用 Vulkan 动态状态减少管线切换:
- 动态 viewport: 避免为不同视口创建多个管线
- 动态 scissor: 高效实现裁剪
- 动态 blend constants: 支持动态混合参数

### 4. 管线状态缓存

```cpp
fCurrentPipelineState = fGpu->resourceProvider()
    .findOrCreateCompatiblePipelineState(...);
```

通过 `GrVkResourceProvider` 缓存管线状态,避免重复创建和编译。

### 5. 自依赖优化

对于需要读写同一附件的场景(如高级混合):
- 使用输入附件而非额外纹理采样
- 设置正确的自依赖标志和管线屏障

### 6. MSAA 带宽优化

- **可丢弃 MSAA**: 对于不需要保存的 MSAA 附件使用 `VK_ATTACHMENT_STORE_OP_DONT_CARE`
- **懒加载**: 通过 `LoadFromResolve` 支持从解析附件懒加载到 MSAA 附件

### 7. 清除操作优化

- **加载操作清除**: 优先使用渲染通道的 `LoadOp::CLEAR` 而非运行时 `clearAttachments()`
- **范围清除**: 使用 `clearAttachments()` 实现部分清除(scissor clear)

### 8. 间接绘制批处理

```cpp
void onDrawIndirect(const GrBuffer* drawIndirectBuffer, size_t offset, int drawCount) {
    const uint32_t maxDrawCount = fGpu->vkCaps().maxDrawIndirectDrawCount();
    while (remainingDraws >= 1) {
        uint32_t currDrawCount = std::min(remainingDraws, maxDrawCount);
        currentCommandBuffer()->drawIndirect(...);
        // 批量提交多个间接绘制调用
    }
}
```

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/gpu/ganesh/GrOpsRenderPass.h` | 基类定义 |
| `src/gpu/ganesh/vk/GrVkGpu.h/cpp` | GPU 对象,创建和管理渲染通道 |
| `src/gpu/ganesh/vk/GrVkFramebuffer.h/cpp` | 帧缓冲区,包含附件 |
| `src/gpu/ganesh/vk/GrVkRenderPass.h/cpp` | 渲染通道配置 |
| `src/gpu/ganesh/vk/GrVkCommandBuffer.h/cpp` | 命令缓冲区 |
| `src/gpu/ganesh/vk/GrVkPipelineState.h/cpp` | 管线状态 |
| `src/gpu/ganesh/vk/GrVkImage.h/cpp` | 图像附件 |
| `src/gpu/ganesh/vk/GrVkPipeline.h/cpp` | Vulkan 管线 |
| `src/gpu/ganesh/GrRenderTarget.h` | 渲染目标 |
| `src/gpu/ganesh/GrOpFlushState.h` | 操作刷新状态 |
