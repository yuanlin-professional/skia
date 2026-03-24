# SkSVGGradient

> 源文件: modules/svg/include/SkSVGGradient.h

## 概述

`SkSVGGradient` 是 SVG 渐变元素的基类,为线性渐变(`<linearGradient>`)和径向渐变(`<radialGradient>`)提供共同功能。

## 主要功能

- 管理渐变停止点(`<stop>`)
- 处理渐变变换
- 支持渐变单位系统
- 实现扩展模式(pad, repeat, reflect)
- 转换为 Skia `SkShader`

## 共同属性

- `gradientUnits`: 坐标系统(objectBoundingBox 或 userSpaceOnUse)
- `gradientTransform`: 应用于渐变的变换
- `spreadMethod`: 扩展模式(pad, repeat, reflect)
- `xlink:href`: 引用另一个渐变继承属性

## 派生类

- `SkSVGLinearGradient`: 线性渐变
- `SkSVGRadialGradient`: 径向渐变

## 渐变停止点

通过 `<stop>` 子元素定义颜色停止点,包含位置(offset)和颜色(stop-color)。

## 扩展模式

- `pad`: 使用边界颜色填充超出区域
- `repeat`: 重复渐变模式
- `reflect`: 镜像重复渐变模式

## 相关文件

- `modules/svg/src/SkSVGGradient.cpp`: 基类实现
- `SkSVGLinearGradient.h`, `SkSVGRadialGradient.h`: 派生类
- `SkSVGStop.h`: 停止点元素

该基类统一了渐变的通用功能,简化了具体渐变类型的实现。
