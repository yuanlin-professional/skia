# client_utils/android - Android 客户端工具

## 概述

`android/` 包含专为 Android 平台设计的 Skia 客户端辅助工具，主要提供
图像区域解码和流缓冲功能。

## 目录结构

```
android/
├── BitmapRegionDecoder.cpp      # 区域解码器实现
├── BitmapRegionDecoder.h        # 公共接口
├── BitmapRegionDecoderPriv.h    # 内部实现细节
├── BRDAllocator.h               # 自定义内存分配器
├── FrontBufferedStream.cpp      # 前端缓冲流实现
└── FrontBufferedStream.h        # 前端缓冲流接口
```

## 关键文件

- **BitmapRegionDecoder**: 支持解码图像的任意矩形区域，避免加载整张图片
  到内存。支持子采样（downsampling）以降低内存占用。
- **BRDAllocator**: 区域解码器使用的自定义像素分配器接口
- **FrontBufferedStream**: 对 SkStream 进行缓冲封装，支持对流前部数据的
  随机访问（seek），而不要求底层流支持 seek

## 依赖关系

- Skia SkCodec 框架
- Skia SkStream API

## 相关文档与参考

- Skia 编解码器: `src/codec/`
- Android BitmapRegionDecoder API
