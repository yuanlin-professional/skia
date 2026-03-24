# SkSVGNode

> 源文件: modules/svg/include/SkSVGNode.h

## 概述

`SkSVGNode` 是所有 SVG 元素的抽象基类,定义了 SVG DOM 树的核心接口和属性系统。继承自 `SkRefCnt`,使用智能指针管理生命周期。

## 主要功能

- 定义 SVG 元素的基本接口
- 管理呈现属性(fill, stroke, opacity 等)
- 提供属性解析和设置机制
- 支持渲染、路径转换和边界计算
- 实现属性继承系统

## 核心接口

```cpp
virtual void appendChild(sk_sp<SkSVGNode>);
void render(const SkSVGRenderContext&) const;
bool asPaint(const SkSVGRenderContext&, SkPaint*) const;
SkPath asPath(const SkSVGRenderContext&) const;
SkRect objectBoundingBox(const SkSVGRenderContext&) const;
void setAttribute(SkSVGAttribute, const SkSVGValue&);
bool parseAndSetAttribute(const char*, const char*);
```

## 呈现属性系统

使用 `SVG_PRES_ATTR` 宏定义呈现属性,自动生成 getter/setter,支持继承(inherited)和非继承属性,实现 CSS 样式继承模型。

### 继承属性
Fill, Stroke, FontFamily, FontSize, StrokeWidth, Opacity 等会从父元素继承。

### 非继承属性
ClipPath, Mask, Filter, Display 等不继承,仅应用于当前元素。

## 属性宏系统

**SVG_PRES_ATTR**: 定义呈现属性
**SVG_ATTR**: 定义普通属性(在派生类中)
**SVG_OPTIONAL_ATTR**: 定义可选属性

## 虚函数接口

- `onPrepareToRender()`: 渲染前准备(应用样式和变换)
- `onRender()`: 执行实际渲染
- `onAsPath()`: 转换为路径
- `onAsPaint()`: 转换为绘制属性
- `onObjectBoundingBox()`: 计算对象边界框

## 标签系统

每个节点有一个 `SkSVGTag` 标识元素类型(Circle, Rect, Path, G 等),用于类型识别和调试。

## 设计模式

使用模板方法模式,基类定义算法框架,派生类实现具体步骤。属性系统使用宏生成样板代码,减少重复。

## 相关文件

- `modules/svg/src/SkSVGNode.cpp`: 基类实现
- `SkSVGAttribute.h`: 属性定义
- `SkSVGTypes.h`: SVG 类型系统
- `SkSVGRenderContext.h`: 渲染上下文

`SkSVGNode` 是整个 Skia SVG 模块的核心抽象,定义了 SVG 元素的通用行为和属性管理机制。
