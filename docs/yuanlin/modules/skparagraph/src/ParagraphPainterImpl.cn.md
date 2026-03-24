# ParagraphPainterImpl

> 源文件: modules/skparagraph/src/ParagraphPainterImpl.h, modules/skparagraph/src/ParagraphPainterImpl.cpp

## 概述

`ParagraphPainterImpl` 提供了段落绘制接口 `ParagraphPainter` 的具体实现,将段落的绘制操作桥接到 Skia 的 Canvas 绘图系统。该模块定义了 `CanvasParagraphPainter` 类,负责将文本段落的渲染请求转换为具体的 Canvas 绘制调用,同时提供了一个 RAII 风格的自动状态保存恢复工具类 `ParagraphPainterAutoRestore`。

这个实现层是 Skia 段落布局系统与底层图形渲染系统之间的关键适配器,确保段落的文本、装饰线、阴影等元素能够正确地绘制到画布上。

## 架构位置

在 Skia 的模块化架构中,`ParagraphPainterImpl` 位于 `modules/skparagraph` 段落布局模块的内部实现层:

```
skia/
├── modules/
│   ├── skparagraph/
│   │   ├── include/
│   │   │   └── ParagraphPainter.h          # 抽象绘制接口
│   │   └── src/
│   │       ├── ParagraphPainterImpl.h      # Canvas绘制实现
│   │       ├── ParagraphPainterImpl.cpp
│   │       ├── ParagraphImpl.cpp           # 段落实现(使用Painter)
│   │       └── TextLine.cpp                # 文本行渲染(使用Painter)
```

该类作为具体实现,被段落布局系统的各个组件使用,特别是在 `ParagraphImpl` 和 `TextLine` 中进行实际的渲染操作。

## 主要类与结构体

### CanvasParagraphPainter
```cpp
class CanvasParagraphPainter : public ParagraphPainter
```
段落绘制器的 Canvas 实现类,持有一个 `SkCanvas*` 指针,将所有绘制操作转发给 Canvas。

**核心成员:**
- `fCanvas`: 持有的 Canvas 指针,所有绘制操作的目标画布

**主要方法:**
- `drawTextBlob()`: 绘制文本块
- `drawTextShadow()`: 绘制文本阴影
- `drawRect()`: 绘制矩形
- `drawFilledRect()`: 绘制填充矩形
- `drawPath()`: 绘制路径
- `drawLine()`: 绘制直线
- `clipRect()`: 设置裁剪区域
- `translate()`: 平移坐标系
- `save()/restore()`: 保存/恢复绘图状态

### ParagraphPainterAutoRestore
```cpp
class ParagraphPainterAutoRestore
```
RAII 风格的自动状态管理工具类,在构造时调用 `save()`,析构时调用 `restore()`,确保绘图状态的正确恢复。

**设计特点:**
- 构造函数自动保存画家状态
- 析构函数自动恢复画家状态
- 异常安全的状态管理

### DecorationStyle
```cpp
struct DecorationStyle
```
装饰样式结构体,定义在基类 `ParagraphPainter` 中,但在实现文件中构造:

**成员:**
- `fColor`: 装饰颜色
- `fStrokeWidth`: 线条宽度
- `fDashPathEffect`: 可选的虚线效果
- `fPaint`: 预配置的 SkPaint 对象

### DashPathEffect
```cpp
struct DashPathEffect
```
虚线路径效果配置:

**成员:**
- `fOnLength`: 实线段长度
- `fOffLength`: 空隙段长度

## 公共 API 函数

### 构造函数
```cpp
explicit CanvasParagraphPainter(SkCanvas* canvas)
```
使用指定的 Canvas 创建绘制器,Canvas 的生命周期由外部管理。

### 文本绘制
```cpp
void drawTextBlob(const sk_sp<SkTextBlob>& blob, SkScalar x, SkScalar y,
                  const SkPaintOrID& paint) override
```
在指定位置绘制文本块,使用提供的绘制样式。

**参数:**
- `blob`: 要绘制的文本块
- `x, y`: 绘制位置
- `paint`: 绘制样式(当前实现要求必须是 SkPaint)

```cpp
void drawTextShadow(const sk_sp<SkTextBlob>& blob, SkScalar x, SkScalar y,
                    SkColor color, SkScalar blurSigma) override
```
绘制带阴影效果的文本。

**参数:**
- `blurSigma`: 模糊半径,0 表示无模糊

### 装饰线绘制
```cpp
void drawRect(const SkRect& rect, const SkPaintOrID& paint) override
void drawFilledRect(const SkRect& rect, const DecorationStyle& decorStyle) override
void drawPath(const SkPath& path, const DecorationStyle& decorStyle) override
void drawLine(SkScalar x0, SkScalar y0, SkScalar x1, SkScalar y1,
              const DecorationStyle& decorStyle) override
```
一组用于绘制文本装饰(下划线、删除线等)的方法,支持实线和虚线效果。

### 坐标变换与裁剪
```cpp
void clipRect(const SkRect& rect) override
void translate(SkScalar dx, SkScalar dy) override
```
设置裁剪区域和坐标平移。

### 状态管理
```cpp
void save() override
void restore() override
```
保存和恢复 Canvas 的绘图状态栈。

## 内部实现细节

### 装饰样式初始化
`DecorationStyle` 的构造函数负责配置 `SkPaint` 对象:

```cpp
ParagraphPainter::DecorationStyle::DecorationStyle(
    SkColor color, SkScalar strokeWidth,
    std::optional<DashPathEffect> dashPathEffect)
{
    fPaint.setStyle(SkPaint::kStroke_Style);
    fPaint.setAntiAlias(true);
    fPaint.setColor(fColor);
    fPaint.setStrokeWidth(fStrokeWidth);

    if (fDashPathEffect) {
        const std::array<SkScalar, 4> intervals = {...};
        fPaint.setPathEffect(SkPathEffect::MakeCompose(
            SkDashPathEffect::Make(intervals, 0.0f),
            SkDiscretePathEffect::Make(0, 0)));
    }
}
```

**设计要点:**
- 始终启用抗锯齿以获得更好的视觉效果
- 使用描边样式绘制装饰线
- 虚线效果通过 `SkDashPathEffect` 和 `SkDiscretePathEffect` 的组合实现
- 使用 4 个间隔值来定义虚线模式

### 文本阴影实现
```cpp
void CanvasParagraphPainter::drawTextShadow(...) {
    SkPaint paint;
    paint.setColor(color);
    if (blurSigma != 0.0f) {
        sk_sp<SkMaskFilter> filter = SkMaskFilter::MakeBlur(
            kNormal_SkBlurStyle, blurSigma, false);
        paint.setMaskFilter(filter);
    }
    fCanvas->drawTextBlob(blob, x, y, paint);
}
```

**实现特点:**
- 创建临时 Paint 对象设置阴影颜色
- 使用 `SkMaskFilter::MakeBlur` 创建模糊效果
- `blurSigma` 为 0 时不应用模糊滤镜
- 使用 `kNormal_SkBlurStyle` 标准模糊样式

### Paint 类型断言
当前实现中,`drawTextBlob` 和 `drawRect` 方法都包含断言:
```cpp
SkASSERT(std::holds_alternative<SkPaint>(paint));
```
这表明尽管接口支持 `SkPaintOrID` 变体类型,当前的 Canvas 实现仅支持直接的 `SkPaint` 对象。

## 依赖关系

### 依赖的核心组件
- **SkCanvas**: 底层画布接口,所有绘制操作的目标
- **SkTextBlob**: 文本块表示,优化的文本绘制单元
- **SkPaint**: 绘制样式配置
- **SkMaskFilter**: 模糊效果滤镜
- **SkDashPathEffect**: 虚线路径效果
- **SkDiscretePathEffect**: 离散路径效果

### 被依赖关系
- **ParagraphImpl**: 使用 `CanvasParagraphPainter` 进行段落渲染
- **TextLine**: 使用画家接口绘制文本行
- **各种装饰器**: 使用装饰样式绘制下划线、删除线等

### 类图关系
```
ParagraphPainter (抽象接口)
    ↑
    | implements
    |
CanvasParagraphPainter (Canvas实现)
    |
    | holds
    ↓
SkCanvas (Skia核心)
```

## 设计模式与设计决策

### 适配器模式
`CanvasParagraphPainter` 是典型的适配器模式实现,将 `ParagraphPainter` 抽象接口适配到 `SkCanvas` 的具体实现:
- 接口统一了段落布局系统的绘制操作
- 实现允许切换不同的绘制后端
- 为未来支持其他绘制系统(如 GPU 直接渲染)预留了扩展空间

### RAII 资源管理
`ParagraphPainterAutoRestore` 采用 RAII(Resource Acquisition Is Initialization)模式:
- 自动管理 save/restore 配对,避免状态泄漏
- 异常安全,即使发生异常也能正确恢复状态
- 简化调用代码,无需手动管理状态栈

```cpp
{
    ParagraphPainterAutoRestore autoRestore(painter);
    // 执行绘制操作
} // 自动恢复状态
```

### 预计算优化
`DecorationStyle` 在构造时预配置 `SkPaint` 对象:
- 避免每次绘制时重复配置 Paint
- 路径效果对象预先创建并缓存
- 减少绘制时的 CPU 开销

### 转发模式
所有绘制方法都简单地转发到内部 Canvas:
- 保持薄适配层,最小化开销
- 逻辑清晰,易于维护
- 性能接近直接调用 Canvas

## 性能考量

### 对象生命周期
- **Canvas 引用**: 使用裸指针 `fCanvas`,避免引用计数开销,生命周期由外部管理
- **TextBlob 共享**: 使用 `sk_sp<SkTextBlob>` 智能指针,高效共享文本数据
- **临时 Paint**: 仅在 `drawTextShadow` 中创建临时 Paint,其他方法重用预配置对象

### 绘制优化
- **批量绘制**: TextBlob 本身已经是优化的批量文本表示
- **状态最小化**: 仅在必要时保存/恢复状态
- **抗锯齿**: 装饰线启用抗锯齿,提升视觉质量

### 路径效果缓存
虚线效果通过组合路径效果实现:
```cpp
fPaint.setPathEffect(SkPathEffect::MakeCompose(
    SkDashPathEffect::Make(intervals, 0.0f),
    SkDiscretePathEffect::Make(0, 0)));
```
路径效果对象在 `DecorationStyle` 构造时创建一次,后续绘制重复使用。

### 内联机会
大多数方法都是简单的一行转发,编译器可以有效内联,消除函数调用开销。

## 相关文件

### 接口定义
- `modules/skparagraph/include/ParagraphPainter.h`: 定义抽象的画家接口

### 使用方
- `modules/skparagraph/src/ParagraphImpl.h/.cpp`: 段落实现,主要绘制入口
- `modules/skparagraph/src/TextLine.h/.cpp`: 文本行渲染逻辑

### 依赖的 Skia 核心
- `include/core/SkCanvas.h`: Canvas 绘图接口
- `include/core/SkTextBlob.h`: 文本块表示
- `include/core/SkMaskFilter.h`: 遮罩滤镜(模糊效果)
- `include/effects/SkDashPathEffect.h`: 虚线效果
- `include/effects/SkDiscretePathEffect.h`: 离散路径效果

### 测试文件
- `modules/skparagraph/tests/*`: 段落布局相关测试,间接测试绘制器功能
