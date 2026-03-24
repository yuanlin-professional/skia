# GrMtlTextureRenderTarget

> 源文件
> - src/gpu/ganesh/mtl/GrMtlTextureRenderTarget.h
> - src/gpu/ganesh/mtl/GrMtlTextureRenderTarget.mm

## 概述

`GrMtlTextureRenderTarget` 是 Metal 后端的双用途表面类，同时作为纹理和渲染目标使用。该类通过多重继承 `GrMtlTexture` 和 `GrMtlRenderTarget`，实现了纹理采样和渲染目标绘制的统一管理。支持 MSAA（多重采样抗锯齿），自动创建 MSAA 颜色附件和解析附件，并正确计算 GPU 内存占用，避免重复计数。这是 Metal 后端中渲染到纹理（render-to-texture）场景的核心类。

## 架构位置

- **模块层级**：`src/gpu/ganesh/mtl/` - Ganesh Metal 后端
- **继承关系**：`GrMtlTextureRenderTarget` -> (`GrMtlTexture`, `GrMtlRenderTarget`)
- **使用场景**：离屏渲染、后处理效果、纹理生成

## 主要类与结构体

### GrMtlTextureRenderTarget

```cpp
class GrMtlTextureRenderTarget : public GrMtlTexture, public GrMtlRenderTarget
```

多重继承两个基类，整合纹理和渲染目标功能。

**工厂方法**：
- `MakeNewTextureRenderTarget` - 创建新表面
- `MakeWrappedTextureRenderTarget` - 包装外部纹理

## 公共 API 函数

### MakeNewTextureRenderTarget

```cpp
static sk_sp<GrMtlTextureRenderTarget> MakeNewTextureRenderTarget(
    GrMtlGpu*, skgpu::Budgeted, SkISize, int sampleCnt,
    MTLPixelFormat, uint32_t mipLevels, GrMipmapStatus, std::string_view label)
```

**MSAA 处理**：
- `sampleCnt == 1`：纹理直接作为颜色附件
- `sampleCnt > 1`：创建 MSAA 附件 + 纹理作为解析附件

### MakeWrappedTextureRenderTarget

包装外部 Metal 纹理为双用途表面，推断 Mipmap 状态为 `kDirty`（需要生成）。

## 内部实现细节

### MSAA 附件创建

**create_rt_attachments 辅助函数**：
```cpp
bool create_rt_attachments(GrMtlGpu* gpu, SkISize dimensions, MTLPixelFormat format,
                           int sampleCnt, sk_sp<GrMtlAttachment> texture,
                           sk_sp<GrMtlAttachment>* colorAttachment,
                           sk_sp<GrMtlAttachment>* resolveAttachment) {
    if (sampleCnt > 1) {
        // 创建 MSAA 附件
        auto msaaAttachment = rp->makeMSAAAttachment(dimensions, format, sampleCnt, ...);
        *colorAttachment = msaaAttachment;
        *resolveAttachment = texture;  // 纹理作为解析目标
    } else {
        *colorAttachment = texture;  // 直接使用纹理
    }
}
```

### GPU 内存计算

**onGpuMemorySize 实现**：
```cpp
size_t onGpuMemorySize() const override {
    // 仅计算纹理部分（含 Mipmap）
    return GrSurface::ComputeSize(backendFormat(), dimensions(),
                                  1, mipmapped());
}
```

**设计理由**：
- MSAA 附件单独缓存和计数
- 避免双重计数纹理内存
- 纹理附件标记为零大小（不重复计数）

### 资源释放

```cpp
void onRelease() override {
    GrMtlRenderTarget::onRelease();
    GrMtlTexture::onRelease();
}
void onAbandon() override {
    GrMtlRenderTarget::onAbandon();
    GrMtlTexture::onAbandon();
}
```

按顺序释放两个基类的资源。

### 标签设置

```cpp
void onSetLabel() override {
    GrMtlRenderTarget::onSetLabel();
    GrMtlTexture::onSetLabel();
}
```

同时设置渲染目标和纹理标签。

## 设计模式与设计决策

### 多重继承

使用多重继承统一纹理和渲染目标接口，避免重复代码，但需小心处理菱形继承（通过虚继承 `GrSurface` 解决）。

### 附件分离

- 纹理附件：供着色器采样
- 颜色附件：渲染目标（MSAA 时为独立附件）
- 解析附件：MSAA 解析目标（即纹理）

### 内存计数策略

纹理报告内存，附件不报告，避免重复计数，简化资源管理。

## 性能考量

### MSAA 优化

仅在需要时创建 MSAA 附件，`sampleCnt == 1` 时直接使用纹理，减少内存占用。

### 缓存集成

支持预算管理和包装缓存，与 Skia 资源系统无缝集成。

## 相关文件

- `src/gpu/ganesh/mtl/GrMtlTexture.h/mm` - 纹理基类
- `src/gpu/ganesh/mtl/GrMtlRenderTarget.h/mm` - 渲染目标基类
- `src/gpu/ganesh/mtl/GrMtlAttachment.h/mm` - Metal 附件
