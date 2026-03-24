# SkSVGEllipse

> 源文件: modules/svg/include/SkSVGEllipse.h

## 概述

`SkSVGEllipse` 是 Skia SVG 模块中的椭圆元素类,负责 SVG `<ellipse>` 元素的解析、属性管理和渲染。该类继承自 `SkSVGShape`,实现了标准 SVG 规范中定义的椭圆功能,支持独立的 X 和 Y 半径。

## 主要功能

- SVG 椭圆元素属性的解析和存储(cx, cy, rx, ry)
- 将椭圆转换为 Skia 图形原语
- 支持 SVG 渲染上下文和样式继承
- 提供边界框计算和路径转换

## 核心属性

- `cx`: 椭圆中心 X 坐标(SkSVGLength)
- `cy`: 椭圆中心 Y 坐标(SkSVGLength)
- `rx`: X 方向半径(SkSVGLength)
- `ry`: Y 方向半径(SkSVGLength)

## API 函数

### 工厂方法
- `Make()`: 创建椭圆元素实例

### 属性访问
自动生成的 getter/setter 方法: `getCx()`, `setCx()`, `getCy()`, `setCy()`, `getRx()`, `setRx()`, `getRy()`, `setRy()`

### 渲染接口
- `parseAndSetAttribute()`: 解析属性字符串
- `onDraw()`: 使用 `SkCanvas::drawOval()` 执行渲染
- `onAsPath()`: 转换为包含椭圆的路径
- `onTransformableObjectBoundingBox()`: 计算边界矩形

## 设计特点

使用 SVG_ATTR 宏系统自动生成属性管理代码,确保类型安全。椭圆是圆形的广义形式,支持不同的 X 和 Y 半径,适用于更广泛的图形需求。

## 依赖关系

- `modules/svg/include/SkSVGShape.h`: 形状基类
- `modules/svg/include/SkSVGTypes.h`: SVG 类型系统
- `include/core/SkRect.h`: 椭圆边界矩形

## 相关文件

- 实现文件: `modules/svg/src/SkSVGEllipse.cpp`
- 基类: `modules/svg/include/SkSVGShape.h`
- 相关元素: `SkSVGCircle.h`(特殊情况: rx == ry)

该类是 Skia SVG 渲染管线的组成部分,提供椭圆形状的标准化渲染,是基础 SVG 形状元素之一。
