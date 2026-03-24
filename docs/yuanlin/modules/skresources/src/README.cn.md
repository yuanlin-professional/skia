# skresources/src - 资源管理模块实现代码

## 概述

`modules/skresources/src/` 目录包含资源管理模块的实现代码。主要包含两个功能区域:资源提供者的各种实现 (`SkResources.cpp`) 和动画图像编解码播放器 (`SkAnimCodecPlayer`)。

`SkResources.cpp` 实现了 `FileResourceProvider`(读取本地文件)、`CachingResourceProvider`(线程安全的图像缓存)、`DataURIResourceProviderProxy`(解析 data: URI 和 base64 编码)等资源提供者。

`SkAnimCodecPlayer` 封装了 `SkCodec`,根据时间码选择和解码对应帧,支持多帧动画图像(如 GIF、WebP 动画)的播放。

## 目录结构

```
src/
+-- BUILD.bazel             # Bazel 构建配置
+-- SkResources.cpp         # ResourceProvider 各实现类
+-- SkAnimCodecPlayer.h     # 动画图像播放器头文件
+-- SkAnimCodecPlayer.cpp   # 动画图像播放器实现
```

## 关键类与函数

| 文件 | 核心功能 |
|------|---------|
| `SkResources.cpp` | FileResourceProvider 文件读取、CachingResourceProvider 缓存逻辑、DataURI 解析 |
| `SkAnimCodecPlayer.cpp` | 基于 SkCodec 的多帧图像解码和帧选择 |

## 相关文档与参考

- 公共 API: `modules/skresources/include/SkResources.h`
- SkCodec API: `include/codec/SkCodec.h`
