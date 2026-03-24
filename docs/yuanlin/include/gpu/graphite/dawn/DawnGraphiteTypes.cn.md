# DawnGraphiteTypes

> 源文件: `include/gpu/graphite/dawn/DawnGraphiteTypes.h`

## 概述

DawnGraphiteTypes.h 定义了 Graphite Dawn/WebGPU 后端的纹理信息类 DawnTextureInfo,以及相关的工厂函数和类型转换工具。该文件是 Graphite 与 WebGPU API 交互的核心类型层,支持 WGPUTexture 和 WGPUTextureView 的包装,以及 YCbCr 采样等高级特性。

## 架构位置

该文件位于 Skia Graphite GPU 后端的 Dawn/WebGPU 平台特定接口层,属于 `skgpu::graphite` 命名空间。它实现了 TextureInfo::Data 接口,为 Dawn 后端提供了统一的纹理抽象,是跨平台图形应用的重要基础设施。

## 主要类与结构体

### DawnTextureInfo

```cpp
class SK_API DawnTextureInfo final : public TextureInfo::Data
```

**职责**: 封装 WebGPU 纹理的完整属性信息,实现 TextureInfo 的 Dawn 特定数据层。

**继承关系**: `TextureInfo::Data → DawnTextureInfo`

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fFormat` | `wgpu::TextureFormat` | 纹理的 WebGPU 格式 |
| `fViewFormat` | `wgpu::TextureFormat` | 纹理视图格式(多平面时为平面格式) |
| `fUsage` | `wgpu::TextureUsage` | 纹理用途标志位 |
| `fAspect` | `wgpu::TextureAspect` | 纹理方面(颜色/深度/模板) |
| `fSlice` | `uint32_t` | 平面切片索引 |
| `fYcbcrVkDescriptor` | `wgpu::YCbCrVkDescriptor` | YCbCr Vulkan 描述符(非 Emscripten) |

## 公共 API 函数

### 构造函数

#### 默认构造函数

```cpp
DawnTextureInfo() = default;
```

- **功能**: 创建默认初始化的 DawnTextureInfo
- **默认值**: fFormat = Undefined, fUsage = None

#### 从 WGPUTexture 构造

```cpp
explicit DawnTextureInfo(WGPUTexture texture);
```

- **功能**: 从现有 WGPUTexture 对象提取信息
- **参数**: `texture` - WebGPU 纹理对象
- **用途**: 包装外部创建的纹理
- **提取内容**: 格式、尺寸、用途等所有属性

#### 基础构造函数

```cpp
DawnTextureInfo(SampleCount sampleCount,
                Mipmapped mipmapped,
                wgpu::TextureFormat format,
                wgpu::TextureUsage usage,
                wgpu::TextureAspect aspect)
```

- **功能**: 指定基础纹理属性
- **参数**:
  - `sampleCount`: MSAA 采样数
  - `mipmapped`: 是否有 mipmap 级别
  - `format`: WebGPU 纹理格式
  - `usage`: 纹理用途
  - `aspect`: 纹理方面
- **默认**: fViewFormat = format, fSlice = 0
- **用途**: 创建标准纹理信息

#### 完整构造函数(带视图格式)

```cpp
DawnTextureInfo(SampleCount sampleCount,
                Mipmapped mipmapped,
                wgpu::TextureFormat format,
                wgpu::TextureFormat viewFormat,
                wgpu::TextureUsage usage,
                wgpu::TextureAspect aspect,
                uint32_t slice)
```

- **功能**: 完全控制所有纹理属性
- **额外参数**:
  - `viewFormat`: 纹理视图格式(可与 format 不同)
  - `slice`: 平面切片索引
- **用途**: 多平面纹理、格式视图等高级场景

#### YCbCr 构造函数(非 Emscripten)

```cpp
#if !defined(__EMSCRIPTEN__)
DawnTextureInfo(SampleCount sampleCount,
                Mipmapped mipmapped,
                wgpu::TextureFormat format,
                wgpu::TextureFormat viewFormat,
                wgpu::TextureUsage usage,
                wgpu::TextureAspect aspect,
                uint32_t slice,
                wgpu::YCbCrVkDescriptor ycbcrVkDescriptor)
#endif
```

- **功能**: 创建支持 YCbCr 采样的纹理信息
- **额外参数**: `ycbcrVkDescriptor` - YCbCr Vulkan 描述符
- **平台限制**: 仅在 Android 且底层为 Vulkan 时支持
- **用途**: 高效的视频纹理采样

### 成员函数

#### getViewFormat

```cpp
wgpu::TextureFormat getViewFormat() const {
    return fViewFormat != wgpu::TextureFormat::Undefined ? fViewFormat : fFormat;
}
```

- **功能**: 获取有效的视图格式
- **逻辑**: 如果 fViewFormat 已设置则返回,否则返回 fFormat
- **用途**: 简化视图格式查询

## TextureInfos 命名空间函数

### MakeDawn

```cpp
SK_API TextureInfo MakeDawn(const DawnTextureInfo& dawnInfo);
```

- **功能**: 从 DawnTextureInfo 创建通用的 TextureInfo
- **参数**: Dawn 特定的纹理信息对象
- **返回值**: 平台无关的 TextureInfo 对象
- **用途**: 将 Dawn 特定信息包装为通用接口

### GetDawnTextureInfo

```cpp
SK_API bool GetDawnTextureInfo(const TextureInfo&, DawnTextureInfo*);
```

- **功能**: 从 TextureInfo 提取 Dawn 特定信息
- **参数**:
  - `TextureInfo&`: 通用纹理信息
  - `DawnTextureInfo*`: 输出参数,接收 Dawn 信息
- **返回值**: 成功返回 true,如果不是 Dawn TextureInfo 返回 false
- **用途**: 反向转换,访问 Dawn 特定属性

## BackendTextures 命名空间函数

### MakeDawn (从 WGPUTexture)

```cpp
SK_API BackendTexture MakeDawn(WGPUTexture);
```

- **功能**: 从 WGPUTexture 创建 BackendTexture(推荐方式)
- **参数**: WGPUTexture 对象
- **信息提取**: 自动从纹理查询所有属性
- **生命周期**:
  - BackendTexture 不调用 retain/release
  - 客户端必须保持 WGPUTexture 有效
  - 包装的 SkImage/SkSurface 会调用 retain/release
- **优势**: 最简单,信息自动提取

### MakeDawn (平面纹理)

```cpp
SK_API BackendTexture MakeDawn(SkISize planeDimensions, const DawnTextureInfo&, WGPUTexture);
```

- **功能**: 创建表示 WGPUTexture 平面的 BackendTexture
- **参数**:
  - `planeDimensions`: 平面的尺寸
  - `dawnInfo`: 包含平面 aspect 和信息的 DawnTextureInfo
  - `texture`: 底层 WGPUTexture
- **用途**: 访问多平面纹理的单个平面
- **适用**: YUV 纹理等多平面格式
- **生命周期**: 与上面相同

### MakeDawn (从 WGPUTextureView)

```cpp
SK_API BackendTexture MakeDawn(SkISize dimensions,
                               const DawnTextureInfo& info,
                               WGPUTextureView textureView);
```

- **功能**: 从 WGPUTextureView 创建 BackendTexture
- **参数**:
  - `dimensions`: 纹理尺寸
  - `info`: 纹理信息
  - `textureView`: WebGPU 纹理视图
- **效率警告**: 比使用 WGPUTexture 效率低
  - 涉及缓冲区传输时需要中间拷贝
  - 影响 Context 的 readPixels 和 Surface::writePixels
- **推荐**: 仅在 WGPUTexture 不可用时使用(如 wgpu::SwapChain)
- **生命周期**: BackendTexture 不 retain/release,SkImage/SkSurface 会

## 内部实现细节

### TextureInfo::Data 接口实现

#### isProtected

```cpp
Protected isProtected() const { return Protected::kNo; }
```

- **功能**: 返回纹理是否受保护
- **WebGPU 限制**: 当前不支持受保护内容,总是返回 kNo

#### viewFormat

```cpp
TextureFormat viewFormat() const;
```

- **功能**: 返回纹理视图格式
- **实现**: 将 wgpu::TextureFormat 转换为 Graphite 统一的 TextureFormat

#### toBackendString

```cpp
SkString toBackendString() const override;
```

- **功能**: 生成人类可读的纹理信息字符串
- **用途**: 调试和日志输出
- **格式**: "Dawn(format=RGBA8Unorm, view=RGBA8Unorm, usage=0x05, aspect=All, slice=0)"

#### copyTo

```cpp
void copyTo(TextureInfo::AnyTextureInfoData& dstData) const override {
    dstData.emplace<DawnTextureInfo>(*this);
}
```

- **功能**: 拷贝当前对象到类型擦除的容器
- **实现**: 使用 emplace 原地构造

#### isCompatible

```cpp
bool isCompatible(const TextureInfo& that, bool requireExact) const override;
```

- **功能**: 检查与另一个 TextureInfo 的兼容性
- **参数**:
  - `that`: 要比较的 TextureInfo
  - `requireExact`: 是否要求精确匹配
- **返回值**: 兼容返回 true
- **用途**: 纹理视图创建、格式转换验证

### 静态后端标识

```cpp
static constexpr skgpu::BackendApi kBackend = skgpu::BackendApi::kDawn;
```

- **功能**: 编译期常量,标识 Dawn 后端
- **用途**: 模板特化、编译时分支

### WebGPU 纹理格式

常用的 `wgpu::TextureFormat` 值:

```cpp
// 颜色格式
wgpu::TextureFormat::RGBA8Unorm        // 标准 8-bit RGBA
wgpu::TextureFormat::BGRA8Unorm        // 8-bit BGRA (常用于显示)
wgpu::TextureFormat::RGBA16Float       // 16-bit 浮点 RGBA (HDR)
wgpu::TextureFormat::RGB10A2Unorm      // 10-bit RGB + 2-bit A

// 深度/模板
wgpu::TextureFormat::Depth32Float      // 32-bit 深度
wgpu::TextureFormat::Depth24PlusStencil8  // 深度+模板
wgpu::TextureFormat::Stencil8          // 8-bit 模板

// 压缩格式
wgpu::TextureFormat::BC1RGBAUnorm      // DXT1
wgpu::TextureFormat::BC7RGBAUnorm      // DXT5
wgpu::TextureFormat::ETC2RGB8Unorm     // ETC2
```

### WebGPU 纹理用途

```cpp
wgpu::TextureUsage::None               = 0x00000000,
wgpu::TextureUsage::CopySrc            = 0x00000001,  // 可作为拷贝源
wgpu::TextureUsage::CopyDst            = 0x00000002,  // 可作为拷贝目标
wgpu::TextureUsage::TextureBinding     = 0x00000004,  // 可绑定为纹理
wgpu::TextureUsage::StorageBinding     = 0x00000008,  // 可绑定为存储纹理
wgpu::TextureUsage::RenderAttachment   = 0x00000010,  // 可作为渲染附件
```

### WebGPU 纹理方面

```cpp
wgpu::TextureAspect::All               // 所有方面
wgpu::TextureAspect::StencilOnly       // 仅模板
wgpu::TextureAspect::DepthOnly         // 仅深度
wgpu::TextureAspect::Plane0Only        // 仅平面 0 (多平面格式)
wgpu::TextureAspect::Plane1Only        // 仅平面 1
// ...
```

## YCbCr 支持 (Android Vulkan)

### wgpu::YCbCrVkDescriptor

```cpp
#if !defined(__EMSCRIPTEN__)
struct YCbCrVkDescriptor {
    // YCbCr 转换参数
    // 仅在 Dawn 通过 Vulkan 运行且在 Android 时可用
};
#endif
```

**用途**: 高效的 YUV→RGB 转换
- **平台**: Android
- **后端**: Vulkan (Dawn 的底层驱动)
- **优势**: 硬件加速的颜色空间转换
- **未来**: 可能扩展到其他平台

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkSize.h` | SkISize 定义 |
| `include/gpu/graphite/GraphiteTypes.h` | SampleCount, Mipmapped |
| `include/gpu/graphite/TextureInfo.h` | TextureInfo 基类 |
| `include/private/base/SkAPI.h` | SK_API 宏 |
| `webgpu/webgpu_cpp.h` | WebGPU C++ API |

### 被依赖的模块

- `TextureInfo`: 使用 DawnTextureInfo 作为数据层
- `BackendTexture`: Dawn 后端纹理实现
- Dawn 后端的纹理创建和管理代码

## 设计模式与设计决策

### Pimpl 变体 - Data 接口模式

与 Metal 后端相同的设计:
- **分离**: 平台特定实现与通用接口分离
- **多态**: 通过虚函数提供运行时多态
- **优化**: 编译期已知后端时可直接调用非虚函数

### 视图格式的灵活性

```cpp
wgpu::TextureFormat getViewFormat() const {
    return fViewFormat != Undefined ? fViewFormat : fFormat;
}
```

- **目的**: 支持格式视图(如 RGBA8Unorm 纹理以 RGBA8Srgb 查看)
- **多平面**: 对于 YUV 纹理,fFormat 是组合格式,fViewFormat 是平面格式

### WGPUTexture vs WGPUTextureView

设计了两个 MakeDawn 重载:
- **WGPUTexture**: 推荐,效率高
- **WGPUTextureView**: 应急,效率低

**原因**: SwapChain 只提供 TextureView,但缓冲区传输需要 Texture。

### 平台条件编译

YCbCr 支持仅在非 Emscripten 环境:
```cpp
#if !defined(__EMSCRIPTEN__)
    wgpu::YCbCrVkDescriptor fYcbcrVkDescriptor = {};
#endif
```

- **原因**: WebGPU 标准不包含 YCbCr Vulkan 扩展
- **实现**: Dawn Native 特有特性

## 性能考量

### WGPUTexture vs WGPUTextureView

| 操作 | WGPUTexture | WGPUTextureView |
|------|-------------|-----------------|
| 渲染 | 直接 | 直接 |
| 采样 | 直接 | 直接 |
| readPixels | 直接 | 需要中间拷贝 |
| writePixels | 直接 | 需要中间拷贝 |

**推荐**: 尽可能使用 WGPUTexture。

### 纹理用途优化

正确设置 fUsage 可优化驱动行为:
```cpp
// 只读纹理
usage = wgpu::TextureUsage::TextureBinding | wgpu::TextureUsage::CopyDst;

// 渲染目标
usage = wgpu::TextureUsage::RenderAttachment | wgpu::TextureUsage::TextureBinding;

// 计算着色器输出
usage = wgpu::TextureUsage::StorageBinding | wgpu::TextureUsage::TextureBinding;
```

### YCbCr 采样性能

使用 YCbCr 描述符时:
- **优势**: 硬件加速转换,比着色器快 2-5倍
- **限制**: 仅 Android Vulkan
- **适用**: 视频播放、相机预览

## 使用示例

### 创建标准 RGBA 纹理信息

```cpp
DawnTextureInfo info(
    SampleCount::k1,
    skgpu::Mipmapped::kYes,
    wgpu::TextureFormat::RGBA8Unorm,
    wgpu::TextureUsage::TextureBinding | wgpu::TextureUsage::RenderAttachment,
    wgpu::TextureAspect::All
);

TextureInfo texInfo = TextureInfos::MakeDawn(info);
```

### 从现有纹理提取信息

```cpp
WGPUTexture texture = ...; // 从某处获取
DawnTextureInfo info(texture);

SkDebugf("Format: %d\n", static_cast<int>(info.fFormat));
```

### 包装 WGPUTexture

```cpp
WGPUTexture texture = ...;
BackendTexture bt = BackendTextures::MakeDawn(texture);

// 使用 bt 创建 SkImage 或 SkSurface
sk_sp<SkImage> image = SkImages::WrapTexture(recorder, bt, ...);
```

### 访问多平面纹理

```cpp
// NV12 纹理有两个平面
WGPUTexture nv12Texture = ...;

// Y 平面
DawnTextureInfo yInfo(
    SampleCount::k1, Mipmapped::kNo,
    wgpu::TextureFormat::R8Unorm,  // 格式
    wgpu::TextureFormat::R8Unorm,  // 视图格式
    wgpu::TextureUsage::TextureBinding,
    wgpu::TextureAspect::Plane0Only,
    0  // slice
);
BackendTexture yPlane = BackendTextures::MakeDawn(
    {width, height}, yInfo, nv12Texture);

// UV 平面
DawnTextureInfo uvInfo(
    SampleCount::k1, Mipmapped::kNo,
    wgpu::TextureFormat::RG8Unorm,
    wgpu::TextureFormat::RG8Unorm,
    wgpu::TextureUsage::TextureBinding,
    wgpu::TextureAspect::Plane1Only,
    1  // slice
);
BackendTexture uvPlane = BackendTextures::MakeDawn(
    {width/2, height/2}, uvInfo, nv12Texture);
```

### 处理 SwapChain

```cpp
wgpu::SwapChain swapChain = ...;
wgpu::TextureView view = swapChain.GetCurrentTextureView();

DawnTextureInfo info(
    SampleCount::k1, Mipmapped::kNo,
    wgpu::TextureFormat::BGRA8Unorm,
    wgpu::TextureUsage::RenderAttachment,
    wgpu::TextureAspect::All
);

BackendTexture bt = BackendTextures::MakeDawn(
    {width, height}, info, view);

// 注意: 此方式 readPixels/writePixels 效率较低
```

## 平台相关说明

### Desktop (Dawn Native)

- 支持所有 WebGPU 特性
- 底层可能是 D3D12、Vulkan、Metal
- YCbCr 支持取决于底层 API

### Web (Browser WebGPU)

- 功能取决于浏览器实现
- 不支持 YCbCr Vulkan 扩展
- 某些高级特性可能不可用

### Android (Vulkan 后端)

- 完整的 YCbCr 支持
- 优化的视频纹理处理
- 硬件加速颜色转换

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/gpu/graphite/TextureInfo.h` | 基类定义 |
| `include/gpu/graphite/BackendTexture.h` | 使用 DawnTextureInfo |
| `include/gpu/graphite/dawn/DawnBackendContext.h` | Context 创建 |
| `webgpu/webgpu_cpp.h` | WebGPU C++ API |
| `src/gpu/graphite/dawn/DawnTexture.cpp` | 实现文件 |

## 最佳实践

1. **纹理创建**: 优先使用 WGPUTexture 而非 WGPUTextureView
2. **用途标志**: 只设置实际需要的用途
3. **格式选择**: 使用硬件原生格式(如 BGRA8 用于显示)
4. **多平面**: 正确设置 aspect 和 slice
5. **YCbCr**: 在 Android 上利用 YCbCr 优化视频性能
6. **调试**: 使用 toBackendString() 输出纹理信息
