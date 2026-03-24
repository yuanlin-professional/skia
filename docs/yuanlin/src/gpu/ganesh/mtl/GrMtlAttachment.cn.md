# GrMtlAttachment

> 源文件
> - src/gpu/ganesh/mtl/GrMtlAttachment.h
> - src/gpu/ganesh/mtl/GrMtlAttachment.mm

## 概述

`GrMtlAttachment` 是 Skia 图形库中用于封装 Metal API 纹理对象的类,它继承自 `GrAttachment` 基类,专门处理 Metal 后端的纹理附件(包括颜色附件、模板附件和 MSAA 附件)。该类提供了创建、管理和销毁 Metal 纹理资源的完整接口,支持多种纹理用途和配置选项。

## 架构位置

`GrMtlAttachment` 位于 Skia 的 GPU Ganesh 渲染架构中的 Metal 后端实现层。它是 Metal 渲染管线中纹理资源管理的核心组件,负责将 Skia 的抽象纹理概念映射到 Metal 的具体实现。

```
Skia Graphics Library
└── src/gpu/ganesh/          (Ganesh GPU后端)
    ├── GrAttachment          (抽象附件基类)
    └── mtl/                  (Metal后端实现)
        ├── GrMtlGpu          (Metal GPU管理)
        └── GrMtlAttachment   (Metal纹理附件) ← 当前类
```

## 主要类与结构体

### GrMtlAttachment

Metal 纹理附件的封装类,继承自 `GrAttachment`。

**继承关系:**
- 基类: `GrAttachment`
- 派生类: 无(终端类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTexture` | `id<MTLTexture>` | Metal 纹理对象的 Objective-C 引用 |

## 公共 API 函数

### 静态工厂方法

#### MakeStencil
```cpp
static sk_sp<GrMtlAttachment> MakeStencil(
    GrMtlGpu* gpu,
    SkISize dimensions,
    int sampleCnt,
    MTLPixelFormat format
);
```
创建模板附件纹理,用于深度/模板测试。

#### MakeMSAA
```cpp
static sk_sp<GrMtlAttachment> MakeMSAA(
    GrMtlGpu* gpu,
    SkISize dimensions,
    int sampleCnt,
    MTLPixelFormat format
);
```
创建多重采样抗锯齿(MSAA)附件纹理。

#### MakeTexture
```cpp
static sk_sp<GrMtlAttachment> MakeTexture(
    GrMtlGpu* gpu,
    SkISize dimensions,
    MTLPixelFormat format,
    uint32_t mipLevels,
    GrRenderable renderable,
    int numSamples,
    skgpu::Budgeted budgeted
);
```
创建通用纹理附件,可指定是否可渲染、mipmap 层级等选项。

#### MakeWrapped
```cpp
static sk_sp<GrMtlAttachment> MakeWrapped(
    GrMtlGpu* gpu,
    SkISize dimensions,
    id<MTLTexture> texture,
    UsageFlags attachmentUsages,
    GrWrapCacheable cacheable,
    std::string_view label
);
```
包装现有的 Metal 纹理对象为 GrMtlAttachment。

### 访问器方法

| 方法 | 返回类型 | 说明 |
|-----|---------|------|
| `backendFormat()` | `GrBackendFormat` | 获取后端像素格式 |
| `mtlFormat()` | `MTLPixelFormat` | 获取 Metal 像素格式 |
| `mtlTexture()` | `id<MTLTexture>` | 获取底层 Metal 纹理对象 |
| `sampleCount()` | `unsigned int` | 获取采样数 |
| `framebufferOnly()` | `bool` | 检查是否仅用于帧缓冲 |

## 内部实现细节

### 纹理创建流程

`Make` 私有方法是所有工厂方法的核心实现:

1. **创建纹理描述符:** 使用 `MTLTextureDescriptor` 配置纹理属性
2. **设置纹理类型:** 根据采样数选择 2D 或 2D-Multisample
3. **配置存储模式:** 设置为 `MTLStorageModePrivate` (GPU 专用)
4. **设置使用标志:** 根据用途设置 `MTLTextureUsageRenderTarget` 或 `MTLTextureUsageShaderRead`
5. **分配纹理:** 调用 Metal 设备的 `newTextureWithDescriptor:` 方法
6. **调试标签:** 在调试模式下为纹理添加描述性标签

### 资源生命周期管理

```cpp
void GrMtlAttachment::onRelease() override {
    fTexture = nil;  // 释放 Metal 纹理对象
    GrAttachment::onRelease();
}

void GrMtlAttachment::onAbandon() override {
    fTexture = nil;  // 放弃纹理(不等待清理)
    GrAttachment::onAbandon();
}
```

### 平台版本兼容性

代码中大量使用 `@available` 宏检查系统版本:
- **macOS 10.11+, iOS 9.0+:** 支持纹理使用标志和存储模式
- 旧版本系统使用默认配置(功能受限)

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrAttachment` | 基类,提供附件抽象接口 |
| `GrMtlGpu` | Metal GPU 管理器,提供设备访问 |
| `GrMtlUtil` | Metal 工具函数库 |
| `GrBackendFormat` | 跨后端的格式抽象 |
| `Metal/Metal.h` | Apple Metal API |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrMtlFramebuffer` | 帧缓冲配置中引用附件 |
| `GrMtlRenderTarget` | 渲染目标使用颜色/深度附件 |
| `GrMtlTexture` | 纹理对象可能持有附件 |
| `GrMtlCaps` | 能力查询中检查附件支持 |

## 设计模式与设计决策

### 工厂模式
使用多个静态工厂方法(`MakeStencil`, `MakeMSAA`, `MakeTexture`)提供语义化的创建接口,隐藏底层 `Make` 方法的复杂配置参数。

### RAII 资源管理
使用 `sk_sp` 智能指针管理 GrMtlAttachment 对象,Objective-C 的 ARC(自动引用计数)管理 Metal 纹理对象,确保资源自动释放。

### 平台适配策略
通过编译时宏(`#ifdef SK_BUILD_FOR_MAC`)和运行时版本检查(`@available`)实现跨平台支持,优雅降级到旧系统。

### 调试支持
在 `SK_ENABLE_MTL_DEBUG_INFO` 宏开启时,自动为纹理添加描述性标签,便于 Xcode GPU 调试工具识别。

## 性能考量

### 内存分配优化
- **Private 存储模式:** 所有纹理默认使用 `MTLStorageModePrivate`,确保数据仅存储在 GPU 内存中,避免 CPU-GPU 数据传输
- **对齐要求:** 纹理尺寸自动对齐到 Metal 硬件要求,减少内存浪费

### 纹理复用
通过 `registerWithCache` 方法将纹理注册到资源缓存系统,支持纹理复用,减少重复创建开销。

### 最小化状态切换
`framebufferOnly` 标志允许创建仅用于渲染的纹理,Metal 驱动可据此优化内存布局。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrAttachment.h` | 基类 | 提供平台无关的附件接口 |
| `src/gpu/ganesh/mtl/GrMtlGpu.h` | 协作 | GPU 管理器,创建附件的上下文 |
| `src/gpu/ganesh/mtl/GrMtlUtil.h` | 工具 | 格式转换和 Metal 辅助函数 |
| `src/gpu/ganesh/mtl/GrMtlRenderTarget.h` | 使用者 | 渲染目标持有附件引用 |
| `include/gpu/ganesh/mtl/GrMtlTypes.h` | 类型定义 | Metal 相关类型和常量 |
