# CoreGraphics PDF 转 PNG 工具

> 源文件: `experimental/tools/coreGraphicsPdf2png.cpp`

## 概述

`coreGraphicsPdf2png.cpp` 是一个 macOS 专用的命令行工具，使用 Apple CoreGraphics 框架将 PDF 文件的第一页渲染为 PNG 图像。该工具不依赖 Skia 库本身，是一个独立的原生 macOS 应用程序。

## 架构位置

位于 `experimental/tools/` 目录，属于实验性辅助工具。它是一个独立的 C++ 程序，利用 macOS 的 ApplicationServices 框架完成 PDF 渲染，可用于生成参考图像或验证 Skia 的 PDF 渲染结果。

## 主要类与结构体

该文件没有定义类或结构体，所有逻辑包含在 `main` 函数中。

## 公共 API 函数

- **命令行接口**: `coreGraphicsPdf2png INPUT_PDF_FILE_PATH [OUTPUT_PNG_PATH]`
  - 若未指定输出路径或输出路径为 `"-"`，则输出到标准输出

## 内部实现细节

1. **PDF 加载**: 使用 `CGDataProviderCreateWithFilename` 和 `CGPDFDocumentCreateWithProvider` 打开 PDF
2. **页面获取**: 通过 `CGPDFDocumentGetPage` 获取第 1 页（常量 `PAGE = 1`）
3. **位图渲染**:
   - 获取 MediaBox 尺寸作为输出分辨率
   - 创建 RGBA 8-bit 位图上下文（`kCGBitmapByteOrder32Big | kCGImageAlphaPremultipliedLast`）
   - 使用白色（0xFF）预填充背景
   - 调用 `CGContextDrawPDFPage` 执行渲染
4. **PNG 输出**: 使用 `CGImageDestinationCreateWithDataConsumer` 创建 PNG 编码器，通过 lambda 回调写入文件

## 依赖关系

- macOS ApplicationServices 框架（CoreGraphics）
- C++ 标准库: `<cstdio>`, `<memory>`
- 编译命令: `c++ --std=c++11 coreGraphicsPdf2png.cpp -o coreGraphicsPdf2png -framework ApplicationServices`

## 设计模式与设计决策

- 使用 `ASSERT` 宏进行错误检查，失败时直接返回错误码 1
- 使用 `std::unique_ptr` 管理位图内存，确保异常安全
- lambda 表达式封装 `CGDataConsumer` 回调，简化文件写入逻辑
- 支持标准输出作为 PNG 输出目标，便于管道操作

## 性能考量

- 使用堆分配 (`new uint32_t[w * h]`) 存储位图数据，避免栈溢出
- 单页渲染模式，不支持批量处理

## 相关文件

- `experimental/tools/mskp_parser.py`: 同目录下的另一个实验性工具
- `src/pdf/`: Skia 自身的 PDF 后端实现
