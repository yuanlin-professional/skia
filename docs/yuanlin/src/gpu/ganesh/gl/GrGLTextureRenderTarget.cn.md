# GrGLTextureRenderTarget

> 源文件
> - src/gpu/ganesh/gl/GrGLTextureRenderTarget.h
> - src/gpu/ganesh/gl/GrGLTextureRenderTarget.cpp

## 概述

`GrGLTextureRenderTarget` 是 Skia Ganesh OpenGL 后端中同时支持纹理和渲染目标功能的类。它通过多重继承同时继承 `GrGLTexture` 和 `GrGLRenderTarget`，表示既可以作为渲染目标绘制内容，又可以作为纹理在后续绘制中使用的 GPU 资源。

该类解决了菱形继承问题（通过虚继承 `GrSurface`），并提供统一的内存管理、标签设置和模板附件支持。它是 Skia 中实现"渲染到纹理"（Render-to-Texture）功能的核心类。

## 架构位置

```
            GrSurface (虚继承)
           /         \
    GrTexture      GrRenderTarget
          |             |
    GrGLTexture   GrGLRenderTarget
           \         /
        GrGLTextureRenderTarget

使用场景:
离屏渲染 -> GrGLTextureRenderTarget -> 作为纹理采样
```

该类位于 Ganesh 图形栈的表面管理层，是纹理和渲染目标的组合实现。

## 主要类与结构体

### GrGLTextureRenderTarget

**继承关系:**
- 继承自: `GrGLTexture`, `GrGLRenderTarget`
- 间接继承: `GrSurface` (虚继承)

**无额外成员变量** - 所有数据来自基类

## 公共 API 函数

### 工厂方法
- `static sk_sp<GrGLTextureRenderTarget> MakeWrapped(...)` - 包装外部纹理和 FBO

### 构造
- `GrGLTextureRenderTarget(GrGLGpu*, skgpu::Budgeted, int sampleCount, const GrGLTexture::Desc&, const GrGLRenderTarget::IDs&, GrMipmapStatus, std::string_view label)` - 创建新对象

### 模板支持
- `bool canAttemptStencilAttachment(bool useMultisampleFBO) const` - 是否可以附加模板

### 后端格式
- `GrBackendFormat backendFormat() const` - 获取后端格式（使用纹理路径）

### 内存统计
- `void dumpMemoryStatistics(SkTraceMemoryDump*) const` - 导出内存统计

### 生命周期管理
- `void onAbandon()` - 放弃 GL 对象
- `void onRelease()` - 释放 GL 对象
- `void onSetLabel()` - 设置调试标签

## 内部实现细节

### 构造函数（自有资源）

```cpp
GrGLTextureRenderTarget::GrGLTextureRenderTarget(GrGLGpu* gpu,
                                                 skgpu::Budgeted budgeted,
                                                 int sampleCount,
                                                 const GrGLTexture::Desc& texDesc,
                                                 const GrGLRenderTarget::IDs& rtIDs,
                                                 GrMipmapStatus mipmapStatus,
                                                 std::string_view label)
        // 显式调用虚基类构造函数
        : GrSurface(gpu, texDesc.fSize, texDesc.fIsProtected, label)
        , GrGLTexture(gpu, texDesc, nullptr, mipmapStatus, label)
        , GrGLRenderTarget(gpu, texDesc.fSize, texDesc.fFormat, sampleCount, rtIDs,
                           texDesc.fIsProtected, label) {
    this->registerWithCache(budgeted);
}
```

**注意**:
- 必须显式调用 `GrSurface` 构造函数（虚基类）
- 纹理和渲染目标共享同一尺寸和保护状态

### 包装外部资源

```cpp
GrGLTextureRenderTarget::GrGLTextureRenderTarget(GrGLGpu* gpu,
                                                 int sampleCount,
                                                 const GrGLTexture::Desc& texDesc,
                                                 sk_sp<GrGLTextureParameters> parameters,
                                                 const GrGLRenderTarget::IDs& rtIDs,
                                                 GrWrapCacheable cacheable,
                                                 GrMipmapStatus mipmapStatus,
                                                 std::string_view label)
        : GrSurface(gpu, texDesc.fSize, texDesc.fIsProtected, label)
        , GrGLTexture(gpu, texDesc, std::move(parameters), mipmapStatus, label)
        , GrGLRenderTarget(gpu, texDesc.fSize, texDesc.fFormat, sampleCount, rtIDs,
                           texDesc.fIsProtected, label) {
    this->registerWithCacheWrapped(cacheable);
}
```

### 内存统计（非 Android 框架）

```cpp
void GrGLTextureRenderTarget::dumpMemoryStatistics(
    SkTraceMemoryDump* traceMemoryDump) const {
#ifndef SK_BUILD_FOR_ANDROID_FRAMEWORK
    // 委托给基类，分别统计纹理和渲染缓冲
    GrGLRenderTarget::dumpMemoryStatistics(traceMemoryDump);
    GrGLTexture::dumpMemoryStatistics(traceMemoryDump);
#else
    // Android 框架特殊处理：合并统计
    SkString resourceName = this->getResourceName();
    resourceName.append("/texture_renderbuffer");
    this->dumpMemoryStatisticsPriv(traceMemoryDump, resourceName, "RenderTarget",
                                   this->gpuMemorySize());
#endif
}
```

### 模板附件支持

```cpp
bool GrGLTextureRenderTarget::canAttemptStencilAttachment(bool useMultisampleFBO) const {
    // 该类的 RT FBO 从不由包装的 FBO 创建，因此总是可以附加模板
    SkASSERT(!this->getGpu()->getContext()->priv().caps()->avoidStencilBuffers());
    return true;
}
```

### 资源释放

```cpp
void GrGLTextureRenderTarget::onAbandon() {
    GrGLRenderTarget::onAbandon();  // 先释放 RT
    GrGLTexture::onAbandon();       // 再释放纹理
}

void GrGLTextureRenderTarget::onRelease() {
    GrGLRenderTarget::onRelease();  // 先释放 RT
    GrGLTexture::onRelease();       // 再释放纹理
}
```

### 标签设置

```cpp
void GrGLTextureRenderTarget::onSetLabel() {
    GrGLTexture::onSetLabel();  // 仅设置纹理标签（RT 无需单独标签）
}
```

### GPU 内存大小计算

```cpp
size_t GrGLTextureRenderTarget::onGpuMemorySize() const {
    return GrSurface::ComputeSize(this->backendFormat(), this->dimensions(),
                                  this->totalMemorySamplesPerPixel(), this->mipmapped());
}
```

**说明**:
- 使用 `totalMemorySamplesPerPixel()` 包含所有采样（纹理 + MSAA 缓冲）
- 自动处理 mipmap 的额外内存

### 工厂方法实现

```cpp
sk_sp<GrGLTextureRenderTarget> GrGLTextureRenderTarget::MakeWrapped(
        GrGLGpu* gpu,
        int sampleCount,
        const GrGLTexture::Desc& texDesc,
        sk_sp<GrGLTextureParameters> parameters,
        const GrGLRenderTarget::IDs& rtIDs,
        GrWrapCacheable cacheable,
        GrMipmapStatus mipmapStatus,
        std::string_view label) {
    return sk_sp<GrGLTextureRenderTarget>(
            new GrGLTextureRenderTarget(gpu,
                                        sampleCount,
                                        texDesc,
                                        std::move(parameters),
                                        rtIDs,
                                        cacheable,
                                        mipmapStatus,
                                        label));
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLTexture` | 纹理功能基类 |
| `GrGLRenderTarget` | 渲染目标功能基类 |
| `GrGLGpu` | GPU 接口 |
| `GrSurface` | 表面基类（虚继承） |
| `GrCaps` | 能力查询 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrRenderTargetProxy` | 通过代理访问 |
| `GrTextureProxy` | 通过代理访问 |

## 设计模式与设计决策

### 1. 多重继承 + 虚继承

解决菱形继承问题：

```cpp
        GrSurface (虚基类)
       /         \
GrTexture      GrRenderTarget
      |             |
GrGLTexture   GrGLRenderTarget
       \         /
    GrGLTextureRenderTarget
```

**关键点**:
- `GrSurface` 必须虚继承，避免重复基类
- 构造函数必须显式调用虚基类构造函数

### 2. 资源共享

纹理和渲染目标共享同一 GL 纹理对象：

```cpp
// 纹理 ID 和 FBO 的 color attachment 都指向同一个 GL texture
GrGLuint textureID = ...;
glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, textureID, 0);
```

### 3. 委托模式

大部分功能委托给基类：

```cpp
void onRelease() {
    GrGLRenderTarget::onRelease();
    GrGLTexture::onRelease();
}
```

### 4. Windows 编译器警告抑制

```cpp
#ifdef SK_BUILD_FOR_WIN
#pragma warning(push)
#pragma warning(disable: 4250)  // 禁用 dominance 警告
#endif

class GrGLTextureRenderTarget : public GrGLTexture, public GrGLRenderTarget { ... };

#ifdef SK_BUILD_FOR_WIN
#pragma warning(pop)
#endif
```

**原因**: MSVC 对多重继承中的虚函数覆盖有虚假警告

## 性能考量

### 1. 内存共享

纹理和渲染目标共享内存：

```cpp
// 不需要额外的颜色缓冲，直接渲染到纹理
size_t memory = textureSize;  // 无需 + renderTargetSize
```

### 2. 无额外成员变量

```cpp
// sizeof(GrGLTextureRenderTarget) ≈ sizeof(GrGLTexture) + sizeof(GrGLRenderTarget)
// 虚继承使 GrSurface 只存储一次
```

### 3. 模板附件优化

总是允许附加模板（无需检查）：

```cpp
bool canAttemptStencilAttachment(bool useMultisampleFBO) const {
    return true;  // 始终允许
}
```

### 4. 后端格式查询优化

直接使用纹理路径（避免 RT 路径的额外开销）：

```cpp
GrBackendFormat backendFormat() const {
    return GrGLTexture::backendFormat();  // 优先纹理路径
}
```

## 使用场景

### 1. 离屏渲染

```cpp
// 创建离屏渲染目标
auto rt = GrGLTextureRenderTarget::Make(...);

// 渲染到该目标
canvas->render(rt);

// 使用结果纹理
shader->setTexture(rt->asTexture());
```

### 2. 后处理效果

```cpp
// Pass 1: 渲染场景到纹理
renderScene(sceneRT);

// Pass 2: 应用模糊效果
blurShader->setInput(sceneRT->asTexture());
blurShader->render(blurRT);

// Pass 3: 合成到屏幕
compositeShader->setInput(blurRT->asTexture());
compositeShader->render(screenRT);
```

### 3. Mipmap 生成

```cpp
// 渲染完整分辨率
renderFullRes(textureRT);

// 生成 mipmap
gpu->generateMipmaps(textureRT->asTexture());

// 使用带 mipmap 的纹理
drawWithMipmaps(textureRT->asTexture());
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/gl/GrGLTexture.h` | 基类 | 纹理功能 |
| `src/gpu/ganesh/gl/GrGLRenderTarget.h` | 基类 | 渲染目标功能 |
| `src/gpu/ganesh/GrSurface.h` | 虚基类 | 表面抽象 |
| `src/gpu/ganesh/gl/GrGLGpu.h` | 依赖 | GPU 接口 |
| `src/gpu/ganesh/GrCaps.h` | 依赖 | 能力查询 |
| `include/core/SkTraceMemoryDump.h` | 依赖 | 内存统计接口 |

## 总结

`GrGLTextureRenderTarget` 通过精心设计的多重继承和虚继承机制，实现了纹理和渲染目标功能的完美融合。它是 Skia "渲染到纹理" 功能的基石，广泛用于离屏渲染、后处理效果和复杂的多通道渲染场景。其设计充分考虑了内存效率、平台兼容性和性能优化，是 Skia GPU 后端架构的重要组成部分。
