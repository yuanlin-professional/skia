# DawnBackendTexture

> 源文件
> - src/gpu/graphite/dawn/DawnBackendTexture.cpp

## 概述

`DawnBackendTexture` 模块为 Skia Graphite 提供 Dawn 后端纹理的封装和管理功能。该模块定义了 `DawnBackendTextureData` 类,用于存储 Dawn 纹理句柄(`WGPUTexture`)和纹理视图(`WGPUTextureView`),并提供了一系列工厂函数在 `BackendTextures` 命名空间中创建 `BackendTexture` 对象。这些函数支持从 Dawn 原生纹理对象创建 Graphite 纹理,支持单平面和多平面纹理格式,适用于与外部 WebGPU 纹理互操作的场景。

核心功能包括:封装 Dawn 纹理对象为 Graphite `BackendTexture`、支持多平面纹理(YUV 格式)的平面选择、处理纹理视图的用途限制、提供纹理句柄的查询接口。该模块是 Graphite 与外部 WebGPU 内容(如视频解码器输出、WebGL 互操作纹理)集成的关键桥梁。

## 架构位置

`DawnBackendTexture` 位于 Skia Graphite 的 Dawn 后端纹理互操作层:

```
skgpu::graphite
├── BackendTexture (跨后端纹理抽象)
├── BackendTextureData (后端特定数据接口)
└── dawn/
    ├── DawnBackendTextureData (Dawn 纹理数据实现)
    ├── BackendTextures::MakeDawn*() (工厂函数)
    ├── DawnTexture (内部纹理实现)
    └── DawnGraphiteUtils (工具函数)
```

`BackendTextures` 命名空间中的工厂函数创建的 `BackendTexture` 对象可用于:
- 包装外部创建的 WebGPU 纹理
- 从 WebGPU promise images 创建纹理
- 与视频解码器、Canvas 2D 等互操作

## 主要类与结构体

### DawnBackendTextureData 类

```cpp
class DawnBackendTextureData final : public BackendTextureData {
public:
    DawnBackendTextureData(WGPUTexture tex, WGPUTextureView tv);

#if defined(SK_DEBUG)
    skgpu::BackendApi type() const override { return skgpu::BackendApi::kDawn; }
#endif

    WGPUTexture texture() const { return fTexture; }
    WGPUTextureView textureView() const { return fTextureView; }

private:
    void copyTo(AnyBackendTextureData& dstData) const override;
    bool equal(const BackendTextureData* that) const override;

    WGPUTexture fTexture;          // 可选的 Dawn 纹理对象
    WGPUTextureView fTextureView;  // 可选的 Dawn 纹理视图
};
```

**关键特性**:
- 存储 `WGPUTexture` 和/或 `WGPUTextureView`
- 两者至少有一个非空,支持仅视图的场景
- 实现 `copyTo()` 和 `equal()` 用于对象复制和比较

### BackendTextures 命名空间工厂函数

```cpp
namespace BackendTextures {

// 从 WGPUTexture 创建,自动提取尺寸和格式
BackendTexture MakeDawn(WGPUTexture texture);

// 从 WGPUTexture 创建,指定平面尺寸和纹理信息(用于多平面格式)
BackendTexture MakeDawn(SkISize planeDimensions,
                        const DawnTextureInfo& info,
                        WGPUTexture texture);

// 从 WGPUTextureView 创建(仅视图,无法拷贝)
BackendTexture MakeDawn(SkISize dimensions,
                        const DawnTextureInfo& info,
                        WGPUTextureView textureView);

// 查询接口
WGPUTexture GetDawnTexturePtr(const BackendTexture& tex);
WGPUTextureView GetDawnTextureViewPtr(const BackendTexture& tex);

}  // namespace BackendTextures
```

## 公共 API 函数

### MakeDawn(WGPUTexture texture)

```cpp
BackendTexture MakeDawn(WGPUTexture texture)
```
从 `WGPUTexture` 创建 `BackendTexture`,自动查询纹理的宽度、高度和格式。适用于单平面纹理和不需要指定特定平面的场景。内部调用 `wgpuTextureGetWidth/Height()` 和 `DawnTextureInfo(texture)` 构造函数。

**返回值**: 包含纹理尺寸、格式信息和 Dawn 句柄的 `BackendTexture` 对象。

### MakeDawn(SkISize, const DawnTextureInfo&, WGPUTexture)

```cpp
BackendTexture MakeDawn(SkISize planeDimensions,
                        const DawnTextureInfo& info,
                        WGPUTexture texture)
```
从 `WGPUTexture` 创建 `BackendTexture`,显式指定平面尺寸和纹理信息。主要用于多平面纹理格式(如 `R8BG8Biplanar420Unorm`),其中 `info.fAspect` 指定访问哪个平面:
- `wgpu::TextureAspect::All`: 完整纹理
- `wgpu::TextureAspect::Plane0Only`: Y 平面
- `wgpu::TextureAspect::Plane1Only`: UV 平面
- `wgpu::TextureAspect::Plane2Only`: U/V 平面(三平面格式)

**断言检查**:
- Emscripten: 仅允许 `Aspect::All`
- 原生 Dawn: 允许 `All` 或特定平面

### MakeDawn(SkISize, const DawnTextureInfo&, WGPUTextureView)

```cpp
BackendTexture MakeDawn(SkISize dimensions,
                        const DawnTextureInfo& info,
                        WGPUTextureView textureView)
```
从 `WGPUTextureView` 创建 `BackendTexture`,纹理句柄为空。适用于仅能获取纹理视图的场景(如某些互操作 API)。

**重要限制**: 由于无法访问底层 `WGPUTexture`,纹理用途标志会被 `strip_copy_usage()` 函数移除 `CopySrc` 和 `CopyDst`,因为这些操作需要纹理对象。

### GetDawnTexturePtr / GetDawnTextureViewPtr

```cpp
WGPUTexture GetDawnTexturePtr(const BackendTexture& tex)
WGPUTextureView GetDawnTextureViewPtr(const BackendTexture& tex)
```
查询 `BackendTexture` 中存储的 Dawn 句柄。若纹理无效或后端类型不匹配则返回 `nullptr`。这些函数用于将 Graphite 纹理传递给原生 WebGPU API 或第三方库。

## 内部实现细节

### 纹理用途标志裁剪

`strip_copy_usage()` 函数处理仅有纹理视图的限制:

```cpp
static DawnTextureInfo strip_copy_usage(const DawnTextureInfo& info) {
    DawnTextureInfo result = info;
    result.fUsage &= ~(wgpu::TextureUsage::CopyDst | wgpu::TextureUsage::CopySrc);
    return result;
}
```

**原因**: `wgpu::Texture::CopyTextureToTexture` 和相关 API 需要 `WGPUTexture` 对象,无法仅通过 `WGPUTextureView` 执行拷贝操作。移除这些标志防止上层代码误以为可以对该纹理执行拷贝。

### 多平面纹理支持

代码中的断言检查确保多平面纹理的正确使用:

```cpp
#if defined(__EMSCRIPTEN__)
    SkASSERT(info.fAspect == wgpu::TextureAspect::All);
#else
    SkASSERT(info.fAspect == wgpu::TextureAspect::All ||
             info.fAspect == wgpu::TextureAspect::Plane0Only ||
             info.fAspect == wgpu::TextureAspect::Plane1Only ||
             info.fAspect == wgpu::TextureAspect::Plane2Only);
#endif
```

**WebGPU 限制**: 纯 WebGPU 不支持多平面纹理格式,这些格式是 Dawn 原生扩展,用于高效处理 YUV 视频纹理。Emscripten 构建禁用多平面支持,确保与标准 WebGPU 兼容。

### 对象相等性检查

`DawnBackendTextureData::equal()` 方法比较纹理对象:

```cpp
bool equal(const BackendTextureData* that) const override {
    SkASSERT(!that || that->type() == skgpu::BackendApi::kDawn);
    if (auto otherDawn = static_cast<const DawnBackendTextureData*>(that)) {
        return fTexture == otherDawn->fTexture &&
               fTextureView == otherDawn->fTextureView;
    }
    return false;
}
```

通过指针比较判断是否引用相同的 Dawn 对象,而非比较纹理内容。这对于纹理缓存和去重非常重要。

### 辅助函数 get_and_cast_data

```cpp
static const DawnBackendTextureData* get_and_cast_data(const BackendTexture& tex) {
    auto data = BackendTexturePriv::GetData(tex);
    SkASSERT(!data || data->type() == skgpu::BackendApi::kDawn);
    return static_cast<const DawnBackendTextureData*>(data);
}
```

内部辅助函数,安全地从 `BackendTexture` 提取 `DawnBackendTextureData`,包含类型断言。

## 依赖关系

### 对外依赖

| 依赖类/模块 | 用途 | 依赖类型 |
|------------|------|---------|
| `BackendTextureData` | 后端纹理数据基类 | 继承 |
| `BackendTexture` | Graphite 后端纹理抽象 | 强依赖 |
| `BackendTexturePriv` | BackendTexture 私有接口 | 辅助 |
| `DawnTextureInfo` | Dawn 纹理信息结构体 | 强依赖 |
| `TextureInfos::MakeDawn` | 创建 TextureInfo 的工厂 | 强依赖 |
| `wgpu::Texture` | WebGPU 纹理对象 | 外部依赖 |
| `wgpu::TextureView` | WebGPU 纹理视图 | 外部依赖 |

### 被依赖关系

- **DawnTexture**: 内部使用 `DawnBackendTextureData` 存储纹理句柄
- **Promise Images**: 使用工厂函数创建延迟纹理
- **互操作代码**: 使用 `GetDawnTexturePtr` 访问原生句柄

## 设计模式与设计决策

### 工厂方法模式

`BackendTextures` 命名空间提供多个重载的 `MakeDawn()` 函数,根据输入参数(纹理或纹理视图)选择合适的创建路径,隐藏内部实现细节。

### 类型安全的后端数据

`DawnBackendTextureData` 通过虚函数 `type()` 返回后端类型,运行时检查确保类型安全的转换:
```cpp
SkASSERT(!data || data->type() == skgpu::BackendApi::kDawn);
```

### 值语义与句柄语义的结合

- `BackendTexture` 使用值语义,可复制和赋值
- 内部 `WGPUTexture` 使用句柄语义,拷贝仅复制句柄不复制纹理数据
- `copyTo()` 方法实现浅拷贝

### 平台条件编译

大量使用 `#if !defined(__EMSCRIPTEN__)` 处理多平面纹理:
- 原生 Dawn 支持多平面格式(Android YUV、Vulkan YCbCr)
- Emscripten 仅支持标准 WebGPU 单平面格式
- 编译时排除不支持的代码路径

### 防御性编程

每个公开函数都包含验证检查:
```cpp
if (!tex.isValid() || tex.backend() != skgpu::BackendApi::kDawn) {
    return nullptr;
}
```
确保函数在无效输入下返回安全值而非崩溃。

## 性能考量

### 零拷贝封装

`DawnBackendTextureData` 仅存储指针/句柄,不拷贝纹理数据:
```cpp
DawnBackendTextureData(WGPUTexture tex, WGPUTextureView tv)
    : fTexture(tex), fTextureView(tv) {}
```
创建 `BackendTexture` 开销极小,适合高频调用场景。

### 延迟纹理信息查询

对于仅有 `WGPUTexture` 的重载,尺寸和格式通过 Dawn API 查询:
```cpp
static_cast<int32_t>(wgpuTextureGetWidth(texture)),
static_cast<int32_t>(wgpuTextureGetHeight(texture)),
```
虽然有函数调用开销,但避免了重复存储纹理信息。

### 用途标志优化

`strip_copy_usage()` 在编译时内联,零运行时开销:
```cpp
inline DawnTextureInfo strip_copy_usage(const DawnTextureInfo& info) {
    DawnTextureInfo result = info;
    result.fUsage &= ~(...);
    return result;
}
```

### 多平面纹理的内存效率

多平面纹理通过单个 `WGPUTexture` 表示多个平面,避免为每个平面创建独立纹理对象:
- 减少 GPU 内存分配次数
- 简化平面间的同步
- 提高缓存命中率

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/graphite/BackendTexture.h` | 公共接口 | Graphite 后端纹理抽象 |
| `src/gpu/graphite/BackendTexturePriv.h` | 私有接口 | BackendTexture 内部访问 |
| `include/gpu/graphite/dawn/DawnGraphiteTypes.h` | 类型定义 | DawnTextureInfo 结构体 |
| `src/gpu/graphite/dawn/DawnGraphiteUtils.h` | 工具函数 | 格式转换和查询 |
| `src/gpu/graphite/dawn/DawnTexture.h` | 内部纹理 | Graphite 内部纹理实现 |
| `include/core/SkString.h` | 基础类型 | 字符串工具 |
| `webgpu/webgpu_cpp.h` | 外部依赖 | WebGPU C++ API |
