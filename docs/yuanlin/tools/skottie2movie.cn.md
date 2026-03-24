# skottie2movie - Skottie 动画转 MP4 工具

> 源文件: `tools/skottie2movie.cpp`

## 概述

`skottie2movie` 将 Skottie (Lottie) JSON 动画文件转换为 MP4 视频文件。支持 CPU 和 GPU (OpenGL) 渲染模式,可自定义帧率和输出尺寸。使用 FFmpeg (通过 SkVideoEncoder) 进行视频编码。

## 架构位置

属于 Skia 的 Skottie 动画工具链,用于动画预览和视频导出。

## 主要类与结构体

- **`AsyncRec`**: 异步像素读取的上下文(info + encoder)

## 公共 API 函数

- **`main()`**: 加载动画、配置渲染、逐帧编码
- **`produce_frame()`**: 渲染单帧到 SkSurface

## 内部实现细节

- 支持 GPU 异步像素读取(`asyncRescaleAndReadPixels`)
- CPU 模式使用 `peekPixels` 直接访问像素
- 支持 `--loop` 模式用于性能分析
- 自动计算帧率缩放(`animation->fps() / target_fps`)
- 平台特定字体管理器(CoreText/Fontconfig/Empty)
- 编解码器通过 `CodecUtils::RegisterAllAvailable()` 注册

## 依赖关系

- `experimental/ffmpeg/SkVideoEncoder.h` - FFmpeg 视频编码
- `modules/skottie/include/Skottie.h` - Skottie 动画引擎
- `modules/skresources/include/SkResources.h` - 资源加载
- Ganesh GPU 后端(可选)

## 设计模式与设计决策

- **双模式渲染**: CPU 和 GPU 路径根据 `--gpu` 标志选择
- **异步读取**: GPU 模式使用异步读取避免 GPU/CPU 同步开销

## 性能考量

- GPU 渲染 + 异步读取可显著提升编码速度
- `--loop` 模式报告实际编码帧率用于性能调优

## 相关文件

- `modules/skottie/` - Skottie 动画模块
- `experimental/ffmpeg/` - FFmpeg 集成
