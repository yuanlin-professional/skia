# spiralshader.js - 螺旋着色器效果

> 源文件: `demos.skia.org/demos/textedit/spiralshader.js`

## 概述

定义了一个 SkSL 运行时着色器效果,生成基于极坐标的双色螺旋渐变图案,用于文本编辑器演示中的装饰性着色器效果。

## 架构位置

Skia Web 文本编辑器演示的辅助模块。

## 主要类与结构体

无类,仅一个工厂函数。

## 公共 API 函数

- **`MakeSpiralShaderEffect(CanvasKit)`**: 编译并返回 RuntimeEffect 对象

## 内部实现细节

SkSL 着色器接受四个 uniform: `rad_scale`(半径缩放)、`in_center`(中心点)、`in_colors0` 和 `in_colors1`(两种颜色)。通过极坐标变换和角度/半径混合产生螺旋效果。

## 依赖关系

- CanvasKit.RuntimeEffect.Make

## 设计模式与设计决策

使用 SkSL 运行时着色器在 GPU 上实时生成图案,而非预计算纹理。

## 性能考量

着色器在 GPU 上执行,逐像素计算开销低。

## 相关文件

- `demos.skia.org/demos/textedit/textapi_utils.js`
