# Surface (Graphite)

> 源文件: `include/gpu/graphite/Surface.h`

## 概述

Surface.h 定义了 Graphite GPU 后端中创建和管理 SkSurface 的公共 API 接口。它提供了创建可渲染目标、包装后端纹理以及将 Surface 转换为 Image 的工厂函数,是 Graphite 绘制架构的核心入口点。

## 架构位置

该文件位于 Skia 的 Graphite GPU 后端公共接口层,属于 `skgpu::graphite` 命名空间。它是应用程序与 Graphite 渲染系统交互的主要接口之一,提供了 Surface 的创建和管理功能。文件通过 `SkSurfaces` 命名空间导出工厂方法,遵循 Skia 的命名空间组织模式。

## 主要类型定义

### ReleaseContext 和 TextureReleaseProc

```cpp
using ReleaseContext = void*;
using TextureReleaseProc = void (*)(ReleaseContext);
```

**用途**: 用于后端纹理的生命周期管理回调机制。当包装的纹理不再被使用时,通过 `TextureReleaseProc` 回调通知客户端释放资源。

## 公共 API 函数

### `AsImage`

```cpp
SK_API sk_sp<SkImage> AsImage(sk_sp<const SkSurface>);
```

- **功能**: 将 Surface 转换为 Image,两者共享相同的底层纹理资源
- **参数**: `sk_sp<const SkSurface>` - 源 Surface 对象
- **返回值**: 返回共享资源的 SkImage,如果后端缓冲区不可纹理化则返回 nullptr
- **重要特性**:
  - 不执行拷贝操作,返回的 Image 与 Surface 共享底层纹理
  - 客户端需要确保在 GPU 消费 Image 时内容正确
  - 返回的 Image 的 mipmap 设置与源 Surface 一致
  - 如果后端 GPU 缓冲区不可纹理化,将返回 nullptr (Graphite 不会自动创建拷贝)

### `AsImageCopy`

```cpp
SK_API sk_sp<SkImage> AsImageCopy(sk_sp<const SkSurface>,
                                  const SkIRect* subset = nullptr,
                                  skgpu::Mipmapped = skgpu::Mipmapped::kNo);
```

- **功能**: 创建 Surface 内容的拷贝作为 Image
- **参数**:
  - `surface` - 源 Surface
  - `subset` - 可选的子区域,nullptr 表示整个 Surface
  - `mipmapped` - 是否生成 mipmap 级别
- **返回值**: 新创建的 SkImage 对象
- **特点**:
  - 执行实际的拷贝操作
  - 支持子区域提取
  - 可以在拷贝时添加 mipmap

### `RenderTarget`

```cpp
SK_API sk_sp<SkSurface> RenderTarget(skgpu::graphite::Recorder*,
                                     const SkImageInfo& imageInfo,
                                     skgpu::Mipmapped = skgpu::Mipmapped::kNo,
                                     const SkSurfaceProps* surfaceProps = nullptr,
                                     std::string_view label = {});
```

- **功能**: 创建由 GPU 支持的可渲染目标 Surface
- **参数**:
  - `recorder` - Graphite Recorder 对象,用于记录命令
  - `imageInfo` - 描述 Surface 的尺寸、颜色类型和透明度类型
  - `mipmapped` - 是否启用 mipmapping
  - `surfaceProps` - Surface 属性配置
  - `label` - 调试标签
- **返回值**: 成功时返回 SkSurface,失败返回 nullptr
- **资源管理**:
  - 客户端持有 Surface 引用期间,底层 GPU 对象不计入预算
  - Surface 释放后,底层资源可能成为可重用的 scratch 资源,此时计入预算

### `WrapBackendTexture` (已弃用版本)

```cpp
SK_API sk_sp<SkSurface> WrapBackendTexture(skgpu::graphite::Recorder*,
                                           const skgpu::graphite::BackendTexture&,
                                           SkColorType colorType,
                                           sk_sp<SkColorSpace> colorSpace,
                                           const SkSurfaceProps* props,
                                           TextureReleaseProc = nullptr,
                                           ReleaseContext = nullptr,
                                           std::string_view label = {});
```

- **功能**: 将 GPU 后端纹理包装为 SkSurface (已弃用版本,需要显式指定 colorType)
- **弃用原因**: 使用下面不需要 colorType 参数的重载版本

### `WrapBackendTexture` (推荐版本)

```cpp
SK_API sk_sp<SkSurface> WrapBackendTexture(skgpu::graphite::Recorder*,
                                           const skgpu::graphite::BackendTexture&,
                                           sk_sp<SkColorSpace> colorSpace,
                                           const SkSurfaceProps* props,
                                           TextureReleaseProc = nullptr,
                                           ReleaseContext = nullptr,
                                           std::string_view label = {});
```

- **功能**: 将 GPU 后端纹理包装为 SkSurface
- **参数**:
  - `recorder` - Graphite Recorder 对象
  - `backendTexture` - 后端纹理对象
  - `colorSpace` - 颜色空间
  - `props` - Surface 属性
  - `releaseProc` - 纹理释放回调
  - `releaseContext` - 传递给释放回调的上下文
  - `label` - 调试标签
- **返回值**: 成功时返回 SkSurface,参数无效时返回 nullptr
- **验证条件**:
  - backendTexture 的格式必须与 colorSpace 和 recorder 兼容
  - 纹理尺寸不能超过 recorder 的能力限制
  - recorder 必须能够支持该后端纹理
- **颜色类型推断**: Surface 的 SkColorType 从后端纹理格式推断,尽可能匹配。对于单通道格式,选择 alpha-only SkColorType

## 内部实现细节

### Copy-on-Write 行为的改变

在 Graphite 中,SkSurface 不再支持传统的写时复制行为。这是与旧 GPU 后端的重要区别:

- **旧行为**: `makeImageSnapshot()` 会隐式地执行延迟复制
- **新行为**: 客户端必须显式选择 `AsImage`(共享)或 `AsImageCopy`(复制)
- **资源稳定性**: Surface 的底层资源永远不会改变,这简化了资源管理

### 平台特定的生命周期管理

对于 Metal 后端:
- Skia 会对底层 MTLTexture 调用 retain
- 客户端可以在调用返回后立即释放 MTLTexture
- 其他平台可能有不同的生命周期要求

### Mipmap 处理

- 单通道纹理格式选择 alpha-only SkColorType
- 片段着色器的 alpha 通道输出会存储到纹理中,无论格式是 A 还是 R
- BGR 和 RGB 通道顺序的歧义在 GPU 渲染和采样中无关紧要

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkRefCnt.h` | 引用计数支持 |
| `include/core/SkSurface.h` | SkSurface 基类定义 |
| `include/gpu/GpuTypes.h` | GPU 通用类型定义 |
| `skgpu::graphite::BackendTexture` | 后端纹理抽象 |
| `skgpu::graphite::Recorder` | 命令记录器 |

### 被依赖的模块

该接口被以下模块使用:
- 应用层渲染代码(直接使用 SkSurfaces 命名空间)
- Graphite 内部实现(Surface_Graphite.cpp 等)
- 跨平台渲染抽象层

## 设计模式与设计决策

### 命名空间工厂模式

使用 `SkSurfaces` 命名空间而非类静态方法:
- 更清晰的 API 组织
- 避免类接口膨胀
- 易于扩展和版本管理

### 显式拷贝语义

强制客户端显式选择拷贝还是共享:
- 提高性能可预测性
- 减少隐式内存分配
- 明确资源所有权

### 回调机制

使用函数指针回调而非虚函数:
- 更轻量级的资源释放通知
- 避免额外的虚函数调用开销
- 支持 C 风格 API 绑定

### 标签支持

所有创建函数都支持可选的 `std::string_view label` 参数:
- 用于调试和性能分析
- 零成本抽象(在 Release 构建中可优化掉)

## 性能考量

### 预算管理

- **持有期间**: Surface 被客户端引用时不计入 GPU 预算
- **释放后**: 可能成为 scratch 资源并计入预算
- **设计目的**: 鼓励 Surface 复用,避免频繁创建销毁

### AsImage vs AsImageCopy

- `AsImage`: 零拷贝,但需要同步管理
- `AsImageCopy`: 有拷贝开销,但更安全
- **选择建议**: 优先使用 `AsImage`,在必要时才使用 `AsImageCopy`

### Mipmap 生成

- 创建时指定 mipmapped 参数
- 避免后期动态生成的开销
- 对于频繁缩放的内容应启用 mipmapping

## 平台相关说明

### Metal

- Skia 自动管理 MTLTexture 的引用计数
- 客户端可以在创建 Surface 后释放原始 MTLTexture
- 支持 retain/release 语义

### 其他后端

文档提示其他平台可能有不同的生命周期要求,但当前仅明确说明了 Metal 的行为。

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkSurface.h` | 基类定义 |
| `include/gpu/graphite/Image.h` | Image 创建接口 |
| `include/gpu/graphite/Recorder.h` | 命令记录器定义 |
| `include/gpu/graphite/BackendTexture.h` | 后端纹理抽象 |
| `src/gpu/graphite/Surface_Graphite.cpp` | 实现文件 |
| `include/gpu/GpuTypes.h` | Mipmapped 等类型定义 |

## 使用示例场景

### 创建渲染目标

```cpp
sk_sp<SkSurface> surface = SkSurfaces::RenderTarget(
    recorder,
    SkImageInfo::MakeN32Premul(800, 600),
    skgpu::Mipmapped::kNo);
```

### 包装外部纹理

```cpp
sk_sp<SkSurface> surface = SkSurfaces::WrapBackendTexture(
    recorder,
    backendTexture,
    colorSpace,
    nullptr,  // props
    [](void* context) { /* cleanup */ },
    nullptr);  // context
```

### 零拷贝 Image 创建

```cpp
sk_sp<SkImage> image = SkSurfaces::AsImage(surface);
// image 与 surface 共享底层纹理
```

### 子区域拷贝

```cpp
SkIRect subset = SkIRect::MakeXYWH(100, 100, 200, 200);
sk_sp<SkImage> image = SkSurfaces::AsImageCopy(
    surface,
    &subset,
    skgpu::Mipmapped::kYes);
```
