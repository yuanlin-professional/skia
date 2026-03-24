# SkSVGFeComponentTransfer

> 源文件: modules/svg/include/SkSVGFeComponentTransfer.h

## 概述

`SkSVGFeComponentTransfer` 实现 SVG `<feComponentTransfer>` 滤镜原语,对图像的 RGBA 通道分别应用传递函数,实现复杂的色调映射。继承自 `SkSVGFe`。

## 主要功能

- 独立处理 R, G, B, A 四个通道
- 支持多种传递函数类型(identity, table, discrete, linear, gamma)
- 实现色调曲线和颜色查找表效果
- 转换为 Skia `SkColorFilter`

## 子元素

- `<feFuncR>`: 红色通道传递函数
- `<feFuncG>`: 绿色通道传递函数
- `<feFuncB>`: 蓝色通道传递函数
- `<feFuncA>`: Alpha 通道传递函数

## 传递函数类型

- `identity`: 不变换
- `table`: 查找表插值
- `discrete`: 离散值映射
- `linear`: 线性变换(y = slope * x + intercept)
- `gamma`: 伽马校正(y = amplitude * x^exponent + offset)

## 使用场景

用于实现色阶调整、颜色校正、对比度增强等高级图像处理效果。

## 相关文件

- `modules/svg/src/SkSVGFeComponentTransfer.cpp`: 实现
- `SkSVGFe.h`: 滤镜效果基类

该滤镜原语提供精细的通道级颜色控制,支持专业级图像处理效果。
