# GrCaps

> 源文件
> - src/gpu/ganesh/GrCaps.h
> - src/gpu/ganesh/GrCaps.cpp

## 概述

`GrCaps` 是 Ganesh GPU 后端的能力（Capabilities）查询系统的核心类，用于表示 GPU 上下文（`GrContext`）的各项功能和限制。该类封装了硬件、驱动和 API 的能力信息，包括纹理格式支持、渲染目标尺寸限制、混合模式支持、缓冲区映射能力等。

`GrCaps` 继承自 `SkCapabilities`，是一个抽象基类，由各个后端（OpenGL、Vulkan、Metal、Direct3D）实现具体的子类。它在初始化时查询 GPU 能力，并在整个渲染管线中被频繁查询以决定最佳的渲染路径。

## 架构位置

`GrCaps` 位于 Skia 图形库的架构中：

- **模块**: Ganesh GPU 后端
- **层级**: 能力查询层（Capabilities Layer）
- **继承关系**: `SkCapabilities` -> `GrCaps` -> 各后端具体实现
- **协作对象**: 与 `GrContext`、`GrGpu`、`GrShaderCaps`、`GrResourceProvider` 协作

该类是整个 GPU 渲染管线决策的基础，影响纹理创建、渲染路径选择、格式转换等关键操作。

## 主要类与结构体

### GrCaps（主类）

继承关系：
```
SkCapabilities (基类)
  └── GrCaps (抽象基类)
      ├── GrGLCaps (OpenGL)
      ├── GrVkCaps (Vulkan)
      ├── GrMtlCaps (Metal)
      └── GrD3DCaps (Direct3D)
```

关键成员变量（部分）：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fShaderCaps` | `unique_ptr<GrShaderCaps>` | 着色器能力对象 |
| `fMaxTextureSize` | `int` | 最大纹理尺寸 |
| `fMaxRenderTargetSize` | `int` | 最大渲染目标尺寸 |
| `fMaxVertexAttributes` | `int` | 最大顶点属性数量 |
| `fMaxWindowRectangles` | `int` | 最大窗口矩形数量 |
| `fInternalMultisampleCount` | `int` | 内部多重采样计数 |
| `fMapBufferFlags` | `uint32_t` | 缓冲区映射标志 |
| `fBlendEquationSupport` | `BlendEquationSupport` | 混合方程支持级别 |
| `fNPOTTextureTileSupport` | `bool` | 非二次幂纹理平铺支持 |
| `fMipmapSupport` | `bool` | Mipmap 支持 |
| `fAnisoSupport` | `bool` | 各向异性过滤支持 |
| `fTransferFromBufferToBufferSupport` | `bool` | 缓冲区间传输支持 |
| `fDriverBugWorkarounds` | `GrDriverBugWorkarounds` | 驱动错误解决方案 |

### 枚举类型

#### BlendEquationSupport

```cpp
enum BlendEquationSupport {
    kBasic_BlendEquationSupport,              // 基本混合
    kAdvanced_BlendEquationSupport,           // 高级混合（需要屏障）
    kAdvancedCoherent_BlendEquationSupport,   // 高级混合（无需屏障）
};
```

#### MapFlags

```cpp
enum MapFlags {
    kNone_MapFlags      = 0x0,    // 不支持映射
    kCanMap_MapFlag     = 0x1,    // 可以映射
    kSubset_MapFlag     = 0x2,    // 支持部分映射
    kAsyncRead_MapFlag  = 0x4,    // 异步读取映射
};
```

#### SurfaceReadPixelsSupport

```cpp
enum class SurfaceReadPixelsSupport {
    kSupported,          // 支持直接读取
    kCopyToTexture2D,    // 需要先复制到 Texture2D
    kUnsupported,        // 不支持
};
```

### 辅助结构体

#### SupportedWrite

```cpp
struct SupportedWrite {
    GrColorType fColorType;
    size_t fOffsetAlignmentForTransferBuffer;
};
```

#### SupportedRead

```cpp
struct SupportedRead {
    GrColorType fColorType;
    size_t fOffsetAlignmentForTransferBuffer;
};
```

#### DstCopyRestrictions

```cpp
struct DstCopyRestrictions {
    GrSurfaceProxy::RectsMustMatch fRectsMustMatch;
    bool fMustCopyWholeSrc;
};
```

## 公共 API 函数

### 能力查询函数

#### 纹理相关

```cpp
bool npotTextureTileSupport() const;
bool mipmapSupport() const;
bool anisoSupport() const;
int maxTextureSize() const;
```

#### 渲染目标相关

```cpp
int maxRenderTargetSize() const;
int maxPreferredRenderTargetSize() const;
int maxVertexAttributes() const;
```

#### 格式相关

```cpp
bool isFormatSRGB(const GrBackendFormat&) const = 0;
bool isFormatCompressed(const GrBackendFormat&) const;
bool isFormatTexturable(const GrBackendFormat&, GrTextureType) const = 0;
bool isFormatCopyable(const GrBackendFormat&) const = 0;
int maxRenderTargetSampleCount(const GrBackendFormat&) const = 0;
```

#### 缓冲区相关

```cpp
uint32_t mapBufferFlags() const;
bool preferClientSideDynamicBuffers() const;
bool reuseScratchBuffers() const;
size_t bufferMapThreshold() const;
```

#### 混合和渲染状态

```cpp
BlendEquationSupport blendEquationSupport() const;
bool advancedBlendEquationSupport() const;
bool advancedCoherentBlendEquationSupport() const;
```

#### 特性支持

```cpp
bool drawInstancedSupport() const;
bool nativeDrawIndirectSupport() const;
bool textureBarrierSupport() const;
bool semaphoreSupport() const;
bool backendSemaphoreSupport() const;
```

### 格式和颜色类型兼容性

```cpp
bool areColorTypeAndFormatCompatible(GrColorType, const GrBackendFormat&) const;
GrBackendFormat getDefaultBackendFormat(GrColorType, GrRenderable) const;
skgpu::Swizzle getReadSwizzle(const GrBackendFormat&, GrColorType) const;
```

### 读写支持查询

```cpp
bool surfaceSupportsWritePixels(const GrSurface*) const;
SurfaceReadPixelsSupport surfaceSupportsReadPixels(const GrSurface*) const = 0;
SupportedWrite supportedWritePixelsColorType(GrColorType surfaceColorType,
                                             const GrBackendFormat& surfaceFormat,
                                             GrColorType srcColorType) const = 0;
SupportedRead supportedReadPixelsColorType(GrColorType srcColorType,
                                           const GrBackendFormat& srcFormat,
                                           GrColorType dstColorType) const;
```

### 验证和工具函数

```cpp
bool validateSurfaceParams(const SkISize&, const GrBackendFormat&,
                          GrRenderable, int renderTargetSampleCnt,
                          skgpu::Mipmapped, GrTextureType) const;
bool canCopySurface(const GrSurfaceProxy* dst, const SkIRect& dstRect,
                   const GrSurfaceProxy* src, const SkIRect& srcRect) const;
```

### 调试和诊断

```cpp
void dumpJSON(SkJSONWriter*) const;
const GrDriverBugWorkarounds& workarounds() const;
```

## 内部实现细节

### 初始化流程

```cpp
GrCaps(const GrContextOptions& options);
void finishInitialization(const GrContextOptions& options);
```

1. 构造函数设置所有能力标志的默认值（通常为 `false`）
2. 子类覆盖构造函数，查询特定后端的能力
3. 调用 `finishInitialization()` 应用用户覆盖和驱动解决方案

### 选项覆盖

```cpp
void applyOptionsOverrides(const GrContextOptions& options);
```

允许用户通过 `GrContextOptions` 覆盖某些能力：
- 禁用高级混合方程
- 强制初始化纹理
- 限制最大纹理尺寸
- 禁用 mipmap 支持

### 格式查询模式

```cpp
virtual bool isFormatTexturable(const GrBackendFormat&, GrTextureType) const = 0;
```

所有格式相关的查询都是纯虚函数，由子类实现，因为格式支持高度依赖于后端。

### 回退机制

```cpp
std::tuple<GrColorType, GrBackendFormat> getFallbackColorTypeAndFormat(
    GrColorType, int sampleCnt) const;
```

当请求的颜色类型不支持时，自动查找兼容的回退格式。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrShaderCaps` | 着色器能力查询 |
| `GrContextOptions` | 用户配置选项 |
| `GrBackendFormat` | 后端格式表示 |
| `GrDriverBugWorkarounds` | 驱动错误解决方案 |
| `SkCapabilities` | 基础能力类 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| `GrContext` | 创建和持有 caps 对象 |
| `GrGpu` | 查询能力以执行操作 |
| `GrResourceProvider` | 创建资源前验证参数 |
| `GrSurfaceProxy` | 验证表面参数 |
| `GrOpsTask` | 决定渲染路径 |

## 设计模式与设计决策

### 1. 策略模式

不同的后端实现不同的能力查询策略。

### 2. 模板方法模式

基类定义框架（`finishInitialization`），子类填充具体能力。

### 3. 单例式使用

每个 `GrContext` 持有一个 `GrCaps` 实例，在整个生命周期中不变。

### 4. 位域优化

使用 `bool : 1` 位域减少内存占用。

### 5. 能力降级

通过 `finishInitialization()` 应用用户覆盖，只能降低能力，不能扩展。

### 6. 懒惰查询

许多能力查询依赖于格式，避免预先枚举所有可能的组合。

## 性能考量

### 1. 不可变对象

一旦初始化，能力对象不再改变，允许无锁并发访问。

### 2. 内联访问器

大多数查询函数是简单的访问器，可以被编译器内联。

### 3. 位域紧凑

使用位域减少内存占用，提高缓存局部性。

### 4. 避免虚函数

除了格式查询，大部分能力查询是非虚函数。

### 5. 编译时常量

某些能力（如 `kDefaultBufferSize`）定义为编译时常量。

### 6. 驱动解决方案

通过 `GrDriverBugWorkarounds` 集中管理驱动错误，避免在运行时重复检测。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/gpu/ganesh/GrShaderCaps.h` | 着色器能力类 |
| `include/gpu/ganesh/GrContextOptions.h` | 用户配置选项 |
| `include/gpu/ganesh/GrBackendSurface.h` | 后端格式定义 |
| `include/gpu/ganesh/GrDriverBugWorkarounds.h` | 驱动错误解决方案 |
| `src/gpu/ganesh/GrContext.h` | 持有 caps 对象 |
| `src/gpu/ganesh/GrGpu.h` | 使用 caps 执行操作 |
| `src/gpu/ganesh/gl/GrGLCaps.h` | OpenGL 能力实现 |
| `src/gpu/ganesh/vk/GrVkCaps.h` | Vulkan 能力实现 |
| `src/gpu/ganesh/mtl/GrMtlCaps.h` | Metal 能力实现 |
