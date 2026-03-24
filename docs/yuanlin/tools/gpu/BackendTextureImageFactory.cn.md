# BackendTextureImageFactory

> 源文件
> - tools/gpu/BackendTextureImageFactory.h
> - tools/gpu/BackendTextureImageFactory.cpp

## 概述

`BackendTextureImageFactory` 是 Skia GPU 工具集中用于创建由后端纹理支持的 `SkImage` 对象的工厂模块。与普通的 `makeTextureImage()` 方法不同，该模块不会在色彩格式不支持时降级到 CPU 实现，而是直接失败，这对于测试特定 GPU 代码路径非常有用。该模块提供了从像素数据或纯色创建 GPU 图像的能力，并确保底层纹理资源被正确管理。

核心功能包括：从 `SkPixmap` 创建后端纹理图像、创建纯色填充的后端纹理图像、支持可渲染和不可渲染纹理的选择、自动管理纹理生命周期（与 `ManagedBackendTexture` 集成）、支持 Ganesh 和 Graphite 两种 GPU 后端。该模块主要用于测试场景，确保测试代码使用真实的 GPU 纹理而非 CPU 降级实现。

## 架构位置

`BackendTextureImageFactory` 位于 `tools/gpu/` 目录下，属于 GPU 测试工具层。在 Skia 架构中：

1. **图像工厂层**：提供测试专用的图像创建接口，区别于生产代码的图像工厂
2. **测试基础设施**：为单元测试和 GM 测试提供标准化的 GPU 图像创建方法
3. **资源管理集成**：与 `ManagedBackendTexture` 紧密协作，确保纹理生命周期正确

依赖关系：
- **上游依赖**：`SkImage`（图像抽象）、`SkPixmap`（像素数据）、`ManagedBackendTexture`（纹理管理）
- **后端依赖**：Ganesh（`GrDirectContext`）或 Graphite（`Recorder`）
- **下游使用**：GPU 单元测试、GM 测试、性能基准测试

该模块故意**不**提供降级能力，如果色彩类型不受支持则返回 `nullptr`，这是与生产代码的关键区别。

## 主要类与结构体

### sk_gpu_test 命名空间

所有函数位于 `sk_gpu_test` 命名空间中，表明这是测试工具代码。

### 类型别名

```cpp
using Mipmapped = skgpu::Mipmapped;
using Protected = skgpu::Protected;
using Renderable = skgpu::Renderable;
```

简化类型名称，提高代码可读性。

## 公共 API 函数

### Ganesh API

#### MakeBackendTextureImage（从 Pixmap）

```cpp
sk_sp<SkImage> MakeBackendTextureImage(
    GrDirectContext* dContext,
    const SkPixmap& pixmap,
    Renderable renderable,
    GrSurfaceOrigin origin,
    Protected isProtected = Protected::kNo);
```

从像素数据创建后端纹理图像。

**参数：**
- `dContext`：Direct GPU 上下文
- `pixmap`：源像素数据
- `renderable`：纹理是否可作为渲染目标
- `origin`：纹理原点（`kTopLeft` 或 `kBottomLeft`）
- `isProtected`：是否为受保护内存（DRM 内容）

**返回值：** 成功返回 GPU 支持的 `SkImage`，失败返回 `nullptr`

**失败情况：**
- 像素数据的色彩类型不受 GPU 支持
- GPU 资源分配失败
- 纹理上传失败

**关键特性：** 不会降级到 CPU 图像，强制使用 GPU 纹理

#### MakeBackendTextureImage（纯色）

```cpp
sk_sp<SkImage> MakeBackendTextureImage(
    GrDirectContext* dContext,
    const SkImageInfo& info,
    SkColor4f color,
    Mipmapped mipmapped = Mipmapped::kNo,
    Renderable renderable = Renderable::kNo,
    GrSurfaceOrigin origin = GrSurfaceOrigin::kTopLeft_GrSurfaceOrigin,
    Protected isProtected = Protected::kNo);
```

创建填充指定颜色的后端纹理图像。

**参数：**
- `dContext`：Direct GPU 上下文
- `info`：图像信息（尺寸、色彩类型、alpha 类型、色彩空间）
- `color`：填充颜色（浮点 RGBA，范围 [0, 1]）
- `mipmapped`：是否创建 mipmap 链
- `renderable`：纹理是否可作为渲染目标
- `origin`：纹理原点
- `isProtected`：是否为受保护内存

**返回值：** 纯色 GPU 图像，失败返回 `nullptr`

**颜色处理：**
- 如果 `alphaType` 为 `kOpaque`，颜色强制设为不透明（alpha = 1.0）
- 如果 `alphaType` 为 `kPremul`，颜色预乘 alpha
- 颜色自动适配目标格式

**用途：** 创建用于测试的简单纹理，避免准备复杂的像素数据

### Graphite API

#### MakeBackendTextureImage（从 Pixmap）

```cpp
sk_sp<SkImage> MakeBackendTextureImage(
    skgpu::graphite::Recorder* recorder,
    const SkPixmap& pixmap,
    Mipmapped mipmapped,
    Renderable renderable,
    Origin origin,
    Protected isProtected = Protected::kNo);
```

Graphite 版本的从像素数据创建图像。

**主要差异：**
- 使用 `Recorder` 而非 `GrDirectContext`
- 显式指定是否需要 mipmap（Ganesh 版本不支持 mipmap 参数）
- 使用 `skgpu::Origin` 而非 `GrSurfaceOrigin`

#### MakeBackendTextureImage（纯色）

```cpp
sk_sp<SkImage> MakeBackendTextureImage(
    skgpu::graphite::Recorder* recorder,
    const SkImageInfo& info,
    SkColor4f color,
    Mipmapped mipmapped,
    Renderable renderable,
    Origin origin,
    Protected isProtected = Protected::kNo);
```

Graphite 版本的纯色图像创建。

**实现差异：** 内部使用 `SkBitmap` 分配像素并填充颜色，然后调用 Pixmap 版本，而 Ganesh 直接使用 API 填充颜色。

## 内部实现细节

### Ganesh Pixmap 图像创建流程

```cpp
auto mbet = ManagedBackendTexture::MakeWithData(dContext, pixmap, origin, renderable, isProtected);
return SkImages::BorrowTextureFrom(dContext, mbet->texture(), origin, colorType, alphaType, colorSpace,
                                   ManagedBackendTexture::ReleaseProc, mbet->releaseContext());
```

**关键步骤：**
1. 使用 `ManagedBackendTexture::MakeWithData` 创建纹理并上传像素数据
2. 使用 `SkImages::BorrowTextureFrom` 封装纹理为 `SkImage`
3. 注册 `ManagedBackendTexture::ReleaseProc` 作为释放回调

**"Borrow" 的含义：** `BorrowTextureFrom` 表示 Image 不拥有纹理，而是"借用"它。释放回调确保纹理在 Image 销毁时被释放。

### Ganesh 纯色图像创建流程

```cpp
// 调整颜色以匹配 alpha 类型
if (info.alphaType() == kOpaque_SkAlphaType) {
    color = color.makeOpaque();
} else if (info.alphaType() == kPremul_SkAlphaType) {
    auto pmColor = color.premul();
    color = {pmColor.fR, pmColor.fG, pmColor.fB, pmColor.fA};
}

// 创建纹理并填充颜色
auto mbet = ManagedBackendTexture::MakeWithData(
    dContext, width, height, colorType, color, mipmapped, renderable, isProtected);

// 封装为 Image
return SkImages::BorrowTextureFrom(...);
```

**颜色预处理：**
- **不透明类型**：强制 alpha = 1.0，避免意外的半透明
- **预乘类型**：预先进行预乘，纹理内容为预乘 RGBA
- **未预乘类型**：保持原样（但 Skia 通常不使用未预乘格式）

Ganesh 的 `createBackendTexture` 有专门的重载接受 `SkColor4f` 参数，直接在 GPU 上填充颜色，效率高。

### Graphite Pixmap 图像创建流程

```cpp
auto mbet = ManagedGraphiteTexture::MakeFromPixmap(recorder, pixmap, mipmapped, renderable, isProtected);
return SkImages::WrapTexture(recorder, mbet->texture(), colorType, alphaType, colorSpace, origin,
                             ManagedGraphiteTexture::ImageReleaseProc, mbet->releaseContext());
```

**与 Ganesh 的差异：**
- 使用 `SkImages::WrapTexture` 而非 `BorrowTextureFrom`（API 命名差异，功能相同）
- 使用 `ImageReleaseProc` 而非 `ReleaseProc`（Graphite 有专门的 Image 释放回调）
- 支持显式的 `mipmapped` 参数

### Graphite 纯色图像创建流程

```cpp
// 调整颜色
if (ii.alphaType() == kOpaque_SkAlphaType) {
    color = color.makeOpaque();
}

// 创建 CPU 位图并填充
SkBitmap bitmap;
bitmap.allocPixels(ii);
bitmap.eraseColor(color);

// 转换为 GPU 图像
return MakeBackendTextureImage(recorder, bitmap.pixmap(), mipmapped, renderable, origin, isProtected);
```

**为何不直接填充纹理？** Graphite 的 `createBackendTexture` API 可能没有直接接受颜色的重载，因此先在 CPU 上创建位图，再上传到 GPU。

**性能影响：** 对于大型纹理，CPU 填充可能有额外开销，但对于测试场景（通常是小图像）影响不大。

### 资源生命周期管理

`ManagedBackendTexture` 的引用计数确保资源不会泄漏：

1. `MakeWithData/MakeFromPixmap` 创建 MBET，引用计数为 1
2. `releaseContext()` 增加引用（传递给 Image），引用计数为 2
3. 用户代码释放工厂函数返回的 `sk_sp<SkImage>`，MBET 引用计数仍为 1
4. Image 销毁时调用释放回调，MBET 引用计数减至 0
5. MBET 析构，删除后端纹理

这确保即使用户代码提前释放引用，纹理也会在 Image 销毁时正确释放。

### 为何不降级到 CPU？

生产代码的 `makeTextureImage()` 会在 GPU 不支持时降级到 CPU 位图。该模块故意不提供降级：

**原因：**
- **测试意图明确**：如果测试需要 GPU 图像，降级会掩盖问题
- **代码路径验证**：确保测试的是真实的 GPU 路径，而非 CPU 降级路径
- **失败即反馈**：返回 `nullptr` 立即暴露不兼容问题，促使修复或调整测试

## 依赖关系

### 核心依赖

- **SkImage**：图像抽象接口
- **SkPixmap**：像素数据容器
- **SkColor / SkColor4f**：颜色表示
- **SkImageInfo**：图像元数据
- **SkColorSpace**：色彩空间管理

### 工具依赖

- **ManagedBackendTexture / ManagedGraphiteTexture**：自动管理后端纹理生命周期

### Ganesh 依赖

- **GrDirectContext**：Ganesh GPU 上下文
- **GrBackendSurface**：后端纹理封装
- **SkImageGanesh**：Ganesh 特定的 Image 工厂函数

### Graphite 依赖

- **skgpu::graphite::Recorder**：Graphite 命令记录器
- **skgpu::graphite::Image**：Graphite Image 工厂函数

### 被依赖

- GPU 单元测试（tests/）
- GM 测试（gm/）
- 性能基准测试（bench/）
- 示例代码和教程

## 设计模式与设计决策

### 工厂模式

所有函数都是工厂方法：
- 封装复杂的创建逻辑（纹理创建 + Image 封装）
- 统一的参数接口
- 失败时返回 `nullptr`

### 函数重载

为不同用途提供重载版本：
- **Pixmap 版本**：从现有像素数据创建，灵活性高
- **纯色版本**：快速创建测试图像，便利性高

### 平行 API 设计

Ganesh 和 Graphite 版本保持接口一致：
- 相同的函数名
- 相似的参数顺序和语义
- 便于在两个后端间切换测试

### 严格的失败语义

不提供降级或备选方案：
- 体现"测试优先"的设计哲学
- 立即暴露兼容性问题
- 避免测试结果的不确定性

### RAII 资源管理

通过 `ManagedBackendTexture` 和 `sk_sp` 实现自动资源管理：
- 用户无需手动释放纹理
- 防止资源泄漏
- 简化错误处理

### 颜色预处理

在创建纯色图像时自动调整颜色：
- 确保颜色语义与 `alphaType` 一致
- 避免用户手动预乘的麻烦
- 减少错误使用的风险

### 平台差异的适配

Ganesh 和 Graphite 的实现策略不同：
- **Ganesh**：直接使用 GPU 填充颜色
- **Graphite**：通过 CPU 位图中转

这种差异对用户透明，但反映了底层 API 的能力差异。

## 性能考量

### 纹理创建开销

每次调用都会分配新的 GPU 纹理：
- GPU 内存分配可能涉及驱动交互
- 对于大型纹理，开销不可忽略

建议：在测试循环中复用图像，避免频繁创建。

### 像素数据上传

从 `SkPixmap` 创建图像需要 CPU 到 GPU 的数据传输：
- 受 PCIe 带宽限制
- 对于高分辨率图像，可能成为瓶颈

优化：
- 使用较小的测试图像
- 考虑使用压缩格式（如果测试允许）

### 纯色图像的效率

**Ganesh**：直接在 GPU 上填充，高效。

**Graphite**：通过 CPU 位图中转：
- 需要 CPU 端内存分配和填充
- 额外的上传步骤
- 对于小图像影响不大，大图像可能有明显开销

### Mipmap 生成

Graphite 版本支持 `mipmapped` 参数：
- 自动生成 mipmap 金字塔
- 需要额外 ~33% 的内存
- 生成过程可能涉及 CPU 下采样（在 `ManagedGraphiteTexture` 中）

### Renderable 标志的影响

设置 `Renderable::kYes` 可能：
- 需要额外的渲染目标配置
- 某些格式只支持采样或渲染，不支持两者
- 可能影响内存布局和性能

建议：只在需要渲染到纹理时设置为 `kYes`。

### 测试场景的权衡

该模块优化目标是便利性而非极致性能：
- 适合单次或少量图像创建
- 简化测试代码的编写
- 生产代码应使用更高效的图像创建路径

## 相关文件

### 核心依赖

- `include/core/SkImage.h` - Image 抽象接口
- `include/core/SkPixmap.h` - 像素数据容器
- `include/core/SkColor.h` - 颜色定义
- `include/core/SkImageInfo.h` - 图像元数据
- `include/core/SkColorSpace.h` - 色彩空间

### 工具依赖

- `tools/gpu/ManagedBackendTexture.h` - 托管后端纹理

### Ganesh 相关

- `include/gpu/ganesh/GrDirectContext.h` - Ganesh 上下文
- `include/gpu/ganesh/GrBackendSurface.h` - 后端纹理
- `include/gpu/ganesh/SkImageGanesh.h` - Ganesh Image 工厂

### Graphite 相关

- `include/gpu/graphite/Recorder.h` - Graphite 记录器
- `include/gpu/graphite/Image.h` - Graphite Image 工厂

### 使用场景

- `tests/` - GPU 单元测试
- `gm/` - GM 测试
- `bench/` - 性能基准测试
- 示例代码和教程

### 相关工具类

- `tools/gpu/BackendSurfaceFactory.h` - Surface 工厂（相关但不同：Surface vs Image）
- `tools/gpu/YUVUtils.h` - YUV 图像工具
- `tools/gpu/ProxyUtils.h` - GPU 代理工具
