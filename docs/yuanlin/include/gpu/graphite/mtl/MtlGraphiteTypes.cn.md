# MtlGraphiteTypes

> 源文件: `include/gpu/graphite/mtl/MtlGraphiteTypes.h`

## 概述

MtlGraphiteTypes.h 定义了 Graphite Metal 后端的纹理信息类 MtlTextureInfo,该类封装了 Metal 纹理的格式、用途、存储模式等属性。此文件需要在 Objective-C 环境下编译,提供了与 Metal 框架直接交互的类型定义。

## 架构位置

该文件位于 Skia Graphite GPU 后端的 Metal 平台特定接口层,属于 `skgpu::graphite` 命名空间。它是 Graphite 与 Metal API 之间的桥接层,实现了 TextureInfo::Data 接口,为 Metal 纹理提供了统一的抽象。

## 编译要求

```cpp
#if __OBJC__  // <Metal/Metal.h> only works when compiled for Objective C
```

**重要**: 该文件只能在 Objective-C 或 Objective-C++ 环境下编译,因为它依赖 Metal 框架的 Objective-C 接口。

## 主要类与结构体

### MtlTextureInfo

```cpp
class SK_API MtlTextureInfo final : public TextureInfo::Data
```

**职责**: 封装 Metal 纹理的完整属性信息,实现 TextureInfo 的 Metal 特定数据层。

**继承关系**: `TextureInfo::Data → MtlTextureInfo`

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fFormat` | `MTLPixelFormat` | Metal 像素格式 |
| `fUsage` | `MTLTextureUsage` | 纹理用途标志 |
| `fStorageMode` | `MTLStorageMode` | 存储模式(共享/私有/托管) |
| `fFramebufferOnly` | `bool` | 是否仅用于帧缓冲 |

## 公共 API 函数

### 构造函数

#### 默认构造函数

```cpp
MtlTextureInfo() = default;
```

- **功能**: 创建默认初始化的 MtlTextureInfo
- **默认值**: fFormat = MTLPixelFormatInvalid, fUsage = MTLTextureUsageUnknown

#### 从 MTLTexture 构造

```cpp
explicit MtlTextureInfo(CFTypeRef mtlTexture);
```

- **功能**: 从现有 MTLTexture 对象提取信息
- **参数**: `mtlTexture` - CFTypeRef 类型的 MTLTexture
- **用途**: 包装外部创建的纹理

#### 完整参数构造

```cpp
MtlTextureInfo(SampleCount sampleCount,
               skgpu::Mipmapped mipmapped,
               MTLPixelFormat format,
               MTLTextureUsage usage,
               MTLStorageMode storageMode,
               bool framebufferOnly)
```

- **功能**: 显式指定所有纹理属性
- **参数**:
  - `sampleCount`: MSAA 采样数
  - `mipmapped`: 是否有 mipmap 级别
  - `format`: Metal 像素格式
  - `usage`: 纹理用途位标志
  - `storageMode`: 存储模式
  - `framebufferOnly`: 是否限制为帧缓冲使用

### MTLPixelFormat 常用值

```cpp
// 常见格式
MTLPixelFormatRGBA8Unorm        // 标准 8-bit RGBA
MTLPixelFormatBGRA8Unorm        // 8-bit BGRA (常用于显示)
MTLPixelFormatRGBA16Float       // 16-bit 浮点 RGBA (HDR)
MTLPixelFormatDepth32Float      // 32-bit 深度
MTLPixelFormatStencil8          // 8-bit 模板
MTLPixelFormatRG8Unorm          // 双通道 8-bit
```

### MTLTextureUsage 标志

```cpp
MTLTextureUsageUnknown          = 0x0000,
MTLTextureUsageShaderRead       = 0x0001,  // 着色器读取
MTLTextureUsageShaderWrite      = 0x0002,  // 着色器写入
MTLTextureUsageRenderTarget     = 0x0004,  // 作为渲染目标
MTLTextureUsagePixelFormatView  = 0x0010,  // 支持格式视图
```

### MTLStorageMode 说明

| 模式 | 说明 | 性能 | 可见性 |
|------|------|------|--------|
| `MTLStorageModeShared` | 共享模式 | CPU/GPU 都快 | 都可见 |
| `MTLStorageModeManaged` | 托管模式 (macOS) | 需同步 | 都可见 |
| `MTLStorageModePrivate` | 私有模式 | GPU 最快 | 仅 GPU |
| `MTLStorageModeMemoryless` | 无内存模式 (iOS) | tile 内存 | 临时 |

## 内部实现细节

### TextureInfo::Data 接口实现

#### isProtected

```cpp
Protected isProtected() const { return Protected::kNo; }
```

- **功能**: 返回纹理是否受保护
- **Metal 限制**: Metal 当前不支持受保护内容,总是返回 kNo

#### viewFormat

```cpp
TextureFormat viewFormat() const;
```

- **功能**: 返回纹理视图格式
- **实现**: 将 MTLPixelFormat 转换为 Graphite 统一的 TextureFormat

#### toBackendString

```cpp
SkString toBackendString() const override;
```

- **功能**: 生成人类可读的纹理信息字符串
- **用途**: 调试和日志输出
- **格式**: "Metal(format=RGBA8Unorm, usage=0x0005, mode=Shared, fbOnly=false)"

#### copyTo

```cpp
void copyTo(TextureInfo::AnyTextureInfoData& dstData) const override {
    dstData.emplace<MtlTextureInfo>(*this);
}
```

- **功能**: 拷贝当前对象到类型擦除的容器
- **实现**: 使用 emplace 构造

#### isCompatible

```cpp
bool isCompatible(const TextureInfo& that, bool requireExact) const override;
```

- **功能**: 检查与另一个 TextureInfo 的兼容性
- **参数**:
  - `that`: 要比较的 TextureInfo
  - `requireExact`: 是否要求精确匹配
- **返回值**: 兼容返回 true
- **用途**: 纹理视图创建、格式转换等场景

### 静态后端标识

```cpp
static constexpr skgpu::BackendApi kBackend = skgpu::BackendApi::kMetal;
```

- **功能**: 编译期常量,标识 Metal 后端
- **用途**: 模板特化、编译时分支

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkTypes.h` | 基础类型定义 |
| `include/gpu/graphite/GraphiteTypes.h` | SampleCount 等 |
| `include/gpu/graphite/TextureInfo.h` | TextureInfo 基类 |
| `include/gpu/graphite/mtl/MtlGraphiteTypes_cpp.h` | C++ 桥接类型 |
| `include/private/base/SkAPI.h` | SK_API 宏 |
| `Metal/Metal.h` | Metal 框架 |
| `CoreFoundation/CoreFoundation.h` | CFTypeRef 等 |

### 被依赖的模块

- `TextureInfo`: 使用 MtlTextureInfo 作为数据层
- `BackendTexture`: Metal 后端纹理实现
- Metal 后端的纹理创建和管理代码

## 设计模式与设计决策

### Pimpl 变体 - Data 接口模式

MtlTextureInfo 实现了 TextureInfo::Data 接口:
- **优势**: 平台特定细节与通用接口分离
- **实现**: TextureInfo 持有 Data 指针,运行时多态
- **性能**: 虚函数调用开销可接受,但提供了编译期优化路径

### 非虚模板 API

```cpp
// Non-virtual template API for TextureInfo::Data accessed directly when backend type is known.
static constexpr skgpu::BackendApi kBackend = skgpu::BackendApi::kMetal;
Protected isProtected() const;
TextureFormat viewFormat() const;
```

- **设计**: 当后端类型已知时,可直接调用非虚函数
- **优化**: 编译器可内联这些调用
- **兼容**: 虚函数版本用于类型未知场景

### Objective-C 条件编译

```cpp
#if __OBJC__
// Metal 特定代码
#endif
```

- **目的**: 允许在 C++ 编译单元中包含该头文件(只看到前向声明)
- **实现**: Objective-C++ 编译单元看到完整定义
- **好处**: 减少 Objective-C 编译传播

## 性能考量

### 存储模式选择

#### MTLStorageModeShared (默认)
- **优势**: CPU/GPU 都能高效访问,无需显式同步
- **劣势**: GPU 性能略低于 Private
- **适用**: 频繁 CPU/GPU 交互的纹理

#### MTLStorageModePrivate (高性能)
- **优势**: GPU 访问最快
- **劣势**: CPU 完全无法访问
- **适用**: 纯 GPU 纹理(渲染目标、中间纹理)

#### MTLStorageModeManaged (macOS)
- **优势**: 统一内存架构下与 Shared 类似
- **劣势**: 需要显式同步
- **适用**: 传统 macOS 系统(非 Apple Silicon)

#### MTLStorageModeMemoryless (iOS tile-based)
- **优势**: 零内存开销,极快
- **劣势**: 仅在渲染过程中存在
- **适用**: 深度/模板缓冲,MSAA resolve 纹理

### 纹理用途标志优化

正确设置 fUsage 可优化驱动行为:
```cpp
// 只读纹理
usage = MTLTextureUsageShaderRead;

// 渲染目标
usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead;

// 计算着色器输出
usage = MTLTextureUsageShaderWrite | MTLTextureUsageShaderRead;
```

### FramebufferOnly 优化

```cpp
fFramebufferOnly = true;  // 允许 tile 内存优化
```
- **适用**: 仅用于渲染的纹理
- **效果**: iOS 上可使用 tile 内存,显著降低带宽
- **限制**: 不能读取纹理内容

## 平台相关说明

### iOS 特有特性

- **Memoryless 模式**: 仅 iOS 支持,桌面 Metal 不可用
- **FramebufferOnly**: iOS 优化更明显

### macOS 特有特性

- **Managed 模式**: 主要用于独立显卡场景
- **Apple Silicon**: 与 iOS 更相似,Shared 模式高效

### 统一内存架构 (Apple Silicon)

- Shared 模式几乎零拷贝
- Private 模式优势减小
- 推荐优先使用 Shared

## 使用示例

### 创建标准 RGBA 纹理信息

```cpp
MtlTextureInfo info(
    SampleCount::k1,
    skgpu::Mipmapped::kYes,
    MTLPixelFormatRGBA8Unorm,
    MTLTextureUsageShaderRead | MTLTextureUsageRenderTarget,
    MTLStorageModePrivate,
    false  // framebufferOnly
);
```

### 从现有纹理提取信息

```cpp
id<MTLTexture> texture = ...;  // 从某处获取
MtlTextureInfo info((__bridge CFTypeRef)texture);
```

### 创建高性能渲染目标

```cpp
MtlTextureInfo renderTargetInfo(
    SampleCount::k4,              // 4x MSAA
    skgpu::Mipmapped::kNo,
    MTLPixelFormatBGRA8Unorm,
    MTLTextureUsageRenderTarget,
    MTLStorageModePrivate,        // GPU 专用
    true                          // framebufferOnly 优化
);
```

### 深度缓冲配置

```cpp
MtlTextureInfo depthInfo(
    SampleCount::k1,
    skgpu::Mipmapped::kNo,
    MTLPixelFormatDepth32Float,
    MTLTextureUsageRenderTarget,
    MTLStorageModeMemoryless,     // iOS tile 内存
    true
);
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/gpu/graphite/TextureInfo.h` | 基类定义 |
| `include/gpu/graphite/mtl/MtlGraphiteTypes_cpp.h` | C++ 桥接版本 |
| `include/gpu/graphite/BackendTexture.h` | 使用 MtlTextureInfo |
| `src/gpu/graphite/mtl/MtlTexture.cpp` | 实现文件 |
| `Metal/Metal.h` | Metal 框架头文件 |

## 最佳实践

1. **存储模式**: 优先使用 Private,需要 CPU 访问时用 Shared
2. **用途标志**: 只设置实际需要的标志
3. **FramebufferOnly**: 渲染目标应设置为 true
4. **Mipmap**: 提前决定是否需要,后期生成有开销
5. **格式选择**: 优先使用硬件原生格式(如 BGRA8 用于显示)
