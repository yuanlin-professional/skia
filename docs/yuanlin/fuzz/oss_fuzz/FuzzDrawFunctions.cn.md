# FuzzDrawFunctions (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzDrawFunctions.cpp

## 概述

测试 SkCanvas 的各种绘图函数,包括 drawRect, drawPath, drawText 等。通过随机参数组合发现绘图 API 的崩溃和渲染问题。

## 架构位置

测试 `include/core/SkCanvas.h` 中的所有绘图 API。

## 主要类与结构体

**LLVMFuzzerTestOneInput**: 最大 4000 字节
**fuzz_DrawFunctions**: 随机调用各种 draw* 方法

## 内部实现细节

测试覆盖:
- drawRect, drawRRect, drawCircle, drawOval
- drawPath, drawPoints, drawLine
- drawText, drawTextBlob
- drawImage, drawBitmap
- 使用随机的 SkPaint 参数

## 依赖关系

- `include/core/SkCanvas.h`: 绘图API
- `fuzz/FuzzCanvas.cpp`: 实现

## 设计模式与设计决策

**组合测试**: 随机组合绘图调用和参数,覆盖大量状态空间。

## 性能考量

4000 字节可生成数十到数百个绘图调用。

## 相关文件

- `fuzz/FuzzDrawFunctions.cpp`: 独立版本
- `src/core/SkCanvas.cpp`: Canvas 实现
