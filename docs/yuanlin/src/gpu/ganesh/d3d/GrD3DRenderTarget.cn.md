# GrD3DRenderTarget

> 源文件
> - src/gpu/ganesh/d3d/GrD3DRenderTarget.h
> - src/gpu/ganesh/d3d/GrD3DRenderTarget.cpp

## 概述

`GrD3DRenderTarget` 是 Skia 图形库中 Ganesh D3D 后端的渲染目标封装类,继承自 `GrRenderTarget`,表示可以作为渲染输出的 D3D12 纹理资源。该类管理渲染目标视图(RTV)、深度模板视图(DSV)和 MSAA 解析纹理,提供了 D3D12 渲染目标的完整抽象。

## 架构位置

```
Skia
└── src/gpu/ganesh
    ├── GrRenderTarget (抽象渲染目标基类)
    │   └── GrD3DRenderTarget (D3D12实现) ← 核心类
    │       ├── GrD3DTextureResource (纹理资源)
    │       └── GrD3DAttachment (深度模板附件)
    └── d3d
        ├── GrD3DTexture (可包含渲染目标)
        └── GrD3DTextureRenderTarget (纹理+渲染目标组合)
```

## 主要类与结构体

### GrD3DRenderTarget

**继承关系**:
- 继承自: `GrRenderTarget`, `GrD3DTextureResource`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fColorRenderTargetView` | `GrD3DDescriptorHeap::CPUHandle` | 颜色渲染目标视图(RTV) |
| `fResolveRenderTargetView` | `GrD3DDescriptorHeap::CPUHandle` | MSAA解析渲染目标视图 |
| `fMSAATextureResource` | `sk_sp<GrD3DTextureResource>` | MSAA纹理资源(多采样时使用) |
| `fCachedStencilAttachment` | `sk_sp<GrD3DAttachment>` | 缓存的深度模板附件 |

## 公共 API 函数

```cpp
// 创建渲染目标
static sk_sp<GrD3DRenderTarget> MakeWrappedRenderTarget(GrD3DGpu* gpu,
                                                         SkISize dimensions,
                                                         int sampleCnt,
                                                         const GrD3DTextureResourceInfo& info);

// 获取渲染目标视图
GrD3DDescriptorHeap::CPUHandle colorRenderTargetView() const;

// 获取MSAA纹理资源(如果有)
GrD3DTextureResource* msaaTextureResource() const;

// 获取深度模板附件
GrD3DAttachment* getStencilAttachment() const;

// 解析MSAA(如果需要)
void onResolve();
```

## 内部实现细节

### 渲染目标创建

```cpp
sk_sp<GrD3DRenderTarget> MakeWrappedRenderTarget(...) {
    // 1. 创建渲染目标视图(RTV)
    GrD3DDescriptorHeap::CPUHandle rtvHandle =
        gpu->resourceProvider().createRenderTargetView(resource);
    
    // 2. 如果是MSAA,创建MSAA纹理和视图
    sk_sp<GrD3DTextureResource> msaaResource;
    if (sampleCnt > 1) {
        msaaResource = createMSAATexture(...);
    }
    
    // 3. 创建渲染目标对象
    return sk_sp<GrD3DRenderTarget>(
        new GrD3DRenderTarget(gpu, dimensions, sampleCnt,
                             info, rtvHandle, msaaResource));
}
```

### MSAA 解析

```cpp
void onResolve() {
    if (fMSAATextureResource && this != fMSAATextureResource.get()) {
        // 解析MSAA纹理到单采样纹理
        gpu->resolveTexture(this, fMSAATextureResource.get(), resolveRect);
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrRenderTarget` | 渲染目标抽象基类 |
| `GrD3DTextureResource` | D3D12纹理资源基类 |
| `GrD3DAttachment` | 深度模板附件 |
| `ID3D12Resource` | D3D12资源 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrD3DOpsRenderPass` | 设置渲染目标 |
| `GrD3DGpu` | 创建和管理渲染目标 |
| `GrD3DTextureRenderTarget` | 组合纹理和渲染目标 |

## 设计模式与设计决策

### 组合模式

组合纹理资源和渲染目标功能:
- 支持纹理即渲染目标
- 代码复用
- 清晰的继承关系

### 延迟解析

MSAA解析在需要时才执行:
- 减少不必要的解析
- 优化性能
- 支持多次绘制

## 性能考量

### MSAA 纹理分离

MSAA纹理与解析纹理分离存储:
- 避免频繁解析
- 支持延迟解析
- 减少内存带宽

### 视图缓存

缓存RTV和DSV:
- 避免重复创建
- 减少描述符开销
- 提高渲染效率

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrRenderTarget.h` | 基类 | 抽象渲染目标 |
| `src/gpu/ganesh/d3d/GrD3DTextureResource.h/cpp` | 基类 | D3D12纹理资源 |
| `src/gpu/ganesh/d3d/GrD3DAttachment.h/cpp` | 组件 | 深度模板附件 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h/cpp` | 使用者 | GPU设备 |
