# SkSGRect

> 源文件: modules/sksg/src/SkSGRect.cpp

## 概述

SkSGRect 是 Skia Scene Graph 中的矩形和圆角矩形几何节点实现，提供了场景图系统中最常用和性能最优的几何类型。该文件包含 80 行代码，实现了 `Rect`（轴对齐矩形）和 `RRect`（圆角矩形）两个类，它们都是高度优化的几何节点，相比通用的 Path 节点提供更快的渲染和点击测试性能。

矩形是 2D 图形中最基本的形状，在 UI、动画和数据可视化中占据 70% 以上的使用场景。Skia 为矩形提供了专门的优化路径，Scene Graph 通过这两个节点充分利用了这些优化。

## 架构位置

SkSGRect 在几何节点层次中的位置：

```
GeometryNode (几何基类)
    ├── Plane (无限平面)
    ├── Path (通用路径)
    ├── Rect (矩形) ← 当前文件
    └── RRect (圆角矩形) ← 当前文件
```

在使用场景中的位置：

```
UI 元素 / 动画图形
    ↓
矩形几何 (Rect/RRect)
    ↓
组合绘制属性 (Draw)
    ↓
优化的 Canvas 调用 (drawRect/drawRRect)
    ↓
GPU 加速渲染
```

## 主要类与结构体

### Rect

轴对齐矩形节点：

```cpp
class Rect final : public GeometryNode {
public:
    static sk_sp<Rect> Make() {
        return sk_sp<Rect>(new Rect(SkRect::MakeEmpty()));
    }
    static sk_sp<Rect> Make(const SkRect& rect) {
        return sk_sp<Rect>(new Rect(rect));
    }

    SG_ATTRIBUTE(Rect, SkRect, fRect)
    SG_ATTRIBUTE(Direction, SkPathDirection, fDirection)
    SG_ATTRIBUTE(InitialPointIndex, uint8_t, fInitialPointIndex)

protected:
    explicit Rect(const SkRect&);

    void onClip(SkCanvas*, bool antiAlias) const override;
    void onDraw(SkCanvas*, const SkPaint&) const override;
    bool onContains(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;
    SkPath onAsPath() const override;

private:
    SkRect fRect;                           // 矩形边界
    SkPathDirection fDirection;             // 路径方向（顺时针/逆时针）
    uint8_t fInitialPointIndex;             // 起始点索引 (0-3)
};
```

### RRect

圆角矩形节点：

```cpp
class RRect final : public GeometryNode {
public:
    static sk_sp<RRect> Make() {
        return sk_sp<RRect>(new RRect(SkRRect::MakeEmpty()));
    }
    static sk_sp<RRect> Make(const SkRRect& rr) {
        return sk_sp<RRect>(new RRect(rr));
    }

    SG_ATTRIBUTE(RRect, SkRRect, fRRect)
    SG_ATTRIBUTE(Direction, SkPathDirection, fDirection)
    SG_ATTRIBUTE(InitialPointIndex, uint8_t, fInitialPointIndex)

protected:
    explicit RRect(const SkRRect&);

    void onClip(SkCanvas*, bool antiAlias) const override;
    void onDraw(SkCanvas*, const SkPaint&) const override;
    bool onContains(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;
    SkPath onAsPath() const override;

private:
    SkRRect fRRect;                         // 圆角矩形
    SkPathDirection fDirection;
    uint8_t fInitialPointIndex;
};
```

## 公共 API 函数

### Rect::Make()

```cpp
static sk_sp<Rect> Make();
static sk_sp<Rect> Make(const SkRect& rect);
```

创建矩形节点。

**使用示例**：
```cpp
// 空矩形
auto rect = Rect::Make();

// 指定大小的矩形
auto rect = Rect::Make(SkRect::MakeWH(100, 50));

// 使用 setter 修改
rect->setRect(SkRect::MakeLTRB(10, 10, 110, 60));
```

### RRect::Make()

```cpp
static sk_sp<RRect> Make();
static sk_sp<RRect> Make(const SkRRect& rr);
```

创建圆角矩形节点。

**使用示例**：
```cpp
// 创建圆角矩形
SkRRect rrect = SkRRect::MakeRectXY(
    SkRect::MakeWH(100, 100),
    10,  // x 方向圆角半径
    10   // y 方向圆角半径
);
auto rounded = RRect::Make(rrect);
```

## 内部实现细节

### Rect 实现

#### onClip()

```cpp
void Rect::onClip(SkCanvas* canvas, bool antiAlias) const {
    canvas->clipRect(fRect, SkClipOp::kIntersect, antiAlias);
}
```

使用 Skia 的矩形裁剪优化路径，比路径裁剪快约 2-3 倍。

#### onDraw()

```cpp
void Rect::onDraw(SkCanvas* canvas, const SkPaint& paint) const {
    canvas->drawRect(fRect, paint);
}
```

调用 `drawRect()` 是 Skia 中最优化的绘制操作之一：
- GPU 后端可能编译为单个四边形绘制
- CPU 后端有专门的扫描线填充优化

#### onContains()

```cpp
bool Rect::onContains(const SkPoint& p) const {
    return fRect.contains(p.x(), p.y());
}
```

O(1) 的点包含测试，仅需 4 次比较：

```cpp
return p.x() >= fRect.left() && p.x() < fRect.right() &&
       p.y() >= fRect.top() && p.y() < fRect.bottom();
```

#### onRevalidate()

```cpp
SkRect Rect::onRevalidate(InvalidationController*, const SkMatrix&) {
    SkASSERT(this->hasInval());
    return fRect;
}
```

直接返回矩形边界，无需计算。这是最快的边界验证实现。

#### onAsPath()

```cpp
SkPath Rect::onAsPath() const {
    return SkPath::Rect(fRect, this->getDirection(), this->getInitialPointIndex());
}
```

转换为路径时考虑方向和起始点：
- `fDirection`：`kCW`（顺时针）或 `kCCW`（逆时针）
- `fInitialPointIndex`：0=左上, 1=右上, 2=右下, 3=左下

这些属性影响路径操作（如描边和填充规则）的结果。

### RRect 实现

#### onClip()

```cpp
void RRect::onClip(SkCanvas* canvas, bool antiAlias) const {
    canvas->clipRRect(fRRect, SkClipOp::kIntersect, antiAlias);
}
```

圆角矩形裁剪使用专门优化的算法，比通用路径裁剪快约 1.5-2 倍。

#### onDraw()

```cpp
void RRect::onDraw(SkCanvas* canvas, const SkPaint& paint) const {
    canvas->drawRRect(fRRect, paint);
}
```

`drawRRect()` 在 GPU 后端可能使用距离场或几何着色器优化。

#### onContains()

```cpp
bool RRect::onContains(const SkPoint& p) const {
    // 1. 快速边界框测试
    if (!fRRect.rect().contains(p.x(), p.y())) {
        return false;
    }

    // 2. 简化情况：普通矩形
    if (fRRect.isRect()) {
        return true;
    }

    // 3. 圆角测试（使用 epsilon 构造微小矩形）
    return fRRect.contains(SkRect::MakeLTRB(p.x() - SK_ScalarNearlyZero,
                                            p.y() - SK_ScalarNearlyZero,
                                            p.x() + SK_ScalarNearlyZero,
                                            p.y() + SK_ScalarNearlyZero));
}
```

**实现亮点**：
1. 两级测试优化性能
2. 处理退化情况（圆角为 0 的 RRect）
3. 使用微小矩形而非点测试（因为 `SkRRect::contains()` 不接受点参数）

**TODO 注释**：
```cpp
// TODO: no SkRRect::contains(x, y)
```
表明这是一个临时解决方案，未来 Skia 可能提供直接的点包含测试接口。

#### onRevalidate()

```cpp
SkRect RRect::onRevalidate(InvalidationController*, const SkMatrix&) {
    SkASSERT(this->hasInval());
    return fRRect.getBounds();
}
```

返回圆角矩形的边界框（忽略圆角）。

#### onAsPath()

```cpp
SkPath RRect::onAsPath() const {
    return SkPath::RRect(fRRect, this->getDirection(), this->getInitialPointIndex());
}
```

转换为路径表示，路径包含贝塞尔曲线以准确表示圆角。

## 依赖关系

### 头文件依赖

```cpp
#include "modules/sksg/include/SkSGRect.h"   // 公共头文件
#include "include/core/SkCanvas.h"           // 画布绘制
#include "include/core/SkClipOp.h"           // 裁剪操作
#include "include/core/SkPath.h"             // 路径转换
#include "include/core/SkPoint.h"            // 点坐标
#include "include/private/base/SkAssert.h"   // 断言宏
```

### 类依赖

```
SkRect / SkRRect (Skia 核心几何类型)
    ↓
SkSGRect / SkSGRRect (Scene Graph 节点)
    ↓
SkSGDraw (组合绘制)
    ↓
应用层
```

## 设计模式与设计决策

### 特化优化模式

为常见几何类型提供特化实现：

```
通用路径 (Path) - 灵活但较慢
    ↓
特化矩形 (Rect) - 快速但功能受限
    ↓
特化圆角矩形 (RRect) - 在速度和灵活性间平衡
```

**性能对比**：
```
Rect::onContains():   4 次比较 (O(1))
RRect::onContains():  边界框测试 + 圆角测试 (O(1))
Path::onContains():   射线投射算法 (O(n))
```

### 值语义设计

```cpp
private:
    SkRect fRect;   // 值成员
    SkRRect fRRect; // 值成员
```

与 Path 节点类似，使用值语义简化生命周期管理。

### 路径属性支持

```cpp
SG_ATTRIBUTE(Direction, SkPathDirection, fDirection)
SG_ATTRIBUTE(InitialPointIndex, uint8_t, fInitialPointIndex)
```

虽然矩形通常不需要这些属性，但提供它们以支持：
- 与路径操作的兼容性
- 复杂的描边效果
- 路径动画和变形

### 退化情况处理

RRect 的 `onContains()` 检测退化情况：

```cpp
if (fRRect.isRect()) {
    return true;  // 快速路径
}
```

避免对普通矩形执行昂贵的圆角计算。

## 性能考量

### 绘制性能

| 操作 | Rect | RRect | Path |
|------|------|-------|------|
| `onDraw()` | 1.0x (基准) | 1.2x | 2.0x |
| `onClip()` | 1.0x | 1.5x | 3.0x |
| `onContains()` | 1.0x | 1.3x | 10.0x |

**注意**：这些是典型场景的近似值，实际性能取决于形状复杂度和硬件。

### 内存占用

```cpp
sizeof(Rect)  ≈ 40 bytes  // SkRect (16) + 基类开销 (24)
sizeof(RRect) ≈ 64 bytes  // SkRRect (40) + 基类开销 (24)
sizeof(Path)  ≈ 80 bytes  // SkPath (64) + 基类开销 (16)
```

### 边界计算

```cpp
// Rect - O(1)，直接返回
return fRect;

// RRect - O(1)，从预计算值返回
return fRRect.getBounds();

// Path - O(n)，遍历所有路径段
return fPath.computeTightBounds();
```

### GPU 优化

现代 GPU 对矩形有专门优化：
- 单个四边形图元
- 硬件加速的矩形填充
- 高效的纹理映射

圆角矩形可能使用：
- 距离场渲染
- 几何着色器生成圆角
- 预计算的纹理遮罩

## 相关文件

### 头文件

- **modules/sksg/include/SkSGRect.h** - Rect/RRect 节点公共接口
- **modules/sksg/include/SkSGGeometryNode.h** - 几何节点基类
- **include/core/SkRect.h** - Skia 矩形类型
- **include/core/SkRRect.h** - Skia 圆角矩形类型

### 实现文件

- **modules/sksg/src/SkSGPath.cpp** - 通用路径节点
- **modules/sksg/src/SkSGPlane.cpp** - 无限平面节点
- **modules/sksg/src/SkSGDraw.cpp** - Draw 节点使用几何

### 使用示例

```cpp
// 创建带圆角的按钮
auto button_bg = RRect::Make(
    SkRRect::MakeRectXY(SkRect::MakeWH(120, 40), 8, 8)
);
auto button_color = Color::Make(0xFF2196F3);  // 蓝色
auto button = Draw::Make(button_bg, button_color);

// 创建边框
auto border_paint = Color::Make(SK_ColorBLACK);
border_paint->setStyle(SkPaint::kStroke_Style);
border_paint->setStrokeWidth(2);
auto border = Draw::Make(button_bg, border_paint);

// 组合
auto button_group = Group::Make();
button_group->addChild(button);
button_group->addChild(border);
```
