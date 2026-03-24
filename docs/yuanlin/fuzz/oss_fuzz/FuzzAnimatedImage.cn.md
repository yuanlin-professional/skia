# FuzzAnimatedImage.cpp - 动画图像解码模糊测试

> 源文件: `fuzz/oss_fuzz/FuzzAnimatedImage.cpp`

## 概述

本文件实现了一个针对 Skia 动画图像（Animated Image）解码和渲染管线的模糊测试。它通过 `SkAndroidCodec` 和 `SkAnimatedImage` API 测试动画图像（如 GIF、WebP 动画）的解码流程，包括创建编解码器、解码帧、推进到下一帧以及将帧绘制到 Surface 上。该测试用于发现动画图像处理中的内存安全问题和逻辑错误。

## 架构位置

该文件位于 `fuzz/oss_fuzz/` 目录下，属于 Skia 的 OSS-Fuzz 安全测试集。它覆盖了 Skia 动画图像处理的完整管线：从原始字节流到 SkAndroidCodec 解码、SkAnimatedImage 帧管理、再到 SkCanvas 渲染输出。

## 主要类与结构体

本文件使用的关键类型：

- **`SkAndroidCodec`**: Android 平台优化的图像编解码器，支持采样缩放
- **`SkAnimatedImage`**: 动画图像封装，管理帧序列和播放状态
- **`SkSurface`**: 渲染目标 Surface（使用 Raster 后端）
- **`SkCanvas`**: 2D 绘图画布
- **`SkMemoryStream`**: 内存流，将字节数组包装为流接口

## 公共 API 函数

- **`FuzzAnimatedImage(const uint8_t *data, size_t size)`**: 核心模糊测试函数，接受原始字节尝试作为动画图像解码和渲染。成功返回 `true`，失败返回 `false`
- **`LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)`**: LibFuzzer 入口点，输入限制 10240 字节

## 内部实现细节

### 测试流程

1. 将输入字节包装为 `SkMemoryStream`
2. 通过 `SkAndroidCodec::MakeFromStream()` 尝试创建编解码器
3. 通过 `SkAnimatedImage::Make()` 创建动画图像对象
4. 创建 128x128 的 N32 Premul Raster Surface
5. 循环解码和绘制帧，直到动画结束或达到 100 帧上限

### 安全限制

- **输入大小**: 最大 10240 字节（10KB），足以覆盖常见的小型动画格式
- **帧数限制**: 最多处理 100 帧（`escape < 100`），防止恶意构造的无限循环动画消耗过多资源
- **内存约束**: 在内存受限的模糊测试环境中，Surface 创建可能失败并安全返回

## 依赖关系

- **`include/android/SkAnimatedImage.h`**: 动画图像 API
- **`include/codec/SkAndroidCodec.h`**: Android 编解码器
- **`include/core/SkCanvas.h`**: 画布 API
- **`include/core/SkStream.h`**: 流 API
- **`include/core/SkSurface.h`**: Surface API

## 设计模式与设计决策

- **完整管线覆盖**: 测试从解码到渲染的完整路径，而非仅测试解码器
- **逃逸计数器**: 使用 `escape` 变量限制帧数，是模糊测试中常见的资源控制模式
- **优雅降级**: 每个步骤都检查返回值，在任何阶段失败时安全退出
- **固定 Surface 尺寸**: 使用 128x128 的小尺寸 Surface，减少内存占用同时仍能触发渲染路径

## 性能考量

- 128x128 的 Surface 尺寸最小化了像素操作的开销
- 100 帧上限防止长动画序列消耗过多 CPU 时间
- 10KB 输入限制确保解码操作在合理时间内完成
- `SkMemoryStream::MakeDirect` 使用零拷贝方式包装输入数据，无额外内存分配
- 使用 N32 Premul 格式的 Surface 是最常用的配置，避免了格式转换开销
- `decodeNextFrame()` 在每帧调用时增量解码，内存占用与单帧大小成正比

### 覆盖的图像格式

虽然测试名称为 "AnimatedImage"，但实际上覆盖了 SkAndroidCodec 支持的所有动画格式：
- GIF 动画
- WebP 动画
- APNG（动画 PNG）

## 相关文件

- `include/android/SkAnimatedImage.h` - SkAnimatedImage 公共头文件
- `include/codec/SkAndroidCodec.h` - SkAndroidCodec 公共头文件
- `fuzz/oss_fuzz/FuzzAndroidCodec.cpp` - Android 编解码器的独立模糊测试
- `src/android/SkAnimatedImage.cpp` - 动画图像实现
