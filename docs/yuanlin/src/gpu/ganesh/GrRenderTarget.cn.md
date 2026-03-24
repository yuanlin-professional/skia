# GrRenderTarget

> 源文件
> - src/gpu/ganesh/GrRenderTarget.h
> - src/gpu/ganesh/GrRenderTarget.cpp

## 概述

`GrRenderTarget` 表示一个可以被渲染的 2D 像素缓冲区,是 Ganesh GPU 后端渲染系统中的核心抽象。它继承自 `GrSurface`,代表了可以作为渲染目标的 GPU 表面资源。

主要功能包括:
- 管理颜色缓冲区和模板附件
- 支持 MSAA(多重采样抗锯齿)渲染
- 处理模板缓冲区的附加和查询
- 提供后端渲染目标的抽象接口
- 管理采样模式和采样位置

渲染目标可以通过多种方式创建:
1. 通过 `GrContext::createTexture` 使用 `kRenderTarget_SurfaceFlag` 标志
2. 包装外部创建的渲染目标
3. 作为纹理渲染目标(TextureRenderTarget)同时支持采样和渲染

## 架构位置

`GrRenderTarget` 在 Ganesh 架构中的位置:

```
GrGpuResource (资源管理)
    └── GrSurface (表面抽象)
        └── GrRenderTarget (渲染目标)
            ├── GrTextureRenderTarget (纹理+渲染目标)
            └── 后端特定实现 (GrGLRenderTarget, GrVkRenderTarget 等)
```

它通过 `GrRenderTargetProxy` 在延迟实例化系统中表示。

## 主要类与结构体

### GrRenderTarget 类

**继承关系**:
- 继承自 `GrSurface` (虚继承,支持多重继承)
- 被 `GrTextureRenderTarget` 继承(同时是纹理和渲染目标)
- 各平台有具体实现(GrGLRenderTarget、GrVkRenderTarget、GrMtlRenderTarget 等)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fStencilAttachment | sk_sp<GrAttachment> | 标准渲染的模板附件 |
| fMSAAStencilAttachment | sk_sp<GrAttachment> | MSAA 渲染的模板附件 |
| fSampleCnt | int | 颜色缓冲区的采样数(非 MSAA 为 1) |

## 公共 API 函数

### 类型转换

```cpp
GrRenderTarget* asRenderTarget() override;
const GrRenderTarget* asRenderTarget() const override;
```

安全地将 `GrSurface` 转换为 `GrRenderTarget`。

### 采样相关

```cpp
int numSamples() const;  // 获取采样数
bool alwaysClearStencil() const;  // 是否总是清除模板
```

### 模板附件管理

```cpp
GrAttachment* getStencilAttachment(bool useMSAASurface) const;
GrAttachment* getStencilAttachment() const;
void attachStencilAttachment(sk_sp<GrAttachment> stencil, bool useMSAASurface);
bool canAttemptStencilAttachment(bool useMSAASurface) const;
int numStencilBits(bool useMSAASurface) const;
```

管理标准和 MSAA 模板附件的生命周期。

### 采样模式

```cpp
int getSamplePatternKey();  // 获取采样模式唯一键(必须是多采样)
const skia_private::TArray<SkPoint>& getSampleLocations();
```

获取硬件采样位置,用于高级渲染技术。

### 后端接口

```cpp
virtual GrBackendRenderTarget getBackendRenderTarget() const = 0;
```

纯虚函数,子类实现返回后端特定的渲染目标描述。

### 手动 MSAA 解析

```cpp
using GrSurface::setRequiresManualMSAAResolve;
using GrSurface::requiresManualMSAAResolve;
```

某些平台需要手动解析 MSAA,这些方法管理该状态。

## 内部实现细节

### 构造函数逻辑

```cpp
GrRenderTarget::GrRenderTarget(GrGpu* gpu,
                               const SkISize& dimensions,
                               int sampleCount,
                               GrProtected isProtected,
                               std::string_view label,
                               sk_sp<GrAttachment> stencil)
        : INHERITED(gpu, dimensions, isProtected, label)
        , fSampleCnt(sampleCount) {
    if (this->numSamples() > 1) {
        fMSAAStencilAttachment = std::move(stencil);
    } else {
        fStencilAttachment = std::move(stencil);
    }
}
```

根据采样数决定模板附件存储位置:
- 多采样(> 1):使用 `fMSAAStencilAttachment`
- 单采样(= 1):使用 `fStencilAttachment`

### 资源释放

```cpp
void GrRenderTarget::onRelease() {
    fStencilAttachment = nullptr;
    fMSAAStencilAttachment = nullptr;
    INHERITED::onRelease();
}

void GrRenderTarget::onAbandon() {
    fStencilAttachment = nullptr;
    fMSAAStencilAttachment = nullptr;
    INHERITED::onAbandon();
}
```

在资源释放或放弃时清理模板附件。

### 模板附件附加

```cpp
void GrRenderTarget::attachStencilAttachment(sk_sp<GrAttachment> stencil,
                                             bool useMSAASurface) {
    auto stencilAttachment = (useMSAASurface)
        ? &GrRenderTarget::fMSAAStencilAttachment
        : &GrRenderTarget::fStencilAttachment;

    if (!stencil && !(this->*stencilAttachment)) {
        return;  // 无需工作
    }

    if (!this->completeStencilAttachment(stencil.get(), useMSAASurface)) {
        return;  // 后端附加失败
    }

    this->*stencilAttachment = std::move(stencil);
}
```

使用成员指针优雅地处理 MSAA 和非 MSAA 情况。

### 模板位数查询

```cpp
int GrRenderTarget::numStencilBits(bool useMSAASurface) const {
    return GrBackendFormatStencilBits(
        this->getStencilAttachment(useMSAASurface)->backendFormat());
}
```

从后端格式提取模板位数信息。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| GrSurface | 基类,提供表面抽象 |
| GrAttachment | 模板附件资源 |
| GrBackendUtils | 后端格式工具函数 |
| GrGpu | GPU 设备接口 |
| SkISize | 尺寸表示 |
| SkPoint | 采样位置表示 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| GrRenderTargetProxy | 延迟实例化的渲染目标代理 |
| GrTextureRenderTarget | 同时是纹理和渲染目标 |
| GrOpsTask | 使用渲染目标执行绘制操作 |
| GrSurfaceDrawContext | 高层绘制上下文 |
| 后端实现 | GrGLRenderTarget、GrVkRenderTarget 等 |

## 设计模式与设计决策

### 虚继承

使用虚继承支持 `GrTextureRenderTarget` 的菱形继承:

```
    GrSurface
    /        \
GrTexture  GrRenderTarget
    \        /
 GrTextureRenderTarget
```

避免基类 `GrSurface` 的重复实例。

### 模板方法模式

`attachStencilAttachment` 调用纯虚函数 `completeStencilAttachment`,由子类实现平台特定逻辑。

### 资源管理

使用 `sk_sp<GrAttachment>` 智能指针自动管理模板附件生命周期。

### 分离标准和 MSAA 模板

维护两个独立的模板附件指针,支持:
- 使用 DMSAA 时需要不同的模板配置
- 某些平台对 MSAA 和非 MSAA 模板有不同要求

### 延迟采样位置查询

采样位置按需查询(`getSampleLocations`),避免不必要的开销。

## 性能考量

### 模板附件缓存

避免重复附加相同的模板附件:

```cpp
if (!stencil && !(this->*stencilAttachment)) {
    return;  // 快速退出
}
```

### 内联访问器

`numSamples()` 等简单访问器内联,无函数调用开销。

### 智能指针开销

使用 `sk_sp` 引用计数,但在移动语义下开销最小。

### 采样位置缓存

`getSampleLocations()` 返回 const 引用,避免拷贝。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/gpu/ganesh/GrSurface.h/cpp | 基类 | 表面抽象基类 |
| src/gpu/ganesh/GrAttachment.h/cpp | 组件 | 模板/颜色附件 |
| src/gpu/ganesh/GrRenderTargetProxy.h/cpp | 代理 | 延迟实例化代理 |
| src/gpu/ganesh/GrTextureRenderTarget.h | 子类 | 纹理+渲染目标 |
| src/gpu/ganesh/gl/GrGLRenderTarget.h/cpp | 子类 | OpenGL 实现 |
| src/gpu/ganesh/vk/GrVkRenderTarget.h/cpp | 子类 | Vulkan 实现 |
| src/gpu/ganesh/mtl/GrMtlRenderTarget.h/mm | 子类 | Metal 实现 |
| src/gpu/ganesh/d3d/GrD3DRenderTarget.h/cpp | 子类 | Direct3D 实现 |
| src/gpu/ganesh/GrBackendUtils.h/cpp | 工具 | 后端格式工具 |
