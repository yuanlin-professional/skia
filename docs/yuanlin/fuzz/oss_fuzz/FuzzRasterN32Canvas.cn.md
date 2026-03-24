# FuzzRasterN32Canvas (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzRasterN32Canvas.cpp

## 概述

测试基于 CPU 的光栅化 Canvas,使用 N32(RGBA/BGRA 32位)色彩格式。这是 Skia 的软件渲染路径,不依赖 GPU。

## 架构位置

测试 CPU 软件渲染器的绘图 API。

## 主要类与结构体

**LLVMFuzzerTestOneInput**:
- 最大 4000 字节
- 使用可移植字体确保一致性

**fuzz_RasterN32Canvas**:
- 创建内存中的位图 Canvas
- 执行随机绘图操作
- 验证输出的像素数据

## 内部实现细节

N32 格式:
- 每像素 32 位
- 平台相关的字节序(RGBA 或 BGRA)
- 最常用的光栅化格式

测试覆盖:
- 各种绘图primitive
- 混合模式和图像滤镜
- 抗锯齿和抖动
- 裁剪和变换

## 依赖关系

- `include/core/SkSurface.h`: Surface 创建
- `src/core/SkBitmapDevice.cpp`: 位图设备实现

## 设计模式与设计决策

**软件渲染测试**: 独立于 GPU 驱动,更容易复现问题。

## 性能考量

CPU 渲染比 GPU 慢,但对于 fuzzing 的简单操作足够快。

## 相关文件

- `src/core/SkRasterPipeline.cpp`: 光栅化管线
- `tests/CanvasTest.cpp`: Canvas 单元测试

该 fuzzer 自 2018 年运行,是最常用的 Canvas fuzzer之一,发现了大量 CPU 渲染路径的问题。
