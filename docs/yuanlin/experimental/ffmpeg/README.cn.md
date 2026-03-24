# ffmpeg - FFmpeg 视频编解码集成

## 概述

`experimental/ffmpeg/` 提供了基于 FFmpeg 库的视频编码和解码封装，允许将 Skia
的绘制内容录制为视频文件，或从视频文件中提取帧进行处理。该模块封装了 FFmpeg
复杂的底层 API，提供了简洁的 Skia 风格接口。

## 目录结构

```
ffmpeg/
├── BUILD.gn               # GN 构建配置
├── SkVideoEncoder.h       # 视频编码器头文件
├── SkVideoEncoder.cpp     # 视频编码器实现
├── SkVideoDecoder.h       # 视频解码器头文件
└── SkVideoDecoder.cpp     # 视频解码器实现
```

## 关键文件

### SkVideoEncoder
视频编码器，支持将 Skia 绘制帧序列编码为视频：
- `beginRecording(size, fps)` - 开始录制
- `addFrame(pixmap)` / `beginFrame()`+`endFrame()` - 添加帧
- `endRecording()` - 结束录制并返回视频数据

### SkVideoDecoder
视频解码器，支持从视频文件中提取帧。

## 依赖关系

- FFmpeg 外部库:
  - `libavcodec` - 编解码核心
  - `libavformat` - 容器格式处理
  - `libavutil` - 工具函数
  - `libswscale` - 图像格式转换
- Skia 核心库（`SkImage`、`SkSurface`、`SkCanvas`、`SkStream`）

## 相关文档与参考

- FFmpeg 官方文档: https://ffmpeg.org/documentation.html
- Skia SkSurface API: `include/core/SkSurface.h`
