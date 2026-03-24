# 绘图函数模糊测试

> 源文件: `fuzz/FuzzDrawFunctions.cpp`

## 概述

此文件对 Skia 的各种基本绘图函数进行模糊测试，包括文本绘制、矩形、圆形、直线、路径、图像和纯色填充。通过随机化绘图参数发现渲染引擎中的边界情况和潜在缺陷。

## 架构位置

位于模糊测试框架 (`fuzz/`) 中，通过 `DEF_FUZZ(DrawFunctions, ...)` 注册。

## 主要类与结构体

无自定义结构体。

## 公共 API 函数

- `DEF_FUZZ(DrawFunctions, fuzz)` - 随机选择并执行一种绘图操作

### 内部绘图函数
- `fuzz_drawText` - 使用随机字体和位置绘制文本
- `fuzz_drawCircle` - 绘制随机圆形
- `fuzz_drawLine` - 绘制随机线段
- `fuzz_drawRect` - 绘制随机矩形并测试裁剪
- `fuzz_drawPath` - 构建随机路径（moveTo/lineTo/quadTo/conicTo/cubicTo/arcTo）并绘制
- `fuzz_drawImage` - 随机绘制图像或图像区域
- `fuzz_drawPaint` - 绘制随机画笔

### 辅助函数
- `init_string` - 生成随机可打印 ASCII 字符串
- `init_paint` - 创建随机 SkPaint
- `init_bitmap` - 创建随机 SkBitmap
- `init_surface` - 创建随机大小的 Surface

## 内部实现细节

- Surface 大小限制为 1-250 像素
- 位图大小固定为 24x24
- 路径操作数量限制为 0-10 次
- 涵盖所有 SkBlendMode、SkPaint::Cap、SkPaint::Join 和 Style 的变体
- 同时测试 drawImage 和 drawImageRect 两种图像绘制方式
- 路径绘制后还测试 clipPath 功能

## 依赖关系

- `fuzz/Fuzz.h` - 模糊测试框架
- Skia 核心绘图 API

## 设计模式与设计决策

**随机选择+随机参数**：先随机选择绘图类型，再对该类型的所有参数进行随机化，最大化代码路径覆盖。

## 性能考量

Surface 和位图大小刻意保持较小，提高模糊测试的执行速度。

## 相关文件

- `fuzz/FuzzCanvas.cpp` - Canvas 级别的模糊测试
