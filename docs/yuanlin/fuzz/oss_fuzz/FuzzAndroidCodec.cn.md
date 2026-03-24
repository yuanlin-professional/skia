# FuzzAndroidCodec.cpp - Android 编解码器模糊测试

> 源文件: `fuzz/oss_fuzz/FuzzAndroidCodec.cpp`

## 概述

本文件实现了针对 `SkAndroidCodec` 图像编解码器的模糊测试。`SkAndroidCodec` 是 Skia 为 Android 平台提供的增强编解码器接口，支持采样缩放解码。该测试覆盖了图像解码（含采样）、gainmap（增益图）提取和解码后渲染到 Surface 的完整流程，用于发现 Android 图像处理管线中的安全漏洞。

## 架构位置

该文件位于 `fuzz/oss_fuzz/` 目录下，测试了 Skia 面向 Android 的图像编解码器子系统。`SkAndroidCodec` 封装了 `SkCodec` 并添加了 Android 特有的功能（如采样缩放和 gainmap 支持），这些功能在 Android Framework 的 `BitmapFactory` 和 `BitmapRegionDecoder` 中被广泛使用。

## 主要类与结构体

- **`SkAndroidCodec`**: Android 平台优化的编解码器
- **`SkAndroidCodec::AndroidOptions`**: Android 特有的解码选项（含 `fSampleSize`）
- **`SkBitmap`**: 像素缓冲区
- **`SkGainmapInfo`**: HDR gainmap 元数据信息
- **`SkSurface` / `SkCanvas`**: 渲染目标和画布

## 公共 API 函数

- **`FuzzAndroidCodec(const uint8_t *fuzzData, size_t fuzzSize, uint8_t sampleSize)`**: 核心模糊测试函数，接受图像数据和采样大小
- **`LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)`**: LibFuzzer 入口点，输入限制 10240 字节

## 内部实现细节

### 测试流程

1. 从输入创建 `SkAndroidCodec`
2. 使用指定的 `sampleSize` 获取采样后的目标尺寸
3. 分配 N32 Premul 格式的 `SkBitmap`
4. 调用 `getAndroidPixels()` 执行采样解码
5. 尝试提取 gainmap 信息（`getAndroidGainmap()`）
6. 将解码后的图像渲染到 Raster Surface

### 输入参数分离

LibFuzzer 入口点中，前几个字节通过 `Fuzz` 对象提取 `sampleSize`（范围 1-64），剩余字节作为图像数据。这种设计允许模糊测试引擎自动探索不同的采样参数。

### 错误容忍

解码结果中 `kSuccess`、`kIncompleteInput`（截断图像）和 `kErrorInInput`（包含错误但仍可部分解码）都被视为可接受的结果，只有其他错误才会中止测试。

### Gainmap 测试

对 `getAndroidGainmap()` 的返回值进行基本验证：
- 检查 `fDisplayRatioSdr` 是否为有限值
- 检查 gainmap 图像流大小是否在合理范围内（< 100MB）

## 依赖关系

- **`include/codec/SkAndroidCodec.h`**: Android 编解码器
- **`include/core/SkBitmap.h`**: 像素缓冲区
- **`include/core/SkCanvas.h` / `SkSurface.h`**: 渲染 API
- **`include/core/SkStream.h`**: 流 API
- **`include/private/SkGainmapInfo.h`**: Gainmap 信息（私有 API）
- **`fuzz/Fuzz.h`**: 模糊测试工具

## 设计模式与设计决策

- **参数化模糊测试**: 将 `sampleSize` 从输入流中提取，让模糊测试引擎能够探索不同的采样参数空间
- **完整管线覆盖**: 从解码到渲染，覆盖了真实使用场景的完整路径
- **Gainmap 覆盖**: 包含 HDR gainmap 功能的测试，覆盖 Android 14+ 的 Ultra HDR 图像支持
- **宽松的错误接受**: 接受部分解码成功的结果，因为不完整的图像在真实场景中很常见

## 性能考量

- `sampleSize` 范围 1-64 允许测试大范围的缩放比例
- 10KB 输入限制平衡了图像格式头部解析和像素数据的覆盖
- 采样解码减少了实际处理的像素量，加速了测试执行
- 内存受限环境中 `tryAllocPixels` 和 Surface 创建可能失败并安全返回

### 支持的图像格式

SkAndroidCodec 支持以下格式的解码：
- JPEG（包含 EXIF 方向处理）
- PNG（包含 APNG 检测）
- WebP（包含动画和有损/无损模式）
- GIF
- HEIF/AVIF（如果编译时启用）

## 相关文件

- `include/codec/SkAndroidCodec.h` - SkAndroidCodec 公共头文件
- `src/codec/SkAndroidCodec.cpp` - SkAndroidCodec 实现
- `fuzz/oss_fuzz/FuzzAnimatedImage.cpp` - 动画图像模糊测试
- `client_utils/android/BitmapRegionDecoderPriv.h` - Android 区域解码器工具
