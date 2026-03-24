# GrSurface

> 源文件
> - src/gpu/ganesh/GrSurface.h
> - src/gpu/ganesh/GrSurface.cpp

## 概述

`GrSurface` 是 Ganesh GPU 后端中表示 GPU 表面（surface）的抽象基类。表面是 GPU 上可以进行渲染或作为纹理使用的二维像素数据区域，是 GPU 资源管理体系中的核心抽象。该类封装了表面的基本属性（尺寸、格式、保护状态）和行为（作为纹理或渲染目标的能力），并管理表面资源的生命周期和释放回调。

在 Ganesh 架构中，`GrSurface` 作为 `GrTexture` 和 `GrRenderTarget` 的共同基类，提供了统一的接口来处理各种 GPU 表面。它支持多种后端（OpenGL、Vulkan、Metal 等），并处理跨 API 的通用表面操作，如尺寸查询、内存大小计算和资源释放通知。

## 架构位置

`GrSurface` 位于 Ganesh GPU 资源层级的核心位置：

```
GPU 资源继承层级
├── GrGpuResource (GPU 资源基类)
│   └── GrSurface (表面抽象基类)
│       ├── GrTexture (纹理)
│       ├── GrRenderTarget (渲染目标)
│       └── GrTextureRenderTarget (纹理+渲染目标)
```

使用流程：
```
GrDirectContext
└── GrResourceCache (资源缓存)
    └── GrSurface 子类实例
        ├── 作为纹理用于采样
        └── 作为渲染目标用于绘制
```

## 主要类与结构体

### GrSurface

表面抽象基类，定义了所有 GPU 表面的共同接口和属性。

**继承关系：**
- 父类：`GrGpuResource`（GPU 资源基类）
- 子类：`GrTexture`、`GrRenderTarget`、`GrTextureRenderTarget`

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDimensions` | `SkISize` | 表面的宽度和高度 |
| `fSurfaceFlags` | `GrInternalSurfaceFlags` | 表面标志位（只读、帧缓冲、MSAA 等） |
| `fIsProtected` | `skgpu::Protected` | 是否为受保护内容（DRM 内容保护） |
| `fReleaseHelper` | `sk_sp<RefCntedReleaseProc>` | 释放回调辅助对象 |

### RefCntedReleaseProc

嵌套类，用于管理表面释放时的回调执行。

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCallback` | `sk_sp<skgpu::RefCntedCallback>` | 用户提供的释放回调 |
| `fDirectContext` | `sk_sp<GrDirectContext>` | 持有的上下文引用，确保上下文在回调前不被销毁 |

**生命周期：**
- 在析构时执行回调
- 通过设置上下文标志确保回调在正确的上下文状态下执行

### GrInternalSurfaceFlags (位标志枚举)

| 标志位 | 说明 |
|-------|------|
| `kReadOnly` | 表面内容不可修改 |
| `kFramebufferOnly` | 仅作为帧缓冲使用（不支持纹理采样） |
| `kGLRTFBOIDIs0` | OpenGL 渲染目标的 FBO ID 为 0（窗口表面） |
| `kRequiresManualMSAAResolve` | 需要手动解析 MSAA |
| `kVkRTSupportsInputAttachment` | Vulkan 渲染目标支持输入附件 |

## 公共 API 函数

### 尺寸查询

```cpp
SkISize dimensions() const
int width() const
int height() const
SkRect getBoundsRect() const
```

获取表面的尺寸信息。

### 类型转换

```cpp
virtual GrTexture* asTexture()
virtual const GrTexture* asTexture() const
virtual GrRenderTarget* asRenderTarget()
virtual const GrRenderTarget* asRenderTarget() const
```

将表面转换为特定类型。默认返回 nullptr，子类根据自身类型重写。

### 格式查询

```cpp
virtual GrBackendFormat backendFormat() const = 0
```

纯虚函数，返回后端特定的表面格式。由子类实现。

### 属性查询

```cpp
bool readOnly() const         // 是否只读
bool framebufferOnly() const  // 是否仅用作帧缓冲
bool isProtected() const      // 是否为受保护内容
GrInternalSurfaceFlags flags() const  // 获取所有标志位
```

### 释放回调设置

```cpp
void setRelease(sk_sp<skgpu::RefCntedCallback> releaseHelper)
void setRelease(ReleaseProc proc, ReleaseCtx ctx)
```

设置表面释放时的回调。支持两种形式：
- 智能指针形式的回调对象
- 函数指针和上下文对

**使用场景：**
- 通知调用者表面已被释放
- 清理与表面关联的外部资源

### 静态工具函数

```cpp
static size_t ComputeSize(
    const GrBackendFormat& format,
    SkISize dimensions,
    int colorSamplesPerPixel,
    skgpu::Mipmapped mipmapped,
    bool binSize = false)
```

计算表面占用的内存大小。

**参数：**
- `format`: 后端格式
- `dimensions`: 尺寸
- `colorSamplesPerPixel`: 每像素的颜色采样数（MSAA）
- `mipmapped`: 是否包含 mipmap
- `binSize`: 是否使用近似尺寸（2的幂次）

**返回值：** 字节数，外部格式返回 0

## 内部实现细节

### 内存大小计算

`ComputeSize` 实现了精确的内存占用计算：

```cpp
size_t GrSurface::ComputeSize(...) {
    // 外部格式（如 EGL Image）无法知道实际大小
    if (format.textureType() == GrTextureType::kExternal) {
        return 0;
    }

    // 可选的尺寸对齐到 2 的幂次
    if (binSize) {
        dimensions = skgpu::GetApproxSize(dimensions);
    }

    // 压缩格式使用特殊计算
    if (compressionType != SkTextureCompressionType::kNone) {
        colorSize = SkCompressedFormatDataSize(compressionType, dimensions, mipmapped);
    } else {
        // 未压缩：宽 × 高 × 每像素字节数
        colorSize = dimensions.width() * dimensions.height() *
                    GrBackendFormatBytesPerPixel(format);
    }

    // MSAA 倍增
    finalSize = colorSamplesPerPixel * colorSize;

    // Mipmap 增加约 1/3
    if (mipmapped == skgpu::Mipmapped::kYes) {
        finalSize += colorSize / 3;
    }

    return finalSize;
}
```

**关键点：**
- 压缩纹理使用块压缩计算公式
- MSAA 表面内存按采样数倍增
- Mipmap 链的总大小约为基础大小的 1.33 倍（几何级数和）

### 释放回调机制

释放流程分为三个层次：

1. **设置阶段**（`setRelease`）：
```cpp
void GrSurface::setRelease(sk_sp<skgpu::RefCntedCallback> releaseHelper) {
    SkASSERT(this->getContext());
    fReleaseHelper.reset(new RefCntedReleaseProc(
        std::move(releaseHelper),
        sk_ref_sp(this->getContext())));
    this->onSetRelease(fReleaseHelper);  // 通知后端
}
```

2. **释放阶段**（`onRelease`/`onAbandon`）：
```cpp
void GrSurface::onRelease() {
    this->invokeReleaseProc();  // 释放回调辅助对象
    this->INHERITED::onRelease();
}
```

3. **回调执行**（`RefCntedReleaseProc` 析构）：
```cpp
GrSurface::RefCntedReleaseProc::~RefCntedReleaseProc() {
    fDirectContext->priv().setInsideReleaseProc(true);  // 设置状态标志
    fCallback.reset();  // 触发用户回调
    fDirectContext->priv().setInsideReleaseProc(false);
}
```

**设计要点：**
- 使用 `RefCntedReleaseProc` 包装延迟回调的执行时机
- 持有 `GrDirectContext` 引用确保回调执行时上下文有效
- 设置 `InsideReleaseProc` 标志防止回调中的递归操作

### 受保护内容支持

`isProtected()` 支持 DRM（数字版权管理）内容的渲染：
- 受保护表面的内容无法被 CPU 读取
- 后端需要特殊创建受保护的 GPU 资源
- 受保护和非受保护表面不能混合使用

### 特殊表面标志处理

```cpp
void setFramebufferOnly() {
    SkASSERT(this->asRenderTarget());
    fSurfaceFlags |= GrInternalSurfaceFlags::kFramebufferOnly;
}

void setGLRTFBOIDIs0() {
    SkASSERT(!this->requiresManualMSAAResolve());
    SkASSERT(!this->asTexture());
    SkASSERT(this->asRenderTarget());
    fSurfaceFlags |= GrInternalSurfaceFlags::kGLRTFBOIDIs0;
}
```

这些受保护的 setter 由友元类和后端实现调用，确保标志设置的正确性。

## 依赖关系

### 依赖的模块

| 模块 | 关系 | 说明 |
|------|------|------|
| `GrGpuResource` | 继承 | GPU 资源基类，提供资源管理能力 |
| `GrDirectContext` | 关联 | 图形上下文，管理表面所属的 GPU 上下文 |
| `GrBackendFormat` | 使用 | 表示后端特定的像素格式 |
| `skgpu::RefCntedCallback` | 使用 | 释放回调的封装 |
| `SkISize` / `SkRect` | 使用 | 几何尺寸表示 |
| `GrBackendUtils` | 工具 | 格式转换和大小计算 |
| `SkCompressedDataUtils` | 工具 | 压缩纹理大小计算 |

### 被依赖的模块

| 模块 | 使用方式 | 说明 |
|------|---------|------|
| `GrTexture` | 继承 | 纹理表面实现 |
| `GrRenderTarget` | 继承 | 渲染目标表面实现 |
| `GrTextureRenderTarget` | 继承 | 纹理+渲染目标混合表面 |
| `GrGpu` | 创建和管理 | GPU 类负责创建表面实例 |
| `GrResourceCache` | 缓存 | 资源缓存管理表面生命周期 |
| `GrProxyProvider` | 代理访问 | 通过代理间接访问表面 |

## 设计模式与设计决策

### 抽象基类设计

`GrSurface` 作为抽象基类：
- 定义了表面的通用接口和属性
- 使用虚函数 `asTexture()` 和 `asRenderTarget()` 实现类型安全的向下转型
- 纯虚函数 `backendFormat()` 强制子类提供后端特定实现

### 类型查询模式

使用 `asTexture()` / `asRenderTarget()` 而非 RTTI：
- **性能优势**：虚函数调用比 `dynamic_cast` 更快
- **类型安全**：返回 nullptr 明确表示类型不匹配
- **灵活性**：支持同时实现多个接口（如 `GrTextureRenderTarget`）

### 资源释放回调设计

多层封装的释放回调机制：
1. **用户层**：`RefCntedCallback`（用户提供的回调）
2. **包装层**：`RefCntedReleaseProc`（管理上下文生命周期）
3. **触发层**：`invokeReleaseProc()`（在表面释放时调用）

**优势：**
- 解耦用户回调和内部资源管理
- 保证回调执行时的上下文有效性
- 支持后端特殊处理（如 Vulkan 延迟释放）

### 标志位管理

使用位标志而非布尔变量：
- 节省内存（多个布尔值可用一个整数表示）
- 支持原子操作和批量查询
- 便于序列化和键生成

### 虚函数钩子

提供 `onSetRelease()` 虚函数允许后端定制释放行为：
- OpenGL：可能无特殊处理
- Vulkan：可能需要等待 GPU 完成后再触发回调
- Metal：可能需要注册完成处理器

## 性能考量

### 内存占用优化

`ComputeSize` 的 `binSize` 参数支持粗略估算：
- 将尺寸对齐到 2 的幂次（如 100×100 → 128×128）
- 用于资源预算和缓存管理
- 避免精确计算的开销

### Mipmap 大小估算

使用 `1/3` 近似计算 mipmap 链的额外内存：
```
1 + 1/4 + 1/16 + 1/64 + ... = 4/3 ≈ 1.33
额外开销 = 原始大小 / 3
```

### 虚函数开销

`asTexture()` 和 `asRenderTarget()` 是虚函数：
- 调用开销：1 次虚表查找
- 优化策略：调用结果可缓存在调用者中
- 替代方案：子类直接转换，绕过虚函数

### 释放回调的延迟执行

使用引用计数管理回调执行时机：
- 避免在不安全的上下文中执行回调
- 支持多个持有者共享同一个回调
- 可能导致回调执行延迟，但保证安全性

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrGpuResource.h` | 父类 | GPU 资源基类 |
| `src/gpu/ganesh/GrTexture.h` | 子类 | 纹理实现 |
| `src/gpu/ganesh/GrRenderTarget.h` | 子类 | 渲染目标实现 |
| `include/gpu/ganesh/GrBackendSurface.h` | 关联 | 后端表面描述 |
| `include/gpu/ganesh/GrDirectContext.h` | 依赖 | 图形上下文 |
| `src/gpu/RefCntedCallback.h` | 使用 | 释放回调封装 |
| `src/gpu/ganesh/GrBackendUtils.h` | 工具 | 后端格式工具 |
| `src/core/SkCompressedDataUtils.h` | 工具 | 压缩纹理计算 |
| `include/core/SkTextureCompressionType.h` | 类型 | 纹理压缩类型 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 类型 | Ganesh 私有类型定义 |
