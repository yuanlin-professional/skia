# skresources/include - 资源管理模块公共头文件

## 概述

`modules/skresources/include/` 目录仅包含一个头文件 `SkResources.h`,它定义了资源管理模块的全部公共 API。该文件集中定义了 `ResourceProvider`、`ImageAsset`、`ExternalTrackAsset` 等核心接口以及多个具体实现类。

所有接口都定义在 `skresources` 命名空间中,使用 `SkRefCnt` 引用计数进行内存管理,通过 `sk_sp` 智能指针传递对象所有权。

## 关键类与函数

| 类 | 说明 |
|----|------|
| `ResourceProvider` | 资源加载的核心接口,定义 load/loadImageAsset/loadAudioAsset/loadFont/loadTypeface |
| `ImageAsset` | 图像资源代理,支持静态和动画图像的帧获取 |
| `MultiFrameImageAsset` | 基于 SkCodec 的多帧图像实现 |
| `ExternalTrackAsset` | 音频轨道的 seek 回调接口 |
| `FileResourceProvider` | 本地文件系统资源加载器 |
| `CachingResourceProvider` | 图像资产缓存代理 |
| `DataURIResourceProviderProxy` | data URI 格式资源解析代理 |

## 相关文档与参考

- 资源管理模块概述: `modules/skresources/README.md`
- 主要使用者: `modules/skottie/`, `modules/svg/`
