# GrMtlTexture

> 源文件
> - src/gpu/ganesh/mtl/GrMtlTexture.h
> - src/gpu/ganesh/mtl/GrMtlTexture.mm

## 概述

`GrMtlTexture` 是 Skia Ganesh Metal 后端中纹理资源的封装类，继承自 `GrTexture` 基类，负责管理 Metal 纹理对象（`id<MTLTexture>`）的生命周期和属性。该类提供创建新纹理和包装外部纹理的工厂方法，支持 Mipmap 管理、压缩纹理格式、只读纹理标记，以及与 Skia 资源缓存系统的集成。作为 Metal 后端的核心纹理表示，`GrMtlTexture` 确保 Metal 纹理对象在 Skia 的统一资源管理框架下正确使用。

## 架构位置

`GrMtlTexture` 位于 Skia GPU 渲染管线的以下位置：

- **模块层级**：`src/gpu/ganesh/mtl/` - Ganesh Metal 后端
- **继承关系**：`GrMtlTexture` -> `GrTexture` -> `GrSurface` -> `GrGpuResource`
- **组合关系**：持有 `sk_sp<GrMtlAttachment>` 封装 Metal 纹理
- **使用者**：`GrMtlGpu`（纹理创建）、`GrMtlTextureRenderTarget`（双用途表面）

## 主要类与结构体

### GrMtlTexture

```cpp
class GrMtlTexture : public GrTexture
```

**核心数据成员**：
- `sk_sp<GrMtlAttachment> fTexture` - 底层 Metal 纹理附件

**访问器**：
- `GrMtlAttachment* attachment() const` - 获取附件对象
- `id<MTLTexture> mtlTexture() const` - 获取 Metal 纹理对象

**构造类型**：
- 预算纹理构造函数（可缓存）
- 包装纹理构造函数（外部纹理）
- 保护构造函数（基类使用）

## 公共 API 函数

### MakeNewTexture

```cpp
static sk_sp<GrMtlTexture> MakeNewTexture(
    GrMtlGpu* gpu,
    skgpu::Budgeted budgeted,
    SkISize dimensions,
    MTLPixelFormat format,
    uint32_t mipLevels,
    GrMipmapStatus mipmapStatus,
    std::string_view label)
```

**功能**：创建新的 Metal 纹理

**步骤**：
1. 调用 `GrMtlAttachment::MakeTexture()` 创建底层附件
2. 参数：`GrRenderable::kNo`（纯纹理）、`numSamples=1`（无 MSAA）
3. 构造 `GrMtlTexture` 并注册到缓存

**返回**：`sk_sp<GrMtlTexture>` - 失败返回 `nullptr`

### MakeWrappedTexture

```cpp
static sk_sp<GrMtlTexture> MakeWrappedTexture(
    GrMtlGpu* gpu,
    SkISize dimensions,
    id<MTLTexture> texture,
    GrWrapCacheable cacheable,
    GrIOType ioType)
```

**功能**：包装外部 Metal 纹理对象

**验证**：
```cpp
SkASSERT(nil != texture);
if (@available(macOS 10.11, iOS 9.0, tvOS 9.0, *)) {
    SkASSERT(SkToBool(texture.usage & MTLTextureUsageShaderRead));
}
```
- 纹理非空
- 支持着色器读取（需要 Metal 2.0+）

**Mipmap 状态推断**：
```cpp
GrMipmapStatus mipmapStatus = texture.mipmapLevelCount > 1
    ? GrMipmapStatus::kValid
    : GrMipmapStatus::kNotAllocated;
```

**IO 类型处理**：
- `kRead_GrIOType` - 标记为只读（`setReadOnly()`）
- 其他类型 - 可读写

### getBackendTexture

```cpp
GrBackendTexture getBackendTexture() const override
```

**功能**：获取后端纹理描述符

**实现**：
```cpp
skgpu::Mipmapped mipmapped = fTexture->mtlTexture().mipmapLevelCount > 1
    ? skgpu::Mipmapped::kYes
    : skgpu::Mipmapped::kNo;
GrMtlTextureInfo info;
info.fTexture.reset(GrRetainPtrFromId(fTexture->mtlTexture()));
return GrBackendTextures::MakeMtl(this->width(), this->height(), mipmapped, info);
```

**注意**：`GrRetainPtrFromId` 增加引用计数，确保外部持有时纹理存活。

### backendFormat

```cpp
GrBackendFormat backendFormat() const override
```

返回纹理的 Metal 像素格式封装（`GrBackendFormats::MakeMtl()`）。

## 内部实现细节

### 构造函数验证

**所有构造函数的共同断言**：
```cpp
SkDEBUGCODE(id<MTLTexture> mtlTexture = fTexture->mtlTexture();)
SkASSERT((GrMipmapStatus::kNotAllocated == mipmapStatus) == (1 == mtlTexture.mipmapLevelCount));
if (@available(macOS 10.11, iOS 9.0, tvOS 9.0, *)) {
    SkASSERT(SkToBool(mtlTexture.usage & MTLTextureUsageShaderRead));
}
SkASSERT(!mtlTexture.framebufferOnly);
```

**检查项**：
1. **Mipmap 一致性**：`kNotAllocated` 状态等价于仅有 1 个 mip 层级
2. **着色器读取权限**：纹理必须可被着色器采样
3. **非 Framebuffer-Only**：纹理不能仅用于帧缓冲（需要可读）

### 只读纹理标记

**压缩纹理自动只读**：
```cpp
if (skgpu::MtlFormatIsCompressed(fTexture->mtlFormat())) {
    this->setReadOnly();
}
```

**包装纹理根据 IO 类型**：
```cpp
if (ioType == kRead_GrIOType) {
    this->setReadOnly();
}
```

**效果**：只读纹理不能作为渲染目标，避免无效操作。

### 资源缓存注册

**新纹理**：
```cpp
this->registerWithCache(budgeted);
```

**包装纹理**：
```cpp
this->registerWithCacheWrapped(cacheable);
```

区分预算管理和缓存策略。

### 标签设置

**onSetLabel 实现**：
```cpp
void GrMtlTexture::onSetLabel() {
    SkASSERT(fTexture);
    if (!this->getLabel().empty()) {
        NSString* labelStr = @(this->getLabel().c_str());
        fTexture->mtlTexture().label = [@"_Skia_" stringByAppendingString:labelStr];
    }
}
```

在 Metal 调试工具（Xcode GPU Debugger）中显示为 `_Skia_<label>`。

### 资源释放

**onRelease**：
```cpp
void onRelease() override {
    fTexture = nil;
    INHERITED::onRelease();
}
```

**onAbandon**：
```cpp
void onAbandon() override {
    fTexture = nil;
    INHERITED::onAbandon();
}
```

释放 Metal 纹理引用，触发 ARC 自动释放。

**析构函数检查**：
```cpp
~GrMtlTexture() {
    SkASSERT(nil == fTexture);
}
```

确保资源已在释放前清理。

### 纹理窃取不支持

```cpp
bool onStealBackendTexture(GrBackendTexture*, SkImages::BackendTextureReleaseProc*) override {
    return false;
}
```

Metal 后端不支持窃取纹理所有权（可能由于 ARC 管理复杂性）。

### 纹理参数修改

```cpp
void textureParamsModified() override {}
```

空实现，Metal 纹理参数通过 `MTLSamplerState` 独立管理，不需要纹理对象本身的通知。

## 依赖关系

**基类**：
- `GrTexture` - 纹理抽象基类
- `GrSurface` - 表面基类
- `GrGpuResource` - GPU 资源管理

**Metal 后端组件**：
- `GrMtlAttachment` - Metal 附件封装（持有 `id<MTLTexture>`）
- `GrMtlGpu` - Metal GPU 实现

**工具库**：
- `src/gpu/mtl/MtlUtilsPriv.h` - Metal 工具函数（`MtlFormatIsCompressed`）

**公共接口**：
- `include/gpu/ganesh/mtl/GrMtlBackendSurface.h` - 后端纹理构建
- `include/gpu/ganesh/SkImageGanesh.h` - 图像集成

## 设计模式与设计决策

### 工厂方法模式

通过静态 `Make*` 方法创建纹理，而非公开构造函数：
- `MakeNewTexture` - 创建新纹理
- `MakeWrappedTexture` - 包装外部纹理

隐藏实现细节，集中管理创建逻辑。

### 组合模式

`GrMtlTexture` 不直接持有 `id<MTLTexture>`，而是通过 `GrMtlAttachment` 间接持有：
- 统一附件管理（纹理、渲染目标、模板缓冲）
- 共享底层 Metal 对象
- 简化双用途表面（`GrMtlTextureRenderTarget`）实现

### 资源管理策略

**预算纹理**：
- 参与 GPU 内存预算管理
- 可被缓存系统驱逐
- 适用于临时纹理

**包装纹理**：
- 外部拥有，Skia 不负责销毁
- 可选择是否缓存（`GrWrapCacheable`）
- 适用于互操作场景

### 平台版本兼容

使用 `@available` 检查 API 可用性：
```cpp
if (@available(macOS 10.11, iOS 9.0, tvOS 9.0, *)) {
    // 使用 Metal 2.0 特性
}
```

确保代码在旧系统上编译和运行（尽管 Skia 实际要求 Metal 2.0+）。

### ARC 管理

**GR_NORETAIN 使用**：
```cpp
GR_NORETAIN_BEGIN
// 所有实现
GR_NORETAIN_END
```

优化引用计数操作，避免不必要的 retain/release。

## 性能考量

### 引用计数优化

**ARC 开销减少**：
- `GR_NORETAIN` 宏避免参数和返回值的自动 retain
- 智能指针（`sk_sp`）管理生命周期，减少临时引用

### 缓存集成

**预算管理**：
- 新纹理注册到缓存，参与 LRU 驱逐
- 包装纹理可选缓存，避免重复包装

### 只读标记优化

压缩纹理自动标记只读：
- 避免无效的渲染目标使用尝试
- 提前失败，减少错误处理开销

### 标签延迟设置

仅在非空标签时设置 Metal 标签：
- 避免空字符串的 NSString 分配
- 减少调试工具开销

## 相关文件

**基类**：
- `src/gpu/ganesh/GrTexture.h` - 纹理抽象基类
- `src/gpu/ganesh/GrSurface.h` - 表面基类

**Metal 附件**：
- `src/gpu/ganesh/mtl/GrMtlAttachment.h/mm` - Metal 附件封装

**GPU 实现**：
- `src/gpu/ganesh/mtl/GrMtlGpu.h/mm` - Metal GPU

**双用途表面**：
- `src/gpu/ganesh/mtl/GrMtlTextureRenderTarget.h/mm` - 纹理+渲染目标

**工具**：
- `src/gpu/mtl/MtlUtilsPriv.h` - Metal 工具函数

**公共接口**：
- `include/gpu/ganesh/mtl/GrMtlBackendSurface.h` - 后端纹理接口
- `include/gpu/ganesh/mtl/GrMtlTypes.h` - Metal 公共类型
