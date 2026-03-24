# GrGLTexture

> 源文件
> - src/gpu/ganesh/gl/GrGLTexture.h
> - src/gpu/ganesh/gl/GrGLTexture.cpp

## 概述

`GrGLTexture` 是 Skia Ganesh OpenGL 后端中表示纹理资源的核心类。它继承自 `GrTexture`，封装了 OpenGL 纹理对象的创建、管理和使用。该类支持多种纹理类型（2D、矩形、外部纹理），并管理纹理参数状态（采样器设置、mipmap 级别等）。

该类负责纹理的生命周期管理、后端纹理信息导出、内存统计以及与 Skia 纹理系统的集成。它可以单独使用，也可以作为 `GrGLTextureRenderTarget` 的基类与渲染目标功能组合。

## 架构位置

```
GrSurface (基类)
    └── GrTexture (纹理抽象)
        └── GrGLTexture (GL纹理实现)
            └── GrGLTextureRenderTarget (纹理+渲染目标组合)

关系:
GrTextureProxy -> GrGLTexture -> OpenGL Texture Object
```

该类位于 Ganesh 图形栈的 OpenGL 纹理层，是 Skia 纹理抽象在 OpenGL 上的具体实现。

## 主要类与结构体

### GrGLTexture

**继承关系:**
- 继承自: `GrTexture`, `GrSurface`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fParameters` | `sk_sp<GrGLTextureParameters>` | 纹理参数状态 |
| `fID` | `GrGLuint` | OpenGL 纹理 ID |
| `fFormat` | `GrGLFormat` | 纹理格式 |
| `fTextureIDOwnership` | `GrBackendObjectOwnership` | 纹理 ID 所有权 |
| `fBaseLevelHasBeenBoundToFBO` | `bool` | 基础级别是否已绑定到 FBO |

### Desc 结构体

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSize` | `SkISize` | 纹理尺寸 |
| `fTarget` | `GrGLenum` | GL 纹理目标（2D/Rectangle/External） |
| `fID` | `GrGLuint` | GL 纹理 ID |
| `fFormat` | `GrGLFormat` | 纹理格式 |
| `fOwnership` | `GrBackendObjectOwnership` | 所有权（拥有/借用） |
| `fIsProtected` | `skgpu::Protected` | 是否为受保护纹理 |

## 公共 API 函数

### 静态工厂方法
- `static GrTextureType TextureTypeFromTarget(GrGLenum textureTarget)` - 从 GL 目标转换为纹理类型
- `static sk_sp<GrGLTexture> MakeWrapped(...)` - 包装外部纹理对象

### 构造与析构
- `GrGLTexture(GrGLGpu*, skgpu::Budgeted, const Desc&, GrMipmapStatus, std::string_view label)` - 创建新纹理
- `~GrGLTexture()` - 析构函数

### 后端接口
- `GrBackendTexture getBackendTexture() const` - 获取后端纹理
- `GrBackendFormat backendFormat() const` - 获取后端格式

### 访问器
- `GrGLTextureParameters* parameters()` - 获取纹理参数对象
- `GrGLuint textureID() const` - 获取 GL 纹理 ID
- `GrGLenum target() const` - 获取 GL 纹理目标
- `GrGLFormat format() const` - 获取纹理格式

### FBO 绑定状态
- `bool hasBaseLevelBeenBoundToFBO() const` - 检查是否已绑定到 FBO
- `void baseLevelWasBoundToFBO()` - 标记已绑定到 FBO

### 纹理参数
- `void textureParamsModified()` - 标记参数已修改（废弃接口）

### 内存统计
- `void dumpMemoryStatistics(SkTraceMemoryDump*) const` - 导出内存统计

## 内部实现细节

### 纹理类型转换

```cpp
GrTextureType GrGLTexture::TextureTypeFromTarget(GrGLenum target) {
    switch (target) {
        case GR_GL_TEXTURE_2D:
            return GrTextureType::k2D;
        case GR_GL_TEXTURE_RECTANGLE:
            return GrTextureType::kRectangle;
        case GR_GL_TEXTURE_EXTERNAL:
            return GrTextureType::kExternal;
    }
    SK_ABORT("Unexpected texture target");
}

static inline GrGLenum target_from_texture_type(GrTextureType type) {
    switch (type) {
        case GrTextureType::k2D:
            return GR_GL_TEXTURE_2D;
        case GrTextureType::kRectangle:
            return GR_GL_TEXTURE_RECTANGLE;
        case GrTextureType::kExternal:
            return GR_GL_TEXTURE_EXTERNAL;
        default:
            SK_ABORT("Unexpected texture target");
    }
}
```

### 纹理初始化

```cpp
void GrGLTexture::init(const Desc& desc) {
    SkASSERT(0 != desc.fID);
    SkASSERT(GrGLFormat::kUnknown != desc.fFormat);
    fID = desc.fID;
    fFormat = desc.fFormat;
    fTextureIDOwnership = desc.fOwnership;
}
```

### 构造函数（自有纹理）

```cpp
GrGLTexture::GrGLTexture(GrGLGpu* gpu,
                         skgpu::Budgeted budgeted,
                         const Desc& desc,
                         GrMipmapStatus mipmapStatus,
                         std::string_view label)
        : GrSurface(gpu, desc.fSize, desc.fIsProtected, label)
        , GrTexture(gpu,
                    desc.fSize,
                    desc.fIsProtected,
                    TextureTypeFromTarget(desc.fTarget),
                    mipmapStatus,
                    label)
        , fParameters(sk_make_sp<GrGLTextureParameters>()) {
    this->init(desc);
    this->registerWithCache(budgeted);

    // 压缩格式的纹理设为只读
    if (GrGLFormatIsCompressed(desc.fFormat)) {
        this->setReadOnly();
    }
}
```

### 包装外部纹理

```cpp
sk_sp<GrGLTexture> GrGLTexture::MakeWrapped(GrGLGpu* gpu,
                                            GrMipmapStatus mipmapStatus,
                                            const Desc& desc,
                                            sk_sp<GrGLTextureParameters> parameters,
                                            GrWrapCacheable cacheable,
                                            GrIOType ioType,
                                            std::string_view label) {
    return sk_sp<GrGLTexture>(new GrGLTexture(
            gpu, desc, mipmapStatus, std::move(parameters), cacheable, ioType, label));
}
```

### 资源释放

```cpp
void GrGLTexture::onRelease() {
    TRACE_EVENT0("skia.gpu", TRACE_FUNC);
    ATRACE_ANDROID_FRAMEWORK_ALWAYS("Texture release(%u)", this->uniqueID().asUInt());

    if (fID) {
        if (GrBackendObjectOwnership::kBorrowed != fTextureIDOwnership) {
            GL_CALL(DeleteTextures(1, &fID));  // 仅删除拥有的纹理
        }
        fID = 0;
    }
    INHERITED::onRelease();
}

void GrGLTexture::onAbandon() {
    fID = 0;  // 放弃所有权，不调用 DeleteTextures
    INHERITED::onAbandon();
}
```

### 后端纹理导出

```cpp
GrBackendTexture GrGLTexture::getBackendTexture() const {
    GrGLTextureInfo info;
    info.fTarget = target_from_texture_type(this->textureType());
    info.fID = fID;
    info.fFormat = GrGLFormatToEnum(fFormat);
    info.fProtected = skgpu::Protected(this->isProtected());

    return GrBackendTextures::MakeGL(
            this->width(), this->height(), this->mipmapped(), info, fParameters);
}

GrBackendFormat GrGLTexture::backendFormat() const {
    return GrBackendFormats::MakeGL(GrGLFormatToEnum(fFormat),
                                    target_from_texture_type(this->textureType()));
}
```

### 纹理窃取（Steal）

允许应用程序接管纹理所有权：

```cpp
bool GrGLTexture::onStealBackendTexture(GrBackendTexture* backendTexture,
                                        SkImages::BackendTextureReleaseProc* releaseProc) {
    *backendTexture = this->getBackendTexture();

    // GL 纹理不需要特殊清理
    *releaseProc = [](GrBackendTexture){};

    // 仅放弃 GrGLTexture 的对象，子类对象（如 RT）仍需清理
    this->GrGLTexture::onAbandon();
    return true;
}
```

### 标签设置

```cpp
void GrGLTexture::onSetLabel() {
    SkASSERT(fID);
    SkASSERT(fTextureIDOwnership == GrBackendObjectOwnership::kOwned);
    if (!this->getLabel().empty()) {
        const std::string label = "_Skia_" + this->getLabel();
        GrGLGpu* glGpu = static_cast<GrGLGpu*>(this->getGpu());
        if (glGpu->glCaps().debugSupport()) {
            GR_GL_CALL(glGpu->glInterface(), ObjectLabel(GR_GL_TEXTURE, fID, -1, label.c_str()));
        }
    }
}
```

### 内存统计

```cpp
void GrGLTexture::dumpMemoryStatistics(SkTraceMemoryDump* traceMemoryDump) const {
    bool refsWrappedTextureObjects =
        this->fTextureIDOwnership == GrBackendObjectOwnership::kBorrowed;
    if (refsWrappedTextureObjects && !traceMemoryDump->shouldDumpWrappedObjects()) {
        return;
    }

    size_t size = GrSurface::ComputeSize(this->backendFormat(), this->dimensions(), 1,
                                         this->mipmapped());

    SkString resourceName = this->getResourceName();
    resourceName.append("/texture");

    this->dumpMemoryStatisticsPriv(traceMemoryDump, resourceName, "Texture", size);

    SkString texture_id;
    texture_id.appendU32(this->textureID());
    traceMemoryDump->setMemoryBacking(resourceName.c_str(), "gl_texture", texture_id.c_str());
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLGpu` | GPU 接口和纹理管理 |
| `GrGLTextureParameters` | 纹理参数状态管理 |
| `GrGLCaps` | OpenGL 能力查询 |
| `GrBackendUtils` | 后端工具函数 |
| `GrSurface` | 表面基类 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrGLTextureRenderTarget` | 继承该类 |
| `GrTextureProxy` | 通过代理访问 |
| `GrGLProgram` | 绑定纹理采样器 |

## 设计模式与设计决策

### 1. 虚继承处理

使用虚继承解决菱形继承问题（在 `GrGLTextureRenderTarget` 中）：

```cpp
// GrGLTextureRenderTarget 同时继承 GrGLTexture 和 GrGLRenderTarget
// 两者都继承自 GrSurface，需要虚继承避免二义性
```

### 2. 参数对象分离

纹理参数独立于纹理对象：

```cpp
sk_sp<GrGLTextureParameters> fParameters;
```

**优势**:
- 参数可以在多个纹理间共享
- 便于包装外部纹理

### 3. 所有权管理

明确区分拥有和借用的纹理：

```cpp
if (GrBackendObjectOwnership::kBorrowed != fTextureIDOwnership) {
    GL_CALL(DeleteTextures(1, &fID));
}
```

### 4. 延迟标签设置

仅在实际设置标签时调用 GL API：

```cpp
void onSetLabel() {
    if (!this->getLabel().empty()) {
        // 仅在非空时调用 glObjectLabel
    }
}
```

## 性能考量

### 1. 参数状态缓存

通过 `GrGLTextureParameters` 避免重复设置：

```cpp
fParameters->invalidate();  // 标记需要重新设置
```

### 2. FBO 绑定优化

跟踪纹理是否已绑定到 FBO：

```cpp
bool hasBaseLevelBeenBoundToFBO() const {
    return fBaseLevelHasBeenBoundToFBO;
}
void baseLevelWasBoundToFBO() {
    fBaseLevelHasBeenBoundToFBO = true;
}
```

**用途**: 某些驱动在首次绑定时有性能问题

### 3. 压缩纹理优化

自动标记压缩纹理为只读：

```cpp
if (GrGLFormatIsCompressed(desc.fFormat)) {
    this->setReadOnly();
}
```

**优势**: 避免不必要的写操作尝试

### 4. 智能指针开销最小化

使用 `sk_sp` 智能指针，但避免不必要的引用计数操作：

```cpp
fParameters = parameters ? std::move(parameters) : sk_make_sp<GrGLTextureParameters>();
```

## 纹理类型支持

### 1. 2D 纹理

标准纹理类型：

```cpp
case GR_GL_TEXTURE_2D:
    return GrTextureType::k2D;
```

### 2. 矩形纹理

用于非 POT（非2的幂）尺寸：

```cpp
case GR_GL_TEXTURE_RECTANGLE:
    return GrTextureType::kRectangle;
```

### 3. 外部纹理

用于 EGL 图像等：

```cpp
case GR_GL_TEXTURE_EXTERNAL:
    return GrTextureType::kExternal;
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrTexture.h` | 基类 | 纹理抽象 |
| `src/gpu/ganesh/gl/GrGLGpu.h` | 依赖 | GPU 接口 |
| `src/gpu/ganesh/gl/GrGLTypesPriv.h` | 依赖 | 纹理参数类型 |
| `src/gpu/ganesh/gl/GrGLTextureRenderTarget.h` | 派生类 | 纹理渲染目标 |
| `src/gpu/ganesh/gl/GrGLCaps.h` | 依赖 | 能力查询 |
| `include/gpu/ganesh/gl/GrGLBackendSurface.h` | 依赖 | 后端纹理创建 |
| `src/gpu/ganesh/GrSurface.h` | 基类 | 表面抽象 |
