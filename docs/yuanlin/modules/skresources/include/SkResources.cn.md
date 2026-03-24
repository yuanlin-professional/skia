# SkResources - 资源提供器接口

> 源文件: `modules/skresources/include/SkResources.h`

## 概述

SkResources.h 定义了 Skia 富媒体模块（如 Lottie 动画）所需的外部资源加载接口体系。它提供了图片资源代理（ImageAsset）、外部音轨（ExternalTrackAsset）、资源提供器（ResourceProvider）及其代理类（缓存代理、Data URI 代理）等一系列抽象和实现，使得动画等富媒体内容能够将图片、字体、音频等外部资源的加载委托给嵌入方。

## 架构位置

SkResources 位于 `skresources` 命名空间内，是 Skia 动画模块（skottie）与外部资源之间的桥梁层。动画加载时通过 ResourceProvider 请求资源，嵌入方实现该接口以提供实际的资源数据。

**调用链**: `skottie::Animation::Make()` -> `ResourceProvider::loadImageAsset()` / `loadTypeface()` -> 嵌入方实现

## 主要类与结构体

### `ImageAsset`（抽象基类）
图片资源代理接口，支持静态和动画图片。
- `isMultiFrame()`: 是否为多帧动画图片
- `getFrame(float t)`: 获取指定时间码的帧（已弃用）
- `getFrameData(float t)`: 获取帧数据（含采样、矩阵、缩放策略）
- `SizeFit` 枚举: Fill/Start/Center/End/None 五种缩放策略
- `FrameData` 结构体: 包含 SkImage、SkSamplingOptions、SkMatrix 和 SizeFit

### `MultiFrameImageAsset`
ImageAsset 的具体实现，基于 SkAnimCodecPlayer 支持多帧动画和图片预解码。

### `ExternalTrackAsset`（抽象基类）
外部音轨接口，`seek(float t)` 控制播放时间码。

### `ResourceProvider`（抽象基类）
资源加载的核心接口：
- `load()`: 加载通用资源（如嵌套动画）
- `loadImageAsset()`: 加载图片资源
- `loadAudioAsset()`: 加载音频资源
- `loadFont()`: 加载字体数据（已弃用）
- `loadTypeface()`: 加载字体为 SkTypeface

### `FileResourceProvider`
基于文件系统的 ResourceProvider 实现，从指定目录加载资源。

### `ResourceProviderProxyBase`
ResourceProvider 的代理基类，将所有调用转发给内部持有的代理对象。

### `CachingResourceProvider`
在 ResourceProviderProxyBase 基础上增加线程安全的图片资源缓存。

### `DataURIResourceProviderProxy`
支持 Data URI（base64 编码）的代理，可直接从内嵌的 base64 数据解码图片和字体。

### `ImageDecodeStrategy`（枚举）
图片解码策略：
- `kLazyDecode`: 延迟解码，在光栅化时按需解码
- `kPreDecode`: 预解码，建造时立即解码

## 公共 API 函数

| 类 | 函数 | 说明 |
|----|------|------|
| `MultiFrameImageAsset` | `Make(sk_sp<SkData>, ...)` | 从数据创建多帧图片资源 |
| `MultiFrameImageAsset` | `Make(unique_ptr<SkCodec>, ...)` | 从已解码的 codec 创建 |
| `MultiFrameImageAsset` | `duration()` | 动画持续时间（毫秒） |
| `FileResourceProvider` | `Make(SkString base_dir, ...)` | 创建文件系统资源提供器 |
| `CachingResourceProvider` | `Make(sk_sp<ResourceProvider>)` | 创建缓存代理 |
| `DataURIResourceProviderProxy` | `Make(sk_sp<ResourceProvider>, ..., sk_sp<SkFontMgr>)` | 创建 Data URI 代理 |

## 内部实现细节

### ImageAsset 的两级 API
- `getFrame()` 为旧版 API（已弃用），只返回 SkImage
- `getFrameData()` 为新版 API，额外返回采样参数、变换矩阵和缩放策略
- 默认实现中 `getFrameData()` 调用 `getFrame()` 以保持向后兼容

### MultiFrameImageAsset 的大图处理
当图片面积超过 2048x2048 时，`generateFrame` 会缩放到合理尺寸，避免内存和性能问题。

## 使用示例

### 基本资源加载
```cpp
// 创建基于文件系统的资源提供器
auto rp = skresources::FileResourceProvider::Make(SkString("/path/to/assets"));

// 添加缓存层
auto cached_rp = skresources::CachingResourceProvider::Make(rp);

// 添加 Data URI 支持
auto uri_rp = skresources::DataURIResourceProviderProxy::Make(
    cached_rp, ImageDecodeStrategy::kPreDecode, fontMgr);
```

### 自定义 ResourceProvider
```cpp
class MyResourceProvider : public skresources::ResourceProvider {
    sk_sp<ImageAsset> loadImageAsset(const char path[],
                                      const char name[],
                                      const char id[]) const override {
        auto data = loadFromNetwork(path, name);
        return MultiFrameImageAsset::Make(std::move(data));
    }
};
```

### ImageAsset 帧数据
FrameData 结构体允许精细控制图片渲染：
- `image`: 实际的 SkImage 负载
- `sampling`: 重采样参数（如 SkFilterMode::kLinear）
- `matrix`: 额外的图片变换矩阵（在 AE 缩放规则之前应用）
- `scaling`: SizeFit 枚举控制图片到 AE 资产尺寸的缩放策略

### SizeFit 枚举说明
| 值 | 说明 | 对应 SkMatrix |
|----|------|---------------|
| kFill | 拉伸填充 | kFill_ScaleToFit |
| kStart | 保持比例，对齐起始 | kStart_ScaleToFit |
| kCenter | 保持比例，居中 | kCenter_ScaleToFit |
| kEnd | 保持比例，对齐末尾 | kEnd_ScaleToFit |
| kNone | 不缩放 | 无对应 |

## 依赖关系

- **SkData**: 二进制数据容器
- **SkImage**: 图片表示
- **SkCodec / SkAnimCodecPlayer**: 图片解码
- **SkFontMgr**: 字体管理（DataURI 代理需要）
- **SkMutex / SkTHash**: 线程安全和缓存容器

## 设计模式与设计决策

1. **策略模式**: ImageDecodeStrategy 允许在延迟解码和预解码之间切换，适应不同的内存/延迟需求。
2. **代理/装饰器模式**: ResourceProviderProxyBase、CachingResourceProvider、DataURIResourceProviderProxy 形成可叠加的代理链。
3. **接口隔离**: ImageAsset、ExternalTrackAsset、ResourceProvider 分别定义不同类型资源的接口。
4. **工厂方法**: 所有具体类通过静态 `Make` 方法创建，隐藏构造细节。

## 性能考量

- **图片缓存**: CachingResourceProvider 使用 mutex 保护的 THashMap 缓存已加载的图片资源
- **延迟解码**: kLazyDecode 策略延迟解码直到光栅化，减少前期内存占用
- **预解码**: kPreDecode 策略避免光栅化时的解码卡顿
- **大图缩放**: 超过 4M 像素的图片自动缩放，防止内存膨胀

## 相关文件

- `modules/skresources/src/SkResources.cpp` - 实现文件
- `modules/skresources/src/SkAnimCodecPlayer.h` - 动画编解码播放器
- `include/codec/SkCodec.h` - 图片编解码接口
- `include/core/SkImage.h` - SkImage 核心接口

## 使用注意事项

1. 调用 `MultiFrameImageAsset::Make` 前必须先通过 `SkCodec::Register()` 注册所需的图片解码器
2. `FileResourceProvider::Make` 会验证目录是否存在，不存在则返回 nullptr
3. `CachingResourceProvider` 使用 resource_id 作为缓存键，确保每个资源有唯一 ID
4. `DataURIResourceProviderProxy` 需要 SkFontMgr 才能处理 base64 编码的字体
5. ImageAsset 的 `getFrame()` 已弃用，新代码应实现 `getFrameData()`
