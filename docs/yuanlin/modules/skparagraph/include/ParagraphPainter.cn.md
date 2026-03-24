# ParagraphPainter

> 源文件: [modules/skparagraph/include/ParagraphPainter.h](../../../../modules/skparagraph/include/ParagraphPainter.h)

## 概述

`ParagraphPainter` 定义了段落绘制的抽象接口，将段落渲染与具体的绘图后端解耦。通过这个接口，客户端可以自定义段落的绘制行为，而不局限于 `SkCanvas`。该接口支持文本 blob 绘制、文本阴影、矩形和路径绘制、装饰线绘制，以及画布状态管理（裁剪、平移、保存/恢复）。

## 架构位置

```
skia::textlayout 命名空间
  ParagraphPainter (抽象接口)  ← 本文件定义
    └── CanvasParagraphPainter (默认 SkCanvas 实现)
          └── 被 Paragraph::paint(ParagraphPainter*) 调用
```

`ParagraphPainter` 是 `Paragraph` 和具体绘图后端之间的抽象层。

## 主要类与结构体

### ParagraphPainter
- 纯虚接口类，定义段落绘制的所有操作
- 虚析构函数确保正确的多态销毁

### ParagraphPainter::PaintID
- `typedef int PaintID`
- 画笔标识符，用于自定义 `ParagraphPainter` 实现中引用预定义的画笔

### ParagraphPainter::SkPaintOrID
- `typedef std::variant<SkPaint, PaintID>`
- 联合类型，允许传递 `SkPaint` 对象或画笔 ID

### ParagraphPainter::DashPathEffect
- 虚线路径效果参数
- `fOnLength`: 虚线段长度
- `fOffLength`: 间隙长度

### ParagraphPainter::DecorationStyle
- 装饰线样式类，封装文本装饰线的绘制参数
- 包含：`fColor`（颜色）、`fStrokeWidth`（线宽）、`fDashPathEffect`（可选虚线效果）、`fPaint`（内部 SkPaint）
- 提供 getter 方法和 `skPaint()` 访问内部画笔

## 公共 API 函数

### 文本绘制
```cpp
virtual void drawTextBlob(const sk_sp<SkTextBlob>& blob, SkScalar x, SkScalar y,
                          const SkPaintOrID& paint) = 0;
```
绘制文本 blob（字形批次），这是段落渲染的核心方法。

```cpp
virtual void drawTextShadow(const sk_sp<SkTextBlob>& blob, SkScalar x, SkScalar y,
                            SkColor color, SkScalar blurSigma) = 0;
```
绘制文本阴影，带模糊效果。

### 图形绘制
```cpp
virtual void drawRect(const SkRect& rect, const SkPaintOrID& paint) = 0;
virtual void drawFilledRect(const SkRect& rect, const DecorationStyle& decorStyle) = 0;
virtual void drawPath(const SkPath& path, const DecorationStyle& decorStyle) = 0;
virtual void drawLine(SkScalar x0, SkScalar y0, SkScalar x1, SkScalar y1,
                      const DecorationStyle& decorStyle) = 0;
```
绘制矩形（用于背景、选区等）、填充矩形、路径和直线（用于装饰线）。

### 画布状态管理
```cpp
virtual void clipRect(const SkRect& rect) = 0;
virtual void translate(SkScalar dx, SkScalar dy) = 0;
virtual void save() = 0;
virtual void restore() = 0;
```
标准的画布状态操作：裁剪、平移、保存和恢复。

## 内部实现细节

### SkPaintOrID 设计

`std::variant<SkPaint, PaintID>` 的设计允许两种使用模式：
- **SkPaint 模式**: 直接传递 Skia 画笔对象，适用于标准 SkCanvas 绘制
- **PaintID 模式**: 传递整数标识符，适用于自定义画笔管理（如 Flutter 引擎中，画笔在 Dart 层创建并通过 ID 引用）

### DecorationStyle 封装

`DecorationStyle` 将装饰线的所有参数封装为一个不可变对象，内部预构建了 `SkPaint`，通过 `skPaint()` 方法暴露，避免在绘制时重复构建画笔。

## 依赖关系

- **Skia 核心**: `SkPaint`、`SkTextBlob`、`SkRect`、`SkPath`、`SkColor`、`SkScalar`
- **标准库**: `<optional>`、`<variant>`

## 设计模式与设计决策

1. **策略模式（Strategy Pattern）**: `ParagraphPainter` 作为绘制策略接口，允许运行时替换不同的绘制后端。`Paragraph::paint(ParagraphPainter*)` 接受任意实现。

2. **接口与实现分离**: 纯虚接口确保段落排版逻辑与绘图后端完全解耦。默认的 `CanvasParagraphPainter` 将调用转发到 `SkCanvas`。

3. **variant 类型**: `SkPaintOrID` 使用 `std::variant` 而非继承或指针，提供类型安全的联合类型，避免堆分配和虚函数调用开销。

4. **值语义参数**: `DashPathEffect` 和 `DecorationStyle` 使用值类型传递，避免生命周期管理问题。

5. **最小接口原则**: 接口仅包含段落绘制所需的操作，不暴露完整的画布 API，限制了实现的复杂度。

## 性能考量

- `drawTextBlob` 是最频繁调用的方法，实现应尽可能高效。
- `DecorationStyle` 预构建 `SkPaint`，避免在装饰线绘制时重复创建。
- `SkPaintOrID` 的 `variant` 访问通过编译器优化后通常为零开销。
- `save()/restore()` 成对调用，实现应使用栈结构以确保 O(1) 操作。

## 相关文件

- `modules/skparagraph/src/ParagraphPainterImpl.h` - 默认 SkCanvas 实现
- `modules/skparagraph/include/Paragraph.h` - 使用此接口的段落类
- `modules/skparagraph/include/TextStyle.h` - 文本样式（引用 SkPaintOrID）
- `include/core/SkPaint.h` - Skia 画笔
- `include/core/SkTextBlob.h` - 文本 blob
