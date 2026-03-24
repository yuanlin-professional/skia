# GrGLRenderTarget

> 源文件
> - src/gpu/ganesh/gl/GrGLRenderTarget.h
> - src/gpu/ganesh/gl/GrGLRenderTarget.cpp

## 概述

`GrGLRenderTarget` 是 Skia Ganesh OpenGL 后端中表示渲染目标的核心类。它继承自 `GrRenderTarget`，封装了 OpenGL 帧缓冲对象（FBO）的管理和操作。该类支持多种渲染配置，包括单采样、多重采样、动态 MSAA（DMSAA）以及多重采样渲染到纹理（Multisampled Render to Texture）等高级特性。

该类管理一个或两个帧缓冲对象：单采样 FBO 用于最终输出，多重采样 FBO 用于抗锯齿渲染。它还负责模板附件的管理、内存统计以及与 OpenGL 后端的同步操作。

## 架构位置

```
GrSurface (基类)
    └── GrRenderTarget (渲染目标抽象)
        └── GrGLRenderTarget (GL渲染目标实现)
            └── GrGLTextureRenderTarget (纹理+渲染目标组合)

关系:
GrRenderTargetProxy -> GrGLRenderTarget -> OpenGL FBO
```

该类位于 Ganesh 图形栈的 OpenGL 渲染目标层，是 Skia 渲染目标抽象在 OpenGL 上的具体实现。

## 主要类与结构体

### GrGLRenderTarget

**继承关系:**
- 继承自: `GrRenderTarget`, `GrSurface`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fMultisampleFBOID` | `GrGLuint` | 多重采样 FBO ID |
| `fSingleSampleFBOID` | `GrGLuint` | 单采样 FBO ID |
| `fMSColorRenderbufferID` | `GrGLuint` | 多重采样颜色渲染缓冲 ID |
| `fRTFormat` | `GrGLFormat` | 渲染目标格式 |
| `fRTFBOOwnership` | `GrBackendObjectOwnership` | FBO 所有权（拥有/借用） |
| `fTotalMemorySamplesPerPixel` | `int` | 每像素总采样数（内存占用） |
| `fNeedsStencilAttachmentBind` | `bool[2]` | 是否需要重新绑定模板附件 |
| `fDMSAARenderToTextureFBOIsMultisample` | `bool` | DMSAA 渲染到纹理 FBO 是否为多重采样 |
| `fDynamicMSAAAttachment` | `sk_sp<GrGLAttachment>` | 动态 MSAA 附件 |

### IDs 结构体

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fMultisampleFBOID` | `GrGLuint` | 多重采样 FBO ID |
| `fRTFBOOwnership` | `GrBackendObjectOwnership` | FBO 所有权 |
| `fSingleSampleFBOID` | `GrGLuint` | 单采样 FBO ID |
| `fMSColorRenderbufferID` | `GrGLuint` | 多重采样颜色渲染缓冲 ID |
| `fTotalMemorySamplesPerPixel` | `int` | 每像素总采样数 |

### ResolveDirection 枚举

```cpp
enum class ResolveDirection : bool {
    kSingleToMSAA,  // 从单采样解析到多重采样
    kMSAAToSingle   // 从多重采样解析到单采样
};
```

## 公共 API 函数

### 工厂方法
- `static sk_sp<GrGLRenderTarget> MakeWrapped(...)` - 包装外部 FBO

### FBO 查询
- `bool isFBO0(bool multisample) const` - 是否为默认帧缓冲（FBO 0）
- `bool isMultisampledRenderToTexture() const` - 是否使用多重采样渲染到纹理
- `bool hasDynamicMSAAAttachment() const` - 是否有动态 MSAA 附件
- `GrGLFormat format() const` - 获取渲染目标格式

### 后端接口
- `GrBackendRenderTarget getBackendRenderTarget() const` - 获取后端渲染目标
- `GrBackendFormat backendFormat() const` - 获取后端格式

### 绑定操作
- `void bind(bool useMultisampleFBO)` - 绑定渲染目标到 GL_FRAMEBUFFER
- `void bindForPixelOps(GrGLenum fboTarget)` - 绑定用于像素操作
- `void bindForResolve(ResolveDirection)` - 绑定用于解析操作
- `bool mustRebind(bool useMultisampleFBO) const` - 是否必须重新绑定

### DMSAA 支持
- `bool ensureDynamicMSAAAttachment()` - 确保动态 MSAA 附件存在

### 模板支持
- `bool canAttemptStencilAttachment(bool useMultisampleFBO) const` - 是否可以附加模板缓冲

### 内存统计
- `void dumpMemoryStatistics(SkTraceMemoryDump*) const` - 导出内存统计信息

### 其他
- `bool alwaysClearStencil() const` - 是否总是清除模板

## 内部实现细节

### FBO 初始化

```cpp
void GrGLRenderTarget::init(GrGLFormat format, const IDs& idDesc) {
    fMultisampleFBOID = idDesc.fMultisampleFBOID;
    fSingleSampleFBOID = idDesc.fSingleSampleFBOID;
    fMSColorRenderbufferID = idDesc.fMSColorRenderbufferID;
    fRTFBOOwnership = idDesc.fRTFBOOwnership;
    fRTFormat = format;
    fTotalMemorySamplesPerPixel = idDesc.fTotalMemorySamplesPerPixel;
}
```

### 动态 MSAA 附件创建

```cpp
bool GrGLRenderTarget::ensureDynamicMSAAAttachment() {
    SkASSERT(this->numSamples() == 1);  // 单采样表面才需要

    if (fMultisampleFBOID) {
        return true;  // 已存在
    }

    // 检查是否支持 MSAA
    int internalSampleCount = caps.internalMultisampleCount(this->backendFormat());
    if (internalSampleCount <= 1) {
        return false;
    }

    // 检查是否支持自动解析（EXT_multisampled_render_to_texture）
    if (resourceProvider->caps()->msaaResolvesAutomatically() && this->asTexture()) {
        fMultisampleFBOID = fSingleSampleFBOID;  // 共用 FBO
        return true;
    }

    // 创建新的多重采样 FBO
    GL_CALL(GenFramebuffers(1, &fMultisampleFBOID));
    this->getGLGpu()->bindFramebuffer(GR_GL_FRAMEBUFFER, fMultisampleFBOID);

    // 创建并附加 MSAA 渲染缓冲
    fDynamicMSAAAttachment.reset(
        static_cast<GrGLAttachment*>(resourceProvider->getDiscardableMSAAAttachment(
            this->dimensions(), this->backendFormat(), internalSampleCount,
            GrProtected(this->isProtected()), GrMemoryless::kNo).release()));

    GL_CALL(FramebufferRenderbuffer(GR_GL_FRAMEBUFFER, GR_GL_COLOR_ATTACHMENT0,
                                    GR_GL_RENDERBUFFER,
                                    fDynamicMSAAAttachment->renderbufferID()));
    return true;
}
```

### 智能绑定逻辑

`bindInternal` 方法处理复杂的绑定场景，包括 DMSAA 渲染到纹理：

```cpp
void GrGLRenderTarget::bindInternal(GrGLenum fboTarget, bool useMultisampleFBO) {
    GrGLuint fboId = useMultisampleFBO ? fMultisampleFBOID : fSingleSampleFBOID;
    this->getGLGpu()->bindFramebuffer(fboTarget, fboId);

    // 处理 EXT_multisampled_render_to_texture 的特殊情况
    if (fSingleSampleFBOID != 0 &&
        fSingleSampleFBOID == fMultisampleFBOID &&
        useMultisampleFBO != fDMSAARenderToTextureFBOIsMultisample) {
        auto* glTex = static_cast<GrGLTexture*>(this->asTexture());

        // 某些驱动要求先解绑纹理
        if (this->getGLGpu()->glCaps().bindTexture0WhenChangingTextureFBOMultisampleCount()) {
            GL_CALL(FramebufferTexture2D(fboTarget, GR_GL_COLOR_ATTACHMENT0,
                                         GR_GL_TEXTURE_2D, 0, 0));
        }

        // 重新附加纹理（多重采样或单采样）
        if (useMultisampleFBO) {
            GL_CALL(FramebufferTexture2DMultisample(fboTarget, GR_GL_COLOR_ATTACHMENT0,
                                                    glTex->target(), glTex->textureID(),
                                                    0, sampleCount));
        } else {
            GL_CALL(FramebufferTexture2D(fboTarget, GR_GL_COLOR_ATTACHMENT0,
                                         glTex->target(), glTex->textureID(), 0));
        }

        fDMSAARenderToTextureFBOIsMultisample = useMultisampleFBO;
        fNeedsStencilAttachmentBind[useMultisampleFBO] = true;
    }

    // 附加模板缓冲
    if (fNeedsStencilAttachmentBind[useMultisampleFBO]) {
        if (auto stencil = this->getStencilAttachment(useMultisampleFBO)) {
            const GrGLAttachment* glStencil = static_cast<const GrGLAttachment*>(stencil);
            GL_CALL(FramebufferRenderbuffer(fboTarget, GR_GL_STENCIL_ATTACHMENT,
                                            GR_GL_RENDERBUFFER, glStencil->renderbufferID()));

            // 如果是 packed depth-stencil 格式，同时附加深度
            if (GrGLFormatIsPackedDepthStencil(glStencil->format())) {
                GL_CALL(FramebufferRenderbuffer(fboTarget, GR_GL_DEPTH_ATTACHMENT,
                                                GR_GL_RENDERBUFFER, glStencil->renderbufferID()));
            }
        }
        fNeedsStencilAttachmentBind[useMultisampleFBO] = false;
    }
}
```

### 解析方向绑定

```cpp
void GrGLRenderTarget::bindForResolve(GrGLGpu::ResolveDirection resolveDirection) {
    SkASSERT(fMultisampleFBOID != 0);
    SkASSERT(!this->isMultisampledRenderToTexture());

    if (resolveDirection == GrGLGpu::ResolveDirection::kMSAAToSingle) {
        this->bindInternal(GR_GL_READ_FRAMEBUFFER, true);   // 从 MSAA 读取
        this->bindInternal(GR_GL_DRAW_FRAMEBUFFER, false);  // 写入单采样
    } else {
        SkASSERT(resolveDirection == GrGLGpu::ResolveDirection::kSingleToMSAA);
        this->bindInternal(GR_GL_READ_FRAMEBUFFER, false);  // 从单采样读取
        this->bindInternal(GR_GL_DRAW_FRAMEBUFFER, true);   // 写入 MSAA
    }
}
```

### 内存统计导出

```cpp
void GrGLRenderTarget::dumpMemoryStatistics(SkTraceMemoryDump* traceMemoryDump) const {
    bool refsWrappedRenderTargetObjects =
        this->fRTFBOOwnership == GrBackendObjectOwnership::kBorrowed;
    if (refsWrappedRenderTargetObjects && !traceMemoryDump->shouldDumpWrappedObjects()) {
        return;
    }

    // 计算非纹理采样数
    int numSamplesNotInTexture = fTotalMemorySamplesPerPixel;
    if (this->asTexture()) {
        --numSamplesNotInTexture;  // GrGLTexture 已统计 1 个采样
    }

    if (numSamplesNotInTexture >= 1) {
        size_t size = GrSurface::ComputeSize(this->backendFormat(),
                                             this->dimensions(),
                                             numSamplesNotInTexture,
                                             skgpu::Mipmapped::kNo);

        SkString resourceName = this->getResourceName();
        resourceName.append("/renderbuffer");

        this->dumpMemoryStatisticsPriv(traceMemoryDump, resourceName, "RenderTarget", size);

        // 关联 GL 渲染缓冲 ID
        SkString renderbuffer_id;
        renderbuffer_id.appendU32(fMSColorRenderbufferID);
        traceMemoryDump->setMemoryBacking(resourceName.c_str(), "gl_renderbuffer",
                                          renderbuffer_id.c_str());
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLGpu` | GPU 接口和 FBO 管理 |
| `GrGLAttachment` | 模板/深度附件 |
| `GrGLCaps` | OpenGL 能力查询 |
| `GrGLTexture` | 纹理对象（纹理渲染目标） |
| `GrResourceProvider` | 资源分配 |
| `GrBackendUtils` | 后端工具函数 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrGLOpsRenderPass` | 将该类作为渲染目标使用 |
| `GrGLTextureRenderTarget` | 继承该类 |
| `GrRenderTargetProxy` | 通过代理访问该类 |

## 设计模式与设计决策

### 1. 多态绑定策略

根据不同场景选择绑定目标：

```cpp
void bindForPixelOps(GrGLenum fboTarget) {
    this->bindInternal(fboTarget,
                       this->numSamples() > 1 && !this->isMultisampledRenderToTexture());
}
```

### 2. 延迟绑定模式

模板附件延迟到实际需要时才绑定：

```cpp
bool completeStencilAttachment(GrAttachment* stencil, bool useMultisampleFBO) {
    if (this->getStencilAttachment(useMultisampleFBO) != stencil) {
        fNeedsStencilAttachmentBind[useMultisampleFBO] = true;
    }
    return true;
}
```

### 3. 特殊值模式

使用特殊值表示不可解析 FBO：

```cpp
static constexpr GrGLuint kUnresolvableFBOID = 0;
```

### 4. 所有权管理

区分拥有和借用的资源：

```cpp
if (GrBackendObjectOwnership::kBorrowed != fRTFBOOwnership) {
    // 仅删除拥有的资源
    gpu->deleteFramebuffer(fSingleSampleFBOID);
}
```

## 性能考量

### 1. 状态缓存

通过 `fNeedsStencilAttachmentBind` 避免重复绑定：

```cpp
if (fNeedsStencilAttachmentBind[useMultisampleFBO]) {
    // 仅在必要时绑定
    fNeedsStencilAttachmentBind[useMultisampleFBO] = false;
}
```

### 2. DMSAA 优化

根据内容边界而非整个表面进行解析：

```cpp
if (!fGpu->glCaps().framebufferResolvesMustBeFullSize()) {
    return GrNativeRect::MakeRelativeTo(fOrigin, fRenderTarget->height(), fContentBounds);
}
```

### 3. 资源共享

对于自动解析的驱动，单采样和多重采样共用同一 FBO：

```cpp
if (resourceProvider->caps()->msaaResolvesAutomatically() && this->asTexture()) {
    fMultisampleFBOID = fSingleSampleFBOID;
    return true;
}
```

### 4. 内存占用缓存

预先计算并缓存内存采样数：

```cpp
fTotalMemorySamplesPerPixel = idDesc.fTotalMemorySamplesPerPixel;
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrRenderTarget.h` | 基类 | 渲染目标抽象 |
| `src/gpu/ganesh/gl/GrGLGpu.h` | 依赖 | GPU 接口 |
| `src/gpu/ganesh/gl/GrGLAttachment.h` | 依赖 | 附件管理 |
| `src/gpu/ganesh/gl/GrGLTextureRenderTarget.h` | 派生类 | 纹理渲染目标 |
| `src/gpu/ganesh/gl/GrGLTexture.h` | 依赖 | 纹理对象 |
| `src/gpu/ganesh/gl/GrGLCaps.h` | 依赖 | 能力查询 |
| `include/gpu/ganesh/gl/GrGLBackendSurface.h` | 依赖 | 后端表面创建 |
