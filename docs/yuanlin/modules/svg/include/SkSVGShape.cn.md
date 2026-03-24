# SkSVGShape

> 源文件: modules/svg/include/SkSVGShape.h

## 概述

`SkSVGShape` 是所有 SVG 形状元素的基类,为 `<rect>`, `<circle>`, `<path>` 等形状提供通用的绘制逻辑。继承自 `SkSVGTransformableNode`。

## 主要功能

- 统一的形状绘制接口
- 处理填充和描边
- 管理形状特定的样式属性
- 提供路径转换
- 实现边界框计算

## 绘制流程

```
形状定义 → 转换为 SkPath
  → 应用填充规则
  → 执行填充绘制
  → 执行描边绘制
  → 应用标记(marker)
```

## 填充和描边

支持同时填充和描边,分别使用不同的 Paint 配置。填充规则: nonzero 或 evenodd。描边属性: width, linecap, linejoin, dash array 等。

## 派生类

- `SkSVGRect`: 矩形
- `SkSVGCircle`: 圆形
- `SkSVGEllipse`: 椭圆
- `SkSVGLine`: 线段
- `SkSVGPath`: 通用路径
- `SkSVGPoly`: 多边形/折线基类

## 虚函数接口

- `onDraw()`: 执行绘制(派生类实现)
- `onAsPath()`: 转换为路径(派生类实现)
- `onTransformableObjectBoundingBox()`: 计算边界框(派生类实现)

## 路径转换

所有形状都可以转换为 `SkPath`,统一了形状的内部表示,简化了路径操作和布尔运算。

## 相关文件

- `modules/svg/src/SkSVGShape.cpp`: 基类实现
- `SkSVGTransformableNode.h`: 可变换节点基类
- `include/core/SkPath.h`: Skia 路径

`SkSVGShape` 统一了所有形状元素的渲染逻辑,简化了具体形状类的实现,是 SVG 形状系统的核心抽象。
