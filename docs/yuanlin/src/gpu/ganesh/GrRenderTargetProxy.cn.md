# GrRenderTargetProxy

> 源文件
> - src/gpu/ganesh/GrRenderTargetProxy.h
> - src/gpu/ganesh/GrRenderTargetProxy.cpp

## 概述

`GrRenderTargetProxy` 是 Ganesh 延迟实例化系统中表示渲染目标的代理类。它延迟了 `GrRenderTarget` 的实际创建,直到真正需要时才分配 GPU 资源。这种设计允许 Skia 在记录绘制命令时避免立即分配 GPU 资源,从而优化资源使用和支持 DDL(延迟显示列表)。

主要功能包括:
- 延迟渲染目标的 GPU 资源分配
- 管理模板需求和 MSAA 配置
- 支持包装外部渲染目标
- 管理 Vulkan 次级命令缓冲区
- 提供每帧分配器(GrArenas)管理
- 追踪 MSAA 脏区域以优化解析

代理的唯一 ID 通常与最终实例化的 `GrRenderTarget` 的唯一 ID 不同,这是延迟实例化的固有特性。

## 架构位置

`GrRenderTargetProxy` 在 Ganesh 代理系统中的位置:

```
GrSurfaceProxy (表面代理基类)
    └── GrRenderTargetProxy (渲染目标代理)
        └── GrTextureRenderTargetProxy (纹理+渲染目标代理)

GrRenderTargetProxy 实例化后生成:
    └── GrRenderTarget (实际的 GPU 渲染目标)
```

它与 `GrRenderTask` 配合工作,表示任务的输出目标。

## 主要类与结构体

### GrRenderTargetProxy 类

**继承关系**:
- 虚继承自 `GrSurfaceProxy`
- 被 `GrTextureRenderTargetProxy` 继承

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fSampleCnt | int8_t | 采样数(MSAA) |
| fNeedsStencil | int8_t | 是否需要模板缓冲 |
| fWrapsVkSecondaryCB | WrapsVkSecondaryCB | 是否包装 Vulkan 次级命令缓冲 |
| fMSAADirtyRect | SkIRect | MSAA 脏矩形区域 |
| fArenas | sk_sp<GrArenas> | 每帧分配器 |
| fPadding[4] | char | 内存对齐填充 |

### GrArenas 类

管理每帧生命周期的分配器:

```cpp
class GrArenas : public SkNVRefCnt<GrArenas> {
public:
    SkArenaAlloc* arenaAlloc();
    sktext::gpu::SubRunAllocator* subRunAlloc();
    void flush();
};
```

**成员**:
- `fArenaAlloc`: 通用快速分配器(1024 字节初始)
- `fSubRunAllocator`: 文本子运行专用分配器(1024 字节初始)

### WrapsVkSecondaryCB 枚举

```cpp
enum class WrapsVkSecondaryCB : bool {
    kNo = false,
    kYes = true
};
```

标识是否包装 Vulkan 次级命令缓冲区。

## 公共 API 函数

### 类型转换

```cpp
GrRenderTargetProxy* asRenderTargetProxy() override;
const GrRenderTargetProxy* asRenderTargetProxy() const override;
```

### 实例化

```cpp
bool instantiate(GrResourceProvider*) override;
```

实际创建底层 `GrRenderTarget` 资源。

### 模板支持

```cpp
bool canUseStencil(const GrCaps& caps) const;
void setNeedsStencil();
int needsStencil() const;
```

管理模板缓冲需求。

### 采样配置

```cpp
int numSamples() const;  // 获取采样数
int maxWindowRectangles(const GrCaps& caps) const;  // 最大窗口矩形数
```

### 特殊标志查询

```cpp
bool glRTFBOIDIs0() const;  // OpenGL FBO ID 是否为 0
bool wrapsVkSecondaryCB() const;  // 是否包装 Vulkan 次级 CB
bool supportsVkInputAttachment() const;  // 支持 Vulkan 输入附件
```

### MSAA 脏区域管理

```cpp
void markMSAADirty(SkIRect dirtyRect);  // 标记脏区域
void markMSAAResolved();  // 标记已解析
bool isMSAADirty() const;  // 是否有脏区域
const SkIRect& msaaDirtyRect() const;  // 获取脏矩形
```

### 分配器管理

```cpp
sk_sp<GrArenas> arenas();  // 获取或创建分配器
void clearArenas();  // 清理分配器
```

### 资源追踪

```cpp
bool refsWrappedObjects() const;  // 是否引用包装对象
```

## 内部实现细节

### 构造函数实现

**延迟版本**(用于新创建的代理):

```cpp
GrRenderTargetProxy::GrRenderTargetProxy(
        const GrCaps& caps,
        const GrBackendFormat& format,
        SkISize dimensions,
        int sampleCount,
        SkBackingFit fit,
        skgpu::Budgeted budgeted,
        GrProtected isProtected,
        GrInternalSurfaceFlags surfaceFlags,
        UseAllocator useAllocator,
        std::string_view label)
        : INHERITED(format, dimensions, fit, budgeted,
                    isProtected, surfaceFlags, useAllocator, label)
        , fSampleCnt(sampleCount)
        , fWrapsVkSecondaryCB(WrapsVkSecondaryCB::kNo) {}
```

**包装版本**(用于包装现有 Surface):

```cpp
GrRenderTargetProxy::GrRenderTargetProxy(
        sk_sp<GrSurface> surf,
        UseAllocator useAllocator,
        WrapsVkSecondaryCB wrapsVkSecondaryCB)
        : INHERITED(std::move(surf), SkBackingFit::kExact, useAllocator)
        , fSampleCnt(fTarget->asRenderTarget()->numSamples())
        , fWrapsVkSecondaryCB(wrapsVkSecondaryCB) {
    // 验证 MSAA 解析标志的一致性
    SkASSERT(!(this->numSamples() <= 1 ||
               fTarget->getContext()->priv().caps()->msaaResolvesAutomatically())
             || !this->requiresManualMSAAResolve());
}
```

### 实例化逻辑

```cpp
bool GrRenderTargetProxy::instantiate(GrResourceProvider* resourceProvider) {
    if (this->isLazy()) {
        return false;  // 懒代理不在这里实例化
    }
    if (!this->instantiateImpl(resourceProvider, fSampleCnt,
                               GrRenderable::kYes,
                               skgpu::Mipmapped::kNo, nullptr)) {
        return false;
    }
    SkASSERT(this->peekRenderTarget());
    SkASSERT(!this->peekTexture());  // 纯渲染目标
    return true;
}
```

### 模板可用性检查

```cpp
bool GrRenderTargetProxy::canUseStencil(const GrCaps& caps) const {
    if (caps.avoidStencilBuffers() || this->wrapsVkSecondaryCB()) {
        return false;
    }
    if (!this->isInstantiated()) {
        // 对于 OpenGL 懒代理,可能包装无模板的目标
        if (this->isLazy() &&
            this->backendFormat().backend() == GrBackendApi::kOpenGL) {
            return SkToBool(this->asTextureProxy());  // 保守判断
        }
        return true;  // 内部创建的目标可以附加模板
    }
    // 已实例化,直接询问实际目标
    GrRenderTarget* rt = this->peekRenderTarget();
    bool useMSAASurface = rt->numSamples() > 1;
    return rt->getStencilAttachment(useMSAASurface) ||
           rt->canAttemptStencilAttachment(useMSAASurface);
}
```

### GPU 内存大小估算

```cpp
size_t GrRenderTargetProxy::onUninstantiatedGpuMemorySize() const {
    int colorSamplesPerPixel = this->numSamples();
    if (colorSamplesPerPixel > 1) {
        ++colorSamplesPerPixel;  // 加上 resolve 缓冲
    }
    return GrSurface::ComputeSize(
        this->backendFormat(),
        this->dimensions(),
        colorSamplesPerPixel,
        skgpu::Mipmapped::kNo,
        !this->priv().isExact());
}
```

### 分配器生命周期管理

```cpp
sk_sp<GrArenas> arenas() {
    if (fArenas == nullptr) {
        fArenas = sk_make_sp<GrArenas>();
    }
    return fArenas;
}

void clearArenas() {
    if (fArenas != nullptr) {
        fArenas->flush();  // 标记为已刷新
    }
    fArenas = nullptr;  // 释放引用
}
```

分配器在第一次 `OpsTask` 调用时创建,在第一个任务执行完成后清理。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| GrSurfaceProxy | 基类,表面代理抽象 |
| GrRenderTarget | 实例化后的目标资源 |
| GrResourceProvider | 资源创建和管理 |
| GrCaps | GPU 能力查询 |
| SkArenaAlloc | 快速内存分配 |
| sktext::gpu::SubRunAllocator | 文本分配 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| GrRenderTask | 使用代理作为渲染目标 |
| GrOpsTask | 管理代理的分配器 |
| GrSurfaceProxyView | 包含代理和视图配置 |
| GrTextureRenderTargetProxy | 继承,同时是纹理和渲染目标 |
| SurfaceFillContext/SurfaceDrawContext | 使用代理进行绘制 |

## 设计模式与设计决策

### 代理模式(Proxy Pattern)

延迟实际 `GrRenderTarget` 的创建:
- 在记录阶段使用代理
- 在刷新阶段实例化真实对象
- 透明访问接口

### 虚继承解决菱形继承

`GrTextureRenderTargetProxy` 需要同时继承 `GrTextureProxy` 和 `GrRenderTargetProxy`,使用虚继承避免 `GrSurfaceProxy` 重复。

### 资源生命周期分离

分配器(Arenas)与代理生命周期分离:
- 代理:长期存在(整个记录阶段)
- 分配器:每帧刷新后清理

### MSAA 脏区域追踪

精确追踪脏区域,优化 MSAA 解析:
- 仅解析脏区域
- 减少带宽消耗

### 内存对齐填充

添加 4 字节填充确保 `GrTextureRenderTargetProxy` 的正确内存对齐,避免 ASAN 警告。

## 性能考量

### 延迟资源分配

避免不必要的 GPU 资源创建:
- 可能被优化掉的渲染目标不会创建
- 支持资源复用和合并

### 分配器优化

- `SkArenaAlloc`:线性分配,极快
- `SubRunAllocator`:针对文本优化的析构语义
- 按帧批量释放,避免逐个释放开销

### 脏区域追踪

`fMSAADirtyRect` 最小化 MSAA 解析区域,节省带宽和时间。

### 惰性分配器创建

分配器按需创建(`arenas()` 检查 null),未使用的代理不产生开销。

### 紧凑内存布局

使用 `int8_t` 存储采样数和模板标志,节省内存。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/gpu/ganesh/GrSurfaceProxy.h/cpp | 基类 | 表面代理基类 |
| src/gpu/ganesh/GrRenderTarget.h/cpp | 实例化目标 | 实际的渲染目标 |
| src/gpu/ganesh/GrTextureRenderTargetProxy.h | 子类 | 纹理+渲染目标代理 |
| src/gpu/ganesh/GrResourceProvider.h/cpp | 依赖 | 资源创建 |
| src/gpu/ganesh/GrCaps.h | 依赖 | GPU 能力 |
| src/gpu/ganesh/GrRenderTask.h/cpp | 使用者 | 渲染任务系统 |
| src/gpu/ganesh/ops/OpsTask.h/cpp | 使用者 | 操作任务 |
| src/base/SkArenaAlloc.h | 组件 | 快速分配器 |
| src/text/gpu/SubRunAllocator.h | 组件 | 文本子运行分配器 |
| src/gpu/ganesh/GrSurfaceProxyView.h | 使用者 | 表面视图 |
