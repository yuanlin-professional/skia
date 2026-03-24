# SkPaintFilterCanvas

> 源文件: include/utils/SkPaintFilterCanvas.h, src/utils/SkPaintFilterCanvas.cpp

## 概述

`SkPaintFilterCanvas` 是 Skia 图形库中的画布代理类,提供了一种在绘制操作执行前拦截和修改 `SkPaint` 的机制。该类继承自 `SkNWayCanvas`,允许开发者在不修改原始绘制代码的情况下,统一过滤和转换所有绘制操作的绘制属性。

核心设计思想是代理模式:所有绘制调用首先经过过滤器处理,然后转发给底层画布。通过重写 `onFilter` 方法,子类可以实现各种效果,如全局透明度调整、颜色空间转换、图层效果预览等。该模块特别适用于需要在不侵入绘制逻辑的情况下修改视觉效果的场景。

## 架构位置

`SkPaintFilterCanvas` 位于 Skia 的实用工具层,作为画布的高级包装器:

```
应用层绘制代码
   ↓
SkPaintFilterCanvas (工具层 - include/utils, src/utils)
   ↓
SkNWayCanvas (多路画布基类)
   ↓
SkCanvas (底层画布)
   ↓
SkDevice (设备层)
```

典型使用场景:
- Android Framework 使用它实现视图过滤
- 图层效果预览
- 调试和测试工具
- 绘制拦截和分析

## 主要类与结构体

### SkPaintFilterCanvas

抽象基类,提供绘制属性过滤功能。

**继承关系**:
```
SkNWayCanvas
   ↑
SkCanvasVirtualEnforcer<SkNWayCanvas>
   ↑
SkPaintFilterCanvas
```

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fList | SkTDArray<SkCanvas*> | 继承自 SkNWayCanvas,存储被代理的画布 |

### AutoPaintFilter (内部辅助类)

RAII 风格的自动过滤器,负责在绘制操作前后管理 `SkPaint` 的过滤。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fPaint | SkPaint | 过滤后的绘制属性副本 |
| fShouldDraw | bool | 指示是否应执行绘制操作 |

**构造函数**:
```cpp
AutoPaintFilter(const SkPaintFilterCanvas* canvas, const SkPaint* paint)
    : fPaint(paint ? *paint : SkPaint()) {
    fShouldDraw = canvas->onFilter(fPaint);
}
```

## 公共 API 函数

### 构造函数

```cpp
explicit SkPaintFilterCanvas(SkCanvas* canvas);
```

创建新的过滤画布,配置为转发到指定画布。同时复制目标画布的矩阵和裁剪边界。

**参数**:
- `canvas`: 被代理的底层画布

### 纯虚函数 - onFilter

```cpp
virtual bool onFilter(SkPaint& paint) const = 0;
```

核心过滤方法,子类必须实现。在每次绘制操作前调用,允许修改绘制属性。

**参数**:
- `paint`: 可修改的绘制属性引用

**返回值**:
- `true`: 执行绘制操作
- `false`: 跳过该绘制操作

**注意**: 基础实现仅过滤顶层/显式的 `SkPaint`。要过滤封装的绘制对象(如 `SkPicture`、`SkTextBlob`)中的属性,需要重写相关方法(如 `drawPicture`、`drawTextBlob`)。

### 转发方法

```cpp
SkISize getBaseLayerSize() const override;
GrRecordingContext* recordingContext() const override;
```

这些方法直接转发给底层画布,确保画布查询返回正确信息。

## 内部实现细节

### 绘制操作拦截模式

所有绘制方法遵循统一模式:

```cpp
void SkPaintFilterCanvas::onDrawRect(const SkRect& rect, const SkPaint& paint) {
    AutoPaintFilter apf(this, paint);
    if (apf.shouldDraw()) {
        this->SkNWayCanvas::onDrawRect(rect, apf.paint());
    }
}
```

1. 创建 `AutoPaintFilter` 对象,触发 `onFilter` 调用
2. 检查 `shouldDraw()` 决定是否绘制
3. 使用过滤后的 `paint` 调用父类方法

### 支持的绘制操作

模块覆盖了所有主要绘制方法:

**基本图形**:
- `onDrawPaint`, `onDrawBehind`
- `onDrawPoints`, `onDrawRect`, `onDrawRRect`
- `onDrawDRRect`, `onDrawOval`, `onDrawArc`
- `onDrawPath`, `onDrawRegion`

**图像绘制**:
- `onDrawImage2`, `onDrawImageRect2`
- `onDrawImageLattice2`, `onDrawAtlas2`

**高级图形**:
- `onDrawVerticesObject`, `onDrawPatch`
- `onDrawEdgeAAQuad`, `onDrawEdgeAAImageSet2`

**文本和复合对象**:
- `onDrawGlyphRunList`, `onDrawTextBlob`
- `onDrawPicture`, `onDrawDrawable`

**特殊操作**:
- `onDrawAnnotation` (不过滤)
- `onDrawShadowRec` (不过滤)

### SkPicture 的特殊处理

`drawPicture` 方法包含优化逻辑:

```cpp
void SkPaintFilterCanvas::onDrawPicture(const SkPicture* picture,
                                        const SkMatrix* m,
                                        const SkPaint* originalPaint) {
    AutoPaintFilter apf(this, originalPaint);
    if (apf.shouldDraw()) {
        const SkPaint* newPaint = &apf.paint();

        // 传递 paint 会导致绘制到图层,影响性能和混合效果
        if (originalPaint == nullptr) {
            if (newPaint->getAlphaf()      == 1.0f &&
                newPaint->getColorFilter() == nullptr &&
                newPaint->getImageFilter() == nullptr &&
                newPaint->asBlendMode()    == SkBlendMode::kSrcOver) {
                // 恢复原始的 nullptr
                newPaint = nullptr;
            }
        }
        this->SkNWayCanvas::onDrawPicture(picture, m, newPaint);
    }
}
```

**优化原理**:
- 传递 `paint` 参数会使 `drawPicture` 创建图层,严重影响性能
- 如果过滤器没有实质性改变(alpha=1, 无滤镜, SrcOver 模式),则恢复 `nullptr`
- 避免不必要的图层创建

### EdgeAAQuad 的颜色处理

```cpp
void SkPaintFilterCanvas::onDrawEdgeAAQuad(const SkRect& rect,
                                           const SkPoint clip[4],
                                           QuadAAFlags aa,
                                           const SkColor4f& color,
                                           SkBlendMode mode) {
    SkPaint paint;
    paint.setColor(color);
    paint.setBlendMode(mode);
    AutoPaintFilter apf(this, paint);
    if (apf.shouldDraw()) {
        this->SkNWayCanvas::onDrawEdgeAAQuad(
            rect, clip, aa,
            apf.paint().getColor4f(),
            apf.paint().getBlendMode_or(SkBlendMode::kSrcOver));
    }
}
```

将颜色和混合模式转换为 `SkPaint` 进行过滤,然后提取回原始参数类型。

### 表面和像素访问转发

```cpp
sk_sp<SkSurface> onNewSurface(const SkImageInfo&, const SkSurfaceProps&) override;
bool onPeekPixels(SkPixmap* pixmap) override;
bool onAccessTopLayerPixels(SkPixmap* pixmap) override;
SkImageInfo onImageInfo() const override;
bool onGetProps(SkSurfaceProps* props, bool top) const override;
```

这些方法直接调用 `proxy()->xxx()`,确保表面相关操作正确转发到底层画布。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkNWayCanvas | 基类,提供多路画布转发机制 |
| SkCanvas | 画布抽象接口 |
| SkPaint | 绘制属性 |
| SkPath, SkRRect, SkRegion | 图形对象 |
| SkImage, SkPicture | 图像和图片对象 |
| SkTextBlob | 文本 blob |
| SkVertices | 顶点数据 |
| SkSurface | 表面抽象 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| Android Framework | SkAndroidFrameworkUtils 使用该类实现视图过滤 |
| 调试工具 | 拦截绘制操作进行分析 |
| 测试框架 | 验证绘制属性是否符合预期 |
| 效果预览工具 | 实时预览不同绘制属性的效果 |

## 设计模式与设计决策

### 代理模式 (Proxy Pattern)

`SkPaintFilterCanvas` 是典型的代理模式实现:

- **Subject**: `SkCanvas` 接口
- **RealSubject**: 被代理的底层画布
- **Proxy**: `SkPaintFilterCanvas` 拦截调用并添加过滤逻辑

**优点**:
- 在不修改原始代码的情况下添加功能
- 透明地替换原始画布
- 可以组合多个过滤器(通过嵌套)

### 模板方法模式 (Template Method Pattern)

`onFilter` 是模板方法:

- 基类定义了调用框架(在每个 `onDraw*` 方法中)
- 子类实现具体的过滤逻辑
- 钩子方法返回布尔值控制流程

### RAII 模式

`AutoPaintFilter` 采用 RAII 风格:

```cpp
AutoPaintFilter apf(this, paint);  // 构造时过滤
// apf 自动管理过滤后的 paint 生命周期
```

**优点**:
- 异常安全
- 自动清理
- 简化调用代码

### 关注点分离

过滤逻辑与转发逻辑分离:

- `AutoPaintFilter`: 负责过滤和判断
- `SkPaintFilterCanvas`: 负责方法拦截和转发
- 子类: 仅实现 `onFilter` 的业务逻辑

### 最小惊讶原则

- 保持画布查询方法的语义:`getBaseLayerSize`、`recordingContext` 等直接转发
- 不过滤的操作(如 `onDrawAnnotation`)保持原样
- 确保过滤画布在外部看来与普通画布行为一致

## 性能考量

### 按值复制 Paint

```cpp
AutoPaintFilter(const SkPaintFilterCanvas* canvas, const SkPaint* paint)
    : fPaint(paint ? *paint : SkPaint())
```

每次绘制都复制 `SkPaint`:

**开销**: `SkPaint` 包含智能指针,复制涉及引用计数操作
**优化**: 由于大部分成员是 `sk_sp`,实际复制仅增加引用计数,不复制底层对象

### SkPicture 图层避免

`onDrawPicture` 的优化逻辑避免了不必要的图层创建:

- **无图层**: 直接绘制,性能最优
- **有图层**: 离屏渲染,内存占用增加,合成操作增加

检查 alpha、滤镜等属性,仅在必要时创建图层。

### 内联小方法

`shouldDraw()` 和 `paint()` 是简单的访问器,编译器可内联:

```cpp
const SkPaint& paint() const { return fPaint; }
bool shouldDraw() const { return fShouldDraw; }
```

### 虚函数调用开销

所有绘制方法都是虚函数,每次绘制涉及虚函数调用:

- `SkPaintFilterCanvas::onDrawRect` (虚函数)
- `onFilter` (纯虚函数)
- `SkNWayCanvas::onDrawRect` (虚函数)

对于高频绘制场景,虚函数开销可能累积。建议仅在必要时使用过滤画布。

### 条件绘制的短路优化

```cpp
if (apf.shouldDraw()) {
    // 仅在需要时调用绘制
}
```

如果 `onFilter` 返回 `false`,后续绘制逻辑完全跳过,节省处理开销。

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| include/utils/SkPaintFilterCanvas.h | 公共 API 头文件 |
| src/utils/SkPaintFilterCanvas.cpp | 实现文件 |
| include/utils/SkNWayCanvas.h | 基类头文件 |
| include/core/SkCanvas.h | 画布接口 |
| include/core/SkPaint.h | 绘制属性 |
| include/core/SkSurface.h | 表面抽象 |
| src/core/SkDevice.h | 设备层 |
