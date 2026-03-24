# DrawParams

> 源文件
> - src/gpu/graphite/DrawParams.h

## 概述

`DrawParams.h` 定义了单个高级绘制调用的所有几何状态封装类，包括变换、几何形状、裁剪、绘制顺序和描边样式。该文件包含三个主要类：`StrokeStyle`（描边样式）、`Clip`（裁剪信息）和 `DrawParams`（完整绘制参数）。

这些类将绘制操作的所有参数打包成紧凑且高效的形式，供 `RenderStep` 执行实际渲染。着色相关的信息（如颜色、着色器）由 `PaintParams` 单独处理。

## 主要类与结构体

### StrokeStyle 类

```cpp
class StrokeStyle {
public:
    StrokeStyle();  // 默认填充
    StrokeStyle(float width, float miterLimit, SkPaint::Join join, SkPaint::Cap cap);

    bool isMiterJoin() const;
    bool isBevelJoin() const;
    bool isRoundJoin() const;

    float halfWidth() const;
    float width() const;
    float miterLimit() const;
    SkPaint::Cap cap() const;
    SkPaint::Join join() const;
    float joinLimit() const;  // 原始限制值

private:
    float fHalfWidth;  // >0: 相对于变换; ==0: 细线，设备空间 1px
    float fJoinLimit;  // >0: miter连接; ==0: bevel连接; <0: round连接
    SkPaint::Cap fCap;
};
```

**编码技巧**：使用 `fJoinLimit` 的符号编码连接类型，节省存储空间。

### Clip 类

```cpp
class Clip {
public:
    Clip(const Rect& drawBounds,
         const Rect& shapeBounds,
         const SkIRect& scissor,
         const NonMSAAClip& nonMSAAClip,
         const SkShader* shader);

    const Rect& drawBounds() const;
    const Rect& transformedShapeBounds() const;
    const SkIRect& scissor() const;
    const NonMSAAClip& nonMSAAClip() const;
    const SkShader* shader() const;

    bool isClippedOut() const;
    bool needsCoverage() const;
    void outsetBoundsForAA();

private:
    Rect fDrawBounds;
    Rect fTransformedShapeBounds;
    SkIRect fScissor;
    NonMSAAClip fNonMSAAClip;
    const SkShader* fShader;
};
```

### DrawParams 类

```cpp
class DrawParams {
public:
    DrawParams(const Transform& transform,
              const Geometry& geometry,
              const Clip& clip,
              DrawOrder drawOrder,
              const StrokeStyle* stroke,
              BarrierType barrierBeforeDraws);

    const Transform& transform() const;
    const Geometry& geometry() const;
    DrawOrder order() const;
    Rect drawBounds() const;
    Rect transformedShapeBounds() const;
    BarrierType barrierBeforeDraws() const;
    const SkIRect& scissor() const;

    bool isStroke() const;
    const StrokeStyle& strokeStyle() const;

private:
    const Transform& fTransform;
    Geometry fGeometry;
    Rect fDrawBounds;
    Rect fTransformedShapeBounds;
    SkIRect fScissor;
    DrawOrder fOrder;
    BarrierType fBarrierBeforeDraws;
    std::optional<StrokeStyle> fStroke;
};
```

## 关键概念

### 边界层次

**drawBounds**：
- 绘制的紧密边界
- 包括描边扩展
- 考虑逆向填充
- 与裁剪矩形相交

**transformedShapeBounds**：
- 设备空间中形状的未裁剪边界
- 包括描边但忽略填充规则
- 不受裁剪矩形限制

**scissor**：
- 裁剪栈产生的裁剪矩形
- 必须包含 drawBounds
- 已与设备边界相交

### 非 MSAA 裁剪

`NonMSAAClip` 用于需要覆盖蒙版但不使用 MSAA 的裁剪：
- 形状边界裁剪
- 图集蒙版裁剪
- 不能收紧 `drawBounds`（避免 GPU 未定义行为）

### 裁剪着色器

`fShader` 指向裁剪着色器（如果有）：
- 输出 alpha 用于进一步裁剪
- 由着色系统处理

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/DrawOrder.h` | 绘制顺序 |
| `src/gpu/graphite/DrawTypes.h` | 绘制类型定义 |
| `src/gpu/graphite/geom/Geometry.h` | 几何形状 |
| `src/gpu/graphite/geom/Transform.h` | 变换矩阵 |
| `src/gpu/graphite/geom/NonMSAAClip.h` | 非 MSAA 裁剪 |
| `src/gpu/graphite/Renderer.h` | 渲染器使用 DrawParams |
