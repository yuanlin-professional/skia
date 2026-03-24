# skresources - 资源管理模块

## 概述

`modules/skresources` 是 Skia 的外部资源管理模块,为富内容模块(如 Lottie 动画的 skottie、SVG 渲染等)提供统一的资源加载抽象层。该模块的核心目标是将图片、字体、音频等外部资源的加载延迟到嵌入客户端,从而实现资源加载策略的灵活定制。

模块的核心是 `ResourceProvider` 抽象接口,它定义了加载各类资源的虚方法,包括通用数据 (`load`)、图像资源 (`loadImageAsset`)、音频轨道 (`loadAudioAsset`)、字体数据 (`loadFont`) 和字体对象 (`loadTypeface`)。客户端通过实现此接口来控制资源的实际获取方式(本地文件系统、网络、内存缓存等)。

`ImageAsset` 接口是图像资源的代理抽象,支持静态图和多帧动画图像。它通过 `getFrameData()` 方法返回指定时间码对应的图像帧数据,包括 `SkImage` 载荷、采样参数、变换矩阵和缩放策略。`MultiFrameImageAsset` 是内置的动画图像资产实现,基于 `SkAnimCodecPlayer` 处理多帧图像编解码。

模块还提供了几个实用的 `ResourceProvider` 实现:`FileResourceProvider` 从本地目录加载文件,`CachingResourceProvider` 为图像资产添加缓存层,`DataURIResourceProviderProxy` 支持解析 data URI 格式的内嵌资源。

## 架构图

```
+-----------------------------+
|       客户端应用             |
+-----------------------------+
              |
              v
+-----------------------------+
|    ResourceProvider (接口)   |
|  - load()                   |
|  - loadImageAsset()         |
|  - loadAudioAsset()         |
|  - loadFont() / loadTypeface()|
+-----------------------------+
      |         |          |
      v         v          v
+----------+ +--------+ +-----------+
|FileResource| |Caching | |DataURI   |
|Provider    | |Resource| |Resource  |
|(本地文件)  | |Provider| |Provider  |
+----------+ |(缓存代理)| |(base64)  |
              +--------+ +-----------+
              |
              v
+-----------------------------+
|   ResourceProviderProxyBase |
|   (代理基类)                |
+-----------------------------+

+-----------------------------+
|     ImageAsset (接口)        |
|  - isMultiFrame()           |
|  - getFrame(float t)        |
|  - getFrameData(float t)    |
+-----------------------------+
              |
              v
+-----------------------------+
|   MultiFrameImageAsset      |
|   (基于 SkAnimCodecPlayer)  |
+-----------------------------+

+-----------------------------+
|   ExternalTrackAsset (接口)  |
|   - seek(float t)           |
+-----------------------------+
```

## 目录结构

```
modules/skresources/
+-- BUILD.gn                # GN 构建配置
+-- BUILD.bazel             # Bazel 构建配置
+-- skresources.gni         # GNI 源文件列表
+-- include/
|   +-- BUILD.bazel         # 头文件 Bazel 配置
|   +-- SkResources.h       # 所有公共接口定义
+-- src/
    +-- BUILD.bazel         # 源文件 Bazel 配置
    +-- SkResources.cpp     # ResourceProvider 各实现类
    +-- SkAnimCodecPlayer.h # 动画编解码播放器头文件
    +-- SkAnimCodecPlayer.cpp # 动画编解码播放器实现
```

## 关键类与函数

| 类/函数 | 文件 | 说明 |
|---------|------|------|
| `ResourceProvider` | `include/SkResources.h` | 资源加载核心抽象接口,所有方法默认返回 nullptr |
| `ImageAsset` | `include/SkResources.h` | 图像资源代理接口,支持静态和多帧动画 |
| `ImageAsset::FrameData` | `include/SkResources.h` | 帧数据结构体 (SkImage + 采样 + 矩阵 + 缩放策略) |
| `ImageAsset::SizeFit` | `include/SkResources.h` | 缩放策略枚举 (Fill/Start/Center/End/None) |
| `MultiFrameImageAsset` | `include/SkResources.h` | 基于 SkCodec 的多帧图像资产实现 |
| `ExternalTrackAsset` | `include/SkResources.h` | 外部音频轨道接口 (seek 回调) |
| `FileResourceProvider` | `include/SkResources.h` | 从本地文件目录加载资源 |
| `CachingResourceProvider` | `include/SkResources.h` | 缓存代理,对图像资产进行哈希缓存 |
| `DataURIResourceProviderProxy` | `include/SkResources.h` | 支持解析 data:// URI 和 base64 编码资源 |
| `ResourceProviderProxyBase` | `include/SkResources.h` | 代理模式基类,转发所有调用到内部 Provider |
| `ImageDecodeStrategy` | `include/SkResources.h` | 图像解码策略 (kLazyDecode / kPreDecode) |
| `SkAnimCodecPlayer` | `src/SkAnimCodecPlayer.h` | 多帧图像编解码播放器 |

## 依赖关系

- **Skia Core**: `SkData`, `SkImage`, `SkCodec`, `SkMatrix`, `SkRefCnt`, `SkString`, `SkTypeface`
- **Skia Core (内部)**: `SkTHash`, `SkMutex` 用于缓存实现
- **被依赖**: `modules/skottie` (Lottie 动画), `modules/svg` (SVG 渲染)

## 设计模式分析

1. **策略模式 (Strategy)**: `ResourceProvider` 作为策略接口,允许客户端自定义资源加载逻辑。不同的实现类代表不同的加载策略。

2. **代理模式 (Proxy)**: `ResourceProviderProxyBase` 和 `CachingResourceProvider` 采用代理模式,在不改变接口的前提下添加缓存或 data URI 解析等增强功能。

3. **工厂方法 (Factory Method)**: 各实现类使用静态 `Make()` 方法创建实例,隐藏构造细节。

4. **空对象模式 (Null Object)**: `ResourceProvider` 的所有方法默认返回 nullptr,客户端只需重写需要的方法。

## 数据流

```
客户端请求资源
       |
       v
ResourceProvider::loadImageAsset(path, name, id)
       |
       +-- FileResourceProvider: 读取 path/name 文件
       |
       +-- DataURIResourceProviderProxy: 解析 data:URI
       |         |
       |         v
       |   base64 解码 --> SkData --> MultiFrameImageAsset
       |
       +-- CachingResourceProvider: 查缓存 / 转发
       |
       v
ImageAsset::getFrameData(t)
       |
       v
FrameData { SkImage, sampling, matrix, scaling }
       |
       v
渲染模块 (skottie / svg) 使用 SkImage 绘制
```

## 相关文档与参考

- skottie 模块 (主要使用者): `modules/skottie/`
- SVG 模块 (资源使用者): `modules/svg/`
- Skia SkCodec API: `include/codec/SkCodec.h`
- Skia SkImage API: `include/core/SkImage.h`
