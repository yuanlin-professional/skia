# Canvas 模糊测试

> 源文件: `fuzz/FuzzCanvas.cpp`

## 概述

此文件定义了多个 Canvas 相关的模糊测试目标，使用随机数据驱动 SkCanvas 的绘图操作来发现渲染引擎中的潜在缺陷。覆盖了 Null Canvas、光栅 Canvas、GPU Canvas、PDF Canvas、SVG Canvas 以及图像滤镜等多种目标。

## 架构位置

位于模糊测试框架 (`fuzz/`) 中，使用 `DEF_FUZZ` 宏注册模糊测试目标。

## 主要类与结构体

无自定义结构体。使用 `Fuzz` 类作为随机数据源。

## 公共 API 函数

### 模糊测试目标（通过 DEF_FUZZ 宏注册）
- `NullCanvas` - 在空 canvas 上执行随机绘图
- `RasterN32Canvas` - 在 N32 光栅 surface 上绘图
- `RasterN32CanvasViaSerialization` - 录制、序列化、反序列化后回放
- `ImageFilter` / `SerializedImageFilter` - 模糊测试图像滤镜
- `MockGPUCanvas` - Mock GPU 上下文上绘图
- `NativeGLCanvas` - 原生 OpenGL 上下文上绘图
- `PDFCanvas` - PDF 文档 canvas
- `SVGCanvas` - SVG canvas
- `_DumpCanvas` - 调试用，输出 canvas 操作的 JSON

## 内部实现细节

- Canvas 大小固定为 128x160
- `SerializedImageFilter` 对序列化数据进行随机位翻转，模拟损坏数据
- GPU 测试通过 `GrContextFactory` 创建上下文
- `_DumpCanvas` 使用 `DebugCanvas` 和 `SkJSONWriter` 输出操作日志

## 依赖关系

- `fuzz/Fuzz.h`, `fuzz/FuzzCanvasHelpers.h`, `fuzz/FuzzCommon.h`
- Skia 核心：`SkCanvas`, `SkSurface`, `SkPicture`
- PDF：`SkPDFDocument`，SVG：`SkSVGCanvas`
- GPU：`GrDirectContext`, `GrContextFactory`

## 设计模式与设计决策

- **多目标覆盖**：每种 Canvas 类型独立注册为模糊测试目标
- **序列化往返测试**：通过序列化-位翻转-反序列化测试数据容错性

## 性能考量

Canvas 大小刻意保持较小 (128x160) 以在模糊测试中获得更高的吞吐量。

## 相关文件

- `fuzz/FuzzCanvasHelpers.h` - Canvas 模糊测试辅助函数
- `fuzz/FuzzCommon.h` - 通用模糊测试工具
