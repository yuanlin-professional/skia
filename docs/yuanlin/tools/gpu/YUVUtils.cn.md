# YUVUtils

> 源文件
> - tools/gpu/YUVUtils.h
> - tools/gpu/YUVUtils.cpp

## 概述

`YUVUtils` 是 Skia GPU 工具集中用于处理 YUV 色彩空间图像的实用工具模块。YUV（也称 YCbCr）是一种将图像分解为亮度（Y）和色度（U、V）分量的色彩表示方式，广泛应用于视频编解码和图像压缩领域。该模块提供了将 RGB 图像转换为 YUV 平面、从 JPEG 等编码数据中提取 YUV 平面，以及在不同 GPU 后端（Ganesh 和 Graphite）上创建 YUV 纹理图像的功能。

核心功能包括：将 RGBA 图像分割为独立的 Y、U、V（和可选的 A）平面、延迟加载和缓存 YUV 图像、支持多种 YUV 创建方式（从像素数据、生成器、纹理或图像）、处理子采样和色彩空间转换。该模块在测试、基准测试和调试工具中广泛使用，帮助验证 Skia 的 YUV 渲染路径。

## 架构位置

`YUVUtils` 位于 `tools/gpu/` 目录下，属于 GPU 相关的测试工具层，而非 Skia 的核心渲染引擎。它在架构中的位置如下：

1. **测试框架层**：为 DM（Skia 的主要测试工具）、GM（Golden Master 测试）和各类基准测试提供 YUV 图像生成和管理能力
2. **GPU 抽象层适配**：支持 Ganesh（传统 GPU 后端）和 Graphite（新一代 GPU 后端）两种架构
3. **编解码器集成**：与 Skia 的编解码器（`SkCodecImageGenerator`）集成，从 JPEG 等格式中提取原始 YUV 数据

该模块依赖于 Skia 的核心图像类（`SkImage`、`SkBitmap`）、GPU 类型定义、以及 YUV 相关的数据结构（`SkYUVAInfo`、`SkYUVAPixmaps`）。它不直接参与用户应用的渲染，而是作为内部测试和开发工具使用。

## 主要类与结构体

### sk_gpu_test 命名空间

所有公共 API 都位于 `sk_gpu_test` 命名空间中，表明这是测试工具代码。

### LazyYUVImage 类

延迟加载的 YUV 图像管理器，核心功能类。

**关键成员变量：**
- `SkYUVAPixmaps fPixmaps`：存储解码后的 YUV 平面数据
- `skgpu::Mipmapped fMipmapped`：是否需要 mipmap
- `sk_sp<SkColorSpace> fColorSpace`：色彩空间信息
- `sk_sp<SkImage> fYUVImage[4]`：缓存的四种类型的 SkImage 对象

**Type 枚举：**
- `kFromPixmaps`：从像素数据直接创建 GPU 纹理
- `kFromGenerator`：通过图像生成器延迟创建
- `kFromTextures`：从预先创建的后端纹理构建
- `kFromImages`：从独立的平面图像构建（仅 Graphite）

### Generator 类（匿名命名空间）

继承自 `SkImageGenerator`，用于将 YUV 平面数据转换为 RGBA 像素数据。

**关键成员变量：**
- `SkYUVAPixmaps fPixmaps`：YUV 平面数据
- `SkBitmap fFlattened`：缓存的扁平化 RGBA 位图

**核心方法：**
- `onGetPixels()`：将 YUV 数据转换为 RGBA 像素
- `onQueryYUVAInfo()`：返回 YUV 平面信息
- `onGetYUVAPlanes()`：直接提供 YUV 平面数据

### 辅助函数

#### convert_yuva_to_rgba
```cpp
static SkPMColor convert_yuva_to_rgba(const float mtx[20], uint8_t yuva[4])
```
使用色彩矩阵将 YUVA 值转换为预乘 RGBA 颜色。

#### look_up
```cpp
static uint8_t look_up(SkPoint normPt, const SkPixmap& pmap, SkColorChannel channel)
```
从归一化坐标在像素图中查找特定通道的值，用于处理子采样。

## 公共 API 函数

### MakeYUVAPlanesAsA8

```cpp
std::tuple<std::array<sk_sp<SkImage>, SkYUVAInfo::kMaxPlanes>, SkYUVAInfo>
MakeYUVAPlanesAsA8(SkImage* src,
                   SkYUVColorSpace cs,
                   SkYUVAInfo::Subsampling ss,
                   GrRecordingContext* rContext);
```

将输入的 RGBA 图像分解为 A8 格式的 YUV(A) 平面。

**参数：**
- `src`：源 RGBA 图像
- `cs`：目标 YUV 色彩空间
- `ss`：子采样模式（如 4:2:0、4:2:2、4:4:4）
- `rContext`：GPU 上下文，如果为 null 则创建 CPU 图像

**返回值：** 平面图像数组和描述平面配置的 `SkYUVAInfo`

### LazyYUVImage::Make（从 SkData）

```cpp
static std::unique_ptr<LazyYUVImage> Make(sk_sp<SkData> data,
                                          skgpu::Mipmapped = skgpu::Mipmapped::kNo,
                                          sk_sp<SkColorSpace> = nullptr);
```

从编码数据（如 JPEG）创建 LazyYUVImage。如果数据无法解码为 YUV 平面，返回 nullptr。

**参数：**
- `data`：编码的图像数据
- `mipmapped`：是否生成 mipmap
- `colorSpace`：自定义色彩空间（可选）

### LazyYUVImage::Make（从 SkYUVAPixmaps）

```cpp
static std::unique_ptr<LazyYUVImage> Make(SkYUVAPixmaps pixmaps,
                                          skgpu::Mipmapped = skgpu::Mipmapped::kNo,
                                          sk_sp<SkColorSpace> = nullptr);
```

从已有的 YUV 平面数据创建 LazyYUVImage。

### LazyYUVImage::refImage

```cpp
sk_sp<SkImage> refImage(GrRecordingContext* rContext, Type type);
sk_sp<SkImage> refImage(GrDirectContext* dContext, Type type);
sk_sp<SkImage> refImage(skgpu::graphite::Recorder* recorder, Type type);  // Graphite
```

获取指定类型的 SkImage 对象。如果该类型的图像尚未创建或上下文已改变，会自动创建并缓存。

**参数：**
- `rContext/dContext/recorder`：GPU 上下文或记录器
- `type`：图像创建类型

**返回值：** 缓存的或新创建的 SkImage 对象

### LazyYUVImage::dimensions

```cpp
SkISize dimensions() const { return fPixmaps.yuvaInfo().dimensions(); }
```

返回图像的尺寸。

### LazyYUVImage::hasImageIndex

```cpp
bool hasImageIndex() { return imageMap.size() > 0; }
```

检查是否已初始化图像索引（此方法在头文件声明但在 UrlDataManager 中定义，此处可能为文档错误）。

## 内部实现细节

### YUV 到 RGBA 转换流程

在 `Generator::onGetPixels()` 中实现：

1. **获取转换矩阵**：使用 `SkColorMatrix_YUV2RGB()` 获取 YUV 到 RGB 的 5x4 色彩矩阵
2. **处理图像方向**：通过 `inverseOriginMatrix()` 处理 EXIF 旋转
3. **逐像素转换**：
   - 对于每个目标像素，计算其在源平面中的归一化坐标
   - 从 Y、U、V（和可选的 A）平面中查找对应的值
   - 使用色彩矩阵转换为 RGB
   - 预乘 alpha 值生成最终 RGBA 颜色
4. **缓存结果**：将扁平化的 RGBA 位图缓存在 `fFlattened` 中

### RGB 到 YUV 平面分解

在 `MakeYUVAPlanesAsA8()` 中实现：

1. **获取转换矩阵**：使用 `SkColorMatrix_RGB2YUV()` 获取 RGB 到 YUV 的 5x4 矩阵
2. **确定平面配置**：根据图像是否透明选择 Y_U_V 或 Y_U_V_A 配置
3. **计算平面尺寸**：根据子采样模式计算每个平面的尺寸
4. **生成每个平面**：
   - 为每个平面创建 A8 格式的 Surface
   - 构造色彩过滤器，将 RGB 矩阵的第 i 行复制到 A 通道
   - 使用 `kSrc` 混合模式绘制源图像到 Surface
   - 提取 Surface 的快照作为平面图像

### 延迟创建机制

`LazyYUVImage` 采用延迟创建策略：
- 构造时只解码和存储 YUV 平面的原始像素数据
- 首次调用 `refImage()` 时才根据指定类型创建 GPU 纹理
- 创建的图像按类型缓存在 `fYUVImage[]` 数组中
- 如果 GPU 上下文改变，会重新创建图像

### Ganesh 和 Graphite 的差异

**Ganesh 实现：**
- 使用 `GrRecordingContext` 和 `GrDirectContext`
- 支持 `kFromPixmaps`、`kFromGenerator`、`kFromTextures` 三种类型
- 使用 `GrYUVABackendTextures` 包装后端纹理
- 检查上下文是否被放弃（`abandoned()`）

**Graphite 实现：**
- 使用 `skgpu::graphite::Recorder`
- 额外支持 `kFromImages` 类型，允许从独立的平面图像构建
- 使用 `skgpu::graphite::YUVABackendTextures`
- 支持手动构建 mipmap 金字塔（通过 `GenerateMipmapsFromBase`）
- 使用 `ManagedGraphiteTexture` 管理纹理生命周期

### 子采样处理

子采样（如 4:2:0）意味着色度平面的分辨率低于亮度平面。在转换时：
- `SkYUVAInfo::PlaneDimensions()` 计算每个平面的正确尺寸
- `look_up()` 函数使用归一化坐标，自动处理不同平面的分辨率差异
- 使用线性插值采样确保色度值在正确位置

## 依赖关系

### 核心依赖

- **SkImage / SkBitmap**：图像数据的基本容器
- **SkYUVAInfo / SkYUVAPixmaps**：YUV 平面信息和数据的标准表示
- **SkColorSpace**：色彩空间管理
- **SkCodecImageGenerator**：从编码数据解码 YUV 平面
- **SkYUVMath**：YUV 和 RGB 之间的色彩矩阵转换

### GPU 依赖

**Ganesh：**
- `GrRecordingContext` / `GrDirectContext`：GPU 上下文
- `GrBackendSurface` / `GrYUVABackendTextures`：后端纹理封装
- `SkImageGanesh` / `SkSurfaceGanesh`：Ganesh 特定的图像和 Surface 工厂

**Graphite：**
- `skgpu::graphite::Recorder`：命令记录器
- `skgpu::graphite::BackendTexture` / `YUVABackendTextures`：Graphite 后端纹理

### 工具依赖

- **ManagedBackendTexture / ManagedGraphiteTexture**：自动管理后端纹理生命周期的辅助类

### 被依赖

- DM 测试框架
- GM（Golden Master）测试用例
- 性能基准测试工具
- 图像编解码器测试

## 设计模式与设计决策

### 工厂模式

`LazyYUVImage::Make()` 使用静态工厂方法，隐藏构造细节，只有在成功解码 YUV 数据后才返回有效对象。

### 延迟初始化（Lazy Initialization）

- 构造时只解码像素数据，不创建 GPU 纹理
- 延迟到首次调用 `refImage()` 时才创建 GPU 资源
- 减少不必要的 GPU 内存占用，特别是在测试场景中可能需要多种类型的图像时

### 缓存模式

通过 `fYUVImage[4]` 数组缓存四种类型的图像，避免重复创建：
- 使用枚举值作为数组索引
- 在创建前检查缓存和上下文有效性
- 节省创建开销，特别是在测试循环中

### 适配器模式

`Generator` 类适配 `SkYUVAPixmaps` 到 `SkImageGenerator` 接口：
- 允许 YUV 数据通过标准的图像生成器接口使用
- 支持延迟转换为 RGBA 格式
- 兼容 Skia 的延迟图像创建机制

### 策略模式

通过 `Type` 枚举支持多种图像创建策略：
- `kFromPixmaps`：直接上传
- `kFromGenerator`：延迟转换
- `kFromTextures`：预创建纹理
- `kFromImages`：从平面图像合成

不同策略适用于不同的测试场景，灵活性高。

### 双后端支持设计

使用条件编译（`#if defined(SK_GANESH)` / `#if defined(SK_GRAPHITE)`）和函数重载支持两个 GPU 后端：
- 共享核心逻辑（YUV 解码、像素数据管理）
- 隔离后端特定代码
- 保持接口一致性

## 性能考量

### 内存效率

- **YUV 数据复用**：一份 YUV 平面数据可以生成多种类型的 SkImage，避免重复存储
- **子采样节省**：YUV 4:2:0 模式下，色度平面只有亮度平面的 1/4 大小，显著减少内存占用
- **延迟创建**：只有在需要时才创建 GPU 纹理，避免浪费

### GPU 纹理管理

- **ManagedBackendTexture**：自动管理纹理生命周期，防止泄漏
- **纹理复用**：通过缓存机制避免重复创建相同类型的纹理
- **Direct Context 检查**：确保只在有效的 GPU 上下文上创建纹理

### 转换性能

- **色彩矩阵转换**：使用预计算的 5x4 矩阵进行快速线性变换
- **扁平化缓存**：`Generator` 中的 `fFlattened` 位图缓存转换结果，避免重复计算
- **GPU 加速**：在 GPU 上使用 ColorFilter 进行 RGB 到 YUV 的转换，利用并行计算

### 适用场景限制

- **主要用于测试**：代码优化主要针对测试场景，而非生产环境的高性能需求
- **单线程设计**：未考虑线程安全，不适合多线程并发访问
- **完整 Mipmap 要求**：Graphite 的 `kFromImages` 模式需要完整的 mipmap 层级，可能增加内存开销

## 相关文件

### 核心依赖

- `include/core/SkYUVAPixmaps.h` - YUV 平面数据封装
- `include/core/SkYUVAInfo.h` - YUV 配置信息
- `src/core/SkYUVMath.h` - YUV 色彩转换数学
- `src/codec/SkCodecImageGenerator.h` - 编解码器生成器

### GPU 后端

- `include/gpu/ganesh/GrYUVABackendTextures.h` - Ganesh YUV 纹理封装
- `include/gpu/graphite/YUVABackendTextures.h` - Graphite YUV 纹理封装
- `tools/gpu/ManagedBackendTexture.h` - 纹理生命周期管理

### 使用场景

- `dm/DMSrcSink.cpp` - DM 测试框架中的图像源
- `gm/` - 各类 GM 测试用例
- `bench/` - 性能基准测试
- `tests/YUVTest.cpp` - YUV 功能单元测试

### 相关工具

- `tools/gpu/BackendSurfaceFactory.h` - GPU Surface 创建工具
- `tools/Resources.h` - 测试资源管理
