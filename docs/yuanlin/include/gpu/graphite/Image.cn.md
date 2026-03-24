# Image (Graphite)

> 源文件: `include/gpu/graphite/Image.h`

## 概述

Image.h 定义了 Graphite GPU 后端中创建和管理 SkImage 的公共 API。它提供了包装后端纹理、创建 Promise Image、YUVA 图像处理、纹理转换、子集提取和滤镜应用等功能,是 Graphite 图像处理系统的核心接口文件。

## 架构位置

该文件位于 Skia Graphite GPU 后端的公共接口层,属于 `SkImages` 命名空间。它是应用程序创建和操作 GPU 图像的主要入口点,与 Surface、Recorder 等核心组件紧密协作,构成了 Graphite 的图像管理架构。

## 主要类型定义

### 回调函数类型

```cpp
using TextureReleaseProc = void (*)(ReleaseContext);
using GraphitePromiseImageContext = void*;
using GraphitePromiseTextureFulfillContext = void*;
using GraphitePromiseTextureReleaseContext = void*;

using GraphitePromiseTextureFulfillProc =
    std::tuple<skgpu::graphite::BackendTexture, GraphitePromiseTextureReleaseContext> (*)(
        GraphitePromiseTextureFulfillContext);
using GraphitePromiseImageReleaseProc = void (*)(GraphitePromiseImageContext);
using GraphitePromiseTextureReleaseProc = void (*)(GraphitePromiseTextureReleaseContext);
```

**用途**: Promise Image 的生命周期管理回调机制
- `TextureReleaseProc`: 纹理释放回调
- `GraphitePromiseTextureFulfillProc`: 获取后端纹理的回调,返回纹理和释放上下文
- `GraphitePromiseImageReleaseProc`: Image 中心数据释放回调
- `GraphitePromiseTextureReleaseProc`: 纹理资源释放回调

### GenerateMipmapsFromBase

```cpp
enum class GenerateMipmapsFromBase : bool { kNo, kYes };
```

**用途**: 指示是否从基础级别生成 mipmap

## 公共 API 函数

### WrapTexture 系列

#### WrapTexture (完整版本)

```cpp
SK_API sk_sp<SkImage> WrapTexture(skgpu::graphite::Recorder*,
                                  const skgpu::graphite::BackendTexture&,
                                  SkColorType colorType,
                                  SkAlphaType alphaType,
                                  sk_sp<SkColorSpace> colorSpace,
                                  skgpu::Origin origin,
                                  GenerateMipmapsFromBase generateMipmapsFromBase,
                                  TextureReleaseProc = nullptr,
                                  ReleaseContext = nullptr,
                                  std::string_view label = {});
```

- **功能**: 将 GPU 后端纹理包装为 SkImage
- **参数**:
  - `recorder`: 记录命令的 Recorder
  - `backendTexture`: 后端纹理对象
  - `colorType/alphaType/colorSpace`: 颜色信息
  - `origin`: TopLeft 或 BottomLeft
  - `generateMipmapsFromBase`: 是否生成 mipmap
    - `kYes`: 从基础级别连续下采样生成上层 mipmap
    - `kNo`: 假设上层 mipmap 已有效(如果纹理有 mipmap)
  - `releaseProc/releaseContext`: 释放回调
  - `label`: 调试标签
- **返回值**: 成功返回 SkImage,失败返回 nullptr
- **前置条件**:
  - 如果 `generateMipmapsFromBase` 为 kYes,纹理必须是 mipmapped 且可渲染
  - 纹理格式必须被 recorder 支持
- **注意**: 客户端仍负责管理后端纹理的生命周期

#### WrapTexture (简化版本)

```cpp
SK_API sk_sp<SkImage> WrapTexture(skgpu::graphite::Recorder*,
                                  const skgpu::graphite::BackendTexture&,
                                  SkColorType colorType,
                                  SkAlphaType alphaType,
                                  sk_sp<SkColorSpace> colorSpace,
                                  skgpu::Origin origin,
                                  TextureReleaseProc = nullptr,
                                  ReleaseContext = nullptr,
                                  std::string_view label = {});
```

- **功能**: WrapTexture 的重载版本,不生成 mipmap
- **等价于**: `generateMipmapsFromBase = kNo`

#### WrapTexture (默认原点版本)

```cpp
SK_API sk_sp<SkImage> WrapTexture(skgpu::graphite::Recorder*,
                                  const skgpu::graphite::BackendTexture&,
                                  SkColorType colorType,
                                  SkAlphaType alphaType,
                                  sk_sp<SkColorSpace> colorSpace,
                                  TextureReleaseProc = nullptr,
                                  ReleaseContext = nullptr,
                                  std::string_view label = {});
```

- **功能**: 使用默认原点的 WrapTexture 版本
- **默认原点**: 取决于后端实现

### Promise Image API

#### PromiseTextureFrom

```cpp
SK_API sk_sp<SkImage> PromiseTextureFrom(skgpu::graphite::Recorder*,
                                         SkISize dimensions,
                                         const skgpu::graphite::TextureInfo&,
                                         const SkColorInfo&,
                                         skgpu::Origin origin,
                                         skgpu::graphite::Volatile,
                                         GraphitePromiseTextureFulfillProc,
                                         GraphitePromiseImageReleaseProc,
                                         GraphitePromiseTextureReleaseProc,
                                         GraphitePromiseImageContext,
                                         std::string_view label = {});
```

- **功能**: 创建 Promise Image,延迟提供实际纹理
- **参数**:
  - `dimensions`: 纹理尺寸
  - `textureInfo`: 纹理结构信息
  - `colorInfo`: 颜色类型、透明度类型和色彩空间
  - `origin`: 原点位置
  - `isVolatile`: 挥发性标志
    - `Volatile::kNo`: 非挥发,fulfill 一次
    - `Volatile::kYes`: 挥发,每次插入都 fulfill
  - `fulfill`: 获取后端纹理的函数
  - `imageRelease`: 图像数据释放回调
  - `textureRelease`: 纹理释放回调
  - `imageContext`: 传递给回调的上下文
- **返回值**: 成功返回 SkImage,失败返回 nullptr

**回调调用时机详解**:

##### 非挥发 Promise Image (Volatile::kNo)

1. **fulfill**: 在 `Context::insertRecording` 时调用
2. **imageRelease**: 总是调用一次,当 Skia 不再尝试 fulfill 时
3. **textureRelease**:
   - 如果 fulfill 失败: 永不调用
   - 如果 fulfill 成功: GPU 完成时调用一次(通常在 `Context::submit` 期间)
4. **多次使用**: 可在多个 Recording 中使用,fulfill 会被多次调用直到成功
5. **失败恢复**: 如果 insertRecording 失败,后续 insertRecording 会继续尝试 fulfill

##### 挥发 Promise Image (Volatile::kYes)

1. **fulfill**: 每次 `insertRecording` 时都调用
2. **imageRelease**: 仍然只调用一次
3. **textureRelease**: 每次成功 fulfill 后,对应的 GPU 完成时调用一次
4. **失败处理**: 某次 fulfill 失败不影响后续调用

#### PromiseTextureFrom (默认原点版本)

```cpp
SK_API sk_sp<SkImage> PromiseTextureFrom(skgpu::graphite::Recorder*,
                                         SkISize dimensions,
                                         const skgpu::graphite::TextureInfo&,
                                         const SkColorInfo&,
                                         skgpu::graphite::Volatile,
                                         GraphitePromiseTextureFulfillProc,
                                         GraphitePromiseImageReleaseProc,
                                         GraphitePromiseTextureReleaseProc,
                                         GraphitePromiseImageContext);
```

### YUVA Promise Image

#### PromiseTextureFromYUVA

```cpp
SK_API sk_sp<SkImage> PromiseTextureFromYUVA(skgpu::graphite::Recorder*,
                                             const skgpu::graphite::YUVABackendTextureInfo&,
                                             sk_sp<SkColorSpace> imageColorSpace,
                                             skgpu::graphite::Volatile,
                                             GraphitePromiseTextureFulfillProc,
                                             GraphitePromiseImageReleaseProc,
                                             GraphitePromiseTextureReleaseProc,
                                             GraphitePromiseImageContext imageContext,
                                             GraphitePromiseTextureFulfillContext planeContexts[],
                                             std::string_view label = {});
```

- **功能**: 从 YUV[A] 平面数据创建 Promise Image
- **平面支持**: 最多 4 个平面(Y, U, V, A)
- **参数**:
  - `backendTextureInfo`: 描述平面排列、格式和 RGB 转换
  - `imageColorSpace`: RGB 色彩空间
  - `planeContexts`: 每个平面的 fulfill 上下文数组
- **回调**: 每个平面有独立的 fulfill 和 textureRelease 调用
- **Mipmap**: 当前忽略 mipmap 属性,未来会要求 fulfill 返回 mipmap 纹理
- **失败处理**: imageRelease 即使失败也会调用

### 纹理转换 API

#### TextureFromImage

```cpp
SK_API sk_sp<SkImage> TextureFromImage(skgpu::graphite::Recorder*,
                                       const SkImage*,
                                       SkImage::RequiredProperties = {});
```

- **功能**: 将任意 SkImage 转换为 Graphite 纹理支持的 Image
- **参数**:
  - `recorder`: Graphite Recorder
  - `image`: 源图像
  - `RequiredProperties`: 必需的属性(如 mipmap)
- **返回值**:
  - 如果源已是兼容的 Graphite Image: 返回原图像
  - 如果需要转换: 返回新的 Graphite Image
  - 如果失败: 返回 nullptr
- **失败情况**:
  - Recorder 为 nullptr
  - 源图像是其他 Recorder 创建且未提交
  - mipmap 要求不兼容
- **Mipmap 处理**: 假设 GPU 总是支持 MIP maps

#### TextureFromImage (智能指针版本)

```cpp
inline sk_sp<SkImage> TextureFromImage(skgpu::graphite::Recorder* r,
                                       const sk_sp<const SkImage>& img,
                                       SkImage::RequiredProperties props = {});
```

### YUVA 纹理创建

#### TextureFromYUVAPixmaps

```cpp
SK_API sk_sp<SkImage> TextureFromYUVAPixmaps(skgpu::graphite::Recorder*,
                                             const SkYUVAPixmaps& pixmaps,
                                             SkImage::RequiredProperties = {},
                                             bool limitToMaxTextureSize = false,
                                             sk_sp<SkColorSpace> imgColorSpace = nullptr,
                                             std::string_view label = {});
```

- **功能**: 从 SkYUVAPixmaps 创建纹理图像
- **参数**:
  - `pixmaps`: 包含 YUV 平面数据和转换信息的 Pixmaps
  - `RequiredProperties`: 必需属性(如 mipmap)
  - `limitToMaxTextureSize`: 是否限制到 GPU 最大纹理尺寸
  - `imgColorSpace`: RGB 结果的色彩空间
- **行为**: 图像保持平面格式,每个平面转换为单独的纹理
- **色彩空间**: `imgColorSpace` 指定转换到 RGB 后的色彩空间
- **限制**: 仅支持 GPU 后端,recorder 为 nullptr 会失败
- **生命周期**: SkYUVAPixmaps 调用后可释放

#### TextureFromYUVATextures

```cpp
SK_API sk_sp<SkImage> TextureFromYUVATextures(
        skgpu::graphite::Recorder* recorder,
        const skgpu::graphite::YUVABackendTextures& yuvaBackendTextures,
        sk_sp<SkColorSpace> imageColorSpace,
        TextureReleaseProc = nullptr,
        ReleaseContext = nullptr,
        std::string_view label = {});
```

- **功能**: 从 YUV[A] 后端纹理创建 SkImage
- **参数**:
  - `yuvaBackendTextures`: 包含 YUVA 数据和转换描述的纹理集
  - `imageColorSpace`: RGB 色彩空间
  - `releaseProc/releaseContext`: 释放回调
- **生命周期**: 客户端负责确保后端纹理在 Image 使用期间有效

#### TextureFromYUVAImages

```cpp
SK_API sk_sp<SkImage> TextureFromYUVAImages(
        skgpu::graphite::Recorder* recorder,
        const SkYUVAInfo& yuvaInfo,
        SkSpan<const sk_sp<SkImage>> images,
        sk_sp<SkColorSpace> imageColorSpace);
```

- **功能**: 从 YUV[A] 平面 SkImage 创建组合 Image
- **参数**:
  - `yuvaInfo`: YUVA 格式描述
  - `images`: SkImage 数组,每个代表一个平面
  - `imageColorSpace`: RGB 色彩空间
- **要求**:
  - 所有 images 必须是 Graphite 类型
  - 不持有 SkImage 的引用,但持有底层 TextureProxy
- **返回值**: 成功返回 Image,任一输入非 Graphite 则返回 nullptr

### 子集与滤镜

#### SubsetTextureFrom

```cpp
SK_API sk_sp<SkImage> SubsetTextureFrom(skgpu::graphite::Recorder* recorder,
                                        const SkImage* img,
                                        const SkIRect& subset,
                                        SkImage::RequiredProperties props = {});
```

- **功能**: 提取图像子集并上传为纹理
- **参数**:
  - `img`: 源图像
  - `subset`: 子区域边界
  - `props`: 必需属性(如 mipmap)
- **失败情况**:
  - subset 为空
  - subset 不在图像边界内
  - 无法读取或复制像素
  - 纹理后端的 context 不匹配
- **返回值**: 成功返回纹理支持的 Image,失败返回 nullptr

#### MakeWithFilter

```cpp
SK_API sk_sp<SkImage> MakeWithFilter(skgpu::graphite::Recorder* recorder,
                                     sk_sp<SkImage> src,
                                     const SkImageFilter* filter,
                                     const SkIRect& subset,
                                     const SkIRect& clipBounds,
                                     SkIRect* outSubset,
                                     SkIPoint* offset);
```

- **功能**: 在 GPU 上对图像应用滤镜
- **参数**:
  - `src`: 源图像
  - `filter`: 图像滤镜
  - `subset`: 滤镜处理的区域
  - `clipBounds`: 预期的滤镜结果边界
  - `outSubset`: 输出实际有效边界
  - `offset`: 输出平移量
- **返回值**: 滤镜后的 Image,失败返回 nullptr
- **用途**: 动画中大小变化的滤镜效果
- **优势**: GPU 纹理可复用于不同大小的效果,outSubset 描述有效区域,offset 对齐动画帧

## 内部实现细节

### Promise Image 的状态机

#### 非挥发 Promise Image

```
创建 → insertRecording → fulfill 成功 → GPU 执行 → textureRelease → imageRelease
                      ↓
                  fulfill 失败 → insertRecording 继续尝试
```

#### 挥发 Promise Image

```
创建 → insertRecording₁ → fulfill₁ 成功 → GPU 执行₁ → textureRelease₁
       ↓
       insertRecording₂ → fulfill₂ 成功 → GPU 执行₂ → textureRelease₂
       ...
       最终 → imageRelease (仅一次)
```

### Mipmap 生成策略

- **WrapTexture**: 支持从基础级别生成
- **TextureFromImage**: 根据 RequiredProperties
- **YUVA**: 当前忽略,未来强制要求

### 颜色空间转换

- **输入**: 源 Image 的色彩空间
- **输出**: 绘制时转换到目标色彩空间
- **YUVA**: YUV → RGB 转换后应用 imageColorSpace

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkImage.h` | SkImage 基类 |
| `include/core/SkColorSpace.h` | 色彩空间管理 |
| `include/gpu/GpuTypes.h` | Mipmapped 等类型 |
| `skgpu::graphite::Recorder` | 命令记录 |
| `skgpu::graphite::BackendTexture` | 后端纹理抽象 |
| `skgpu::graphite::TextureInfo` | 纹理信息 |
| `SkYUVAInfo/SkYUVAPixmaps` | YUVA 数据结构 |

### 被依赖的模块

- 应用层图像加载和处理代码
- Graphite 内部渲染管线
- Surface 实现(用于 readPixels 等)

## 设计模式与设计决策

### 命名空间工厂模式

使用 `SkImages` 命名空间而非类静态方法,与 Surface API 保持一致。

### 回调链模式

Promise Image 使用三个回调:
- `fulfill`: 生产者
- `imageRelease`: 协调者
- `textureRelease`: 消费者

### 重载提供便利性

多个 WrapTexture 重载:
- 完整控制版本
- 简化版本(合理默认值)
- 智能指针适配版本

### 平面独立性

YUVA 图像每个平面独立管理:
- 独立的 fulfill 上下文
- 独立的 textureRelease
- 简化多平面处理

## 性能考量

### Promise Image 的延迟加载

- **优势**: 纹理创建推迟到真正需要时
- **适用**: 纹理来自异步源(网络、解码)
- **开销**: 回调机制有轻微开销

### YUVA vs RGB

- **内存**: YUVA 通常比 RGBA 节省 30-50%
- **带宽**: 采样时带宽更低
- **转换开销**: GPU 上 YUV→RGB 转换很高效

### Mipmap 生成

- **运行时生成**: `GenerateMipmapsFromBase::kYes` 有开销
- **预生成**: 源纹理已有 mipmap 更高效
- **权衡**: 运行时生成灵活但慢,预生成快但占空间

### TextureFromImage 缓存

- 推荐配合 ImageProvider 使用
- 避免重复纹理上传
- 对频繁使用的图像显著提升性能

## 使用示例

### 包装外部纹理

```cpp
sk_sp<SkImage> img = SkImages::WrapTexture(
    recorder, backendTexture,
    kRGBA_8888_SkColorType, kPremul_SkAlphaType,
    SkColorSpace::MakeSRGB(), skgpu::Origin::kTopLeft_Origin,
    SkImages::GenerateMipmapsFromBase::kNo);
```

### 非挥发 Promise Image

```cpp
auto fulfill = [](void* ctx) -> std::tuple<BackendTexture, void*> {
    auto* loader = static_cast<TextureLoader*>(ctx);
    return {loader->getTexture(), loader};
};

auto imgRelease = [](void* ctx) {
    // 清理 loader
};

auto texRelease = [](void* ctx) {
    auto* loader = static_cast<TextureLoader*>(ctx);
    loader->releaseTexture();
};

sk_sp<SkImage> img = SkImages::PromiseTextureFrom(
    recorder, {512, 512}, textureInfo, colorInfo,
    skgpu::Origin::kTopLeft_Origin, Volatile::kNo,
    fulfill, imgRelease, texRelease, loader);
```

### 从 YUVA Pixmaps 创建

```cpp
SkYUVAPixmaps yuvaPixmaps = ...;
sk_sp<SkImage> img = SkImages::TextureFromYUVAPixmaps(
    recorder, yuvaPixmaps,
    SkImage::RequiredProperties{},
    false, // limitToMaxTextureSize
    SkColorSpace::MakeSRGB());
```

### 应用滤镜

```cpp
SkIRect outSubset;
SkIPoint offset;
sk_sp<SkImage> filtered = SkImages::MakeWithFilter(
    recorder, srcImage, blurFilter,
    SkIRect::MakeWH(src->width(), src->height()),
    clipBounds, &outSubset, &offset);
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/gpu/graphite/Surface.h` | Surface 与 Image 转换 |
| `include/gpu/graphite/Recorder.h` | 命令记录器 |
| `include/gpu/graphite/BackendTexture.h` | 后端纹理定义 |
| `include/gpu/graphite/TextureInfo.h` | 纹理信息 |
| `include/core/SkYUVAInfo.h` | YUVA 格式定义 |
| `include/core/SkYUVAPixmaps.h` | YUVA Pixmaps 容器 |
| `src/gpu/graphite/Image_Graphite.cpp` | 实现文件 |
