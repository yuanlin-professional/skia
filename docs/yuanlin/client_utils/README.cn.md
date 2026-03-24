# client_utils/ - 客户端工具库

## 概述

`client_utils/` 包含供 Skia 客户端（如 Android 系统）使用的工具类和辅助
功能。这些工具提供了特定平台上常用的图像处理功能，如 Android 的区域解码和
前端缓冲流。

## 目录结构

```
client_utils/
└── android/                     # Android 客户端工具
    ├── BitmapRegionDecoder.cpp  # 区域解码器实现
    ├── BitmapRegionDecoder.h    # 区域解码器头文件
    ├── BitmapRegionDecoderPriv.h # 区域解码器内部头文件
    ├── BRDAllocator.h           # 区域解码器分配器
    ├── FrontBufferedStream.cpp  # 前端缓冲流实现
    └── FrontBufferedStream.h    # 前端缓冲流头文件
```

## 关键文件

### BitmapRegionDecoder
Android 平台的图像区域解码器，允许只解码图像的一部分区域，常用于大图片的
局部显示场景（如地图、高分辨率照片浏览）。

### FrontBufferedStream
前端缓冲流封装，对输入流的前部数据进行缓冲，支持 `seek()` 回退到已缓冲
区域。这对于图像格式检测非常有用 -- 先读取头部判断格式，然后回退让解码器
从头开始处理。

## 依赖关系

- Skia 编解码器框架（`src/codec/`）
- Skia 流 API（`include/core/SkStream.h`）

## 相关文档与参考

- Android 图像处理: `include/android/`
- Skia 编解码器: `src/codec/`
