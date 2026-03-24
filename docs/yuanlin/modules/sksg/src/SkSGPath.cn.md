# SkSGPath

> 源文件: modules/sksg/src/SkSGPath.cpp

## 概述

SkSGPath 是 Skia Scene Graph 中的通用路径几何节点实现，能够表示任意复杂的矢量图形，包括直线、曲线、多边形和复合路径。该文件仅包含 50 行代码，却提供了场景图系统中最灵活的几何表示能力，是构建复杂矢量图形的基础。

Path 节点封装了 Skia 的 `SkPath` 对象，支持所有路径操作，包括填充规则、路径方向、逆向填充等高级特性。它是除 Rect 和 Plane 之外最常用的几何节点。

## 架构位置

SkSGPath 在场景图几何节点层次中的位置：

```
Scene Graph 模块 (modules/sksg)
    ├── Node (所有节点基类)
    │
    ├── GeometryNode (几何节点基类)
    │   ├── Rect (矩形 - 优化的特殊情况)
    │   ├── Plane (无限平面 - 特殊情况)
    │   ├── Path (通用路径) ← 当前文件
    │   └── ... (其他几何节点)
    │
    └── RenderNode (渲染节点)
        └── Draw (组合几何与绘制)
```

在渲染管线中的作用：

```
路径数据 (SkPath)
    ↓
Path 节点封装
    ↓
Draw 节点组合
    ↓
Canvas 绘制 (drawPath)
    ↓
光栅化输出
```

## 主要类与结构体

### Path

```cpp
class Path final : public GeometryNode {
public:
    // 工厂方法
    static sk_sp<Path> Make() {
        return sk_sp<Path>(new Path(SkPath()));
    }
    static sk_sp<Path> Make(const SkPath& path) {
        return sk_sp<Path>(new Path(path));
    }

    // 属性访问
    SG_ATTRIBUTE(Path, SkPath, fPath)

protected:
    explicit Path(const SkPath&);

    // GeometryNode 接口实现
    void onClip(SkCanvas*, bool antiAlias) const override;
    void onDraw(SkCanvas*, const SkPaint&) const override;
    bool onContains(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;
    SkPath onAsPath() const override;

private:
    SkPath fPath;  // 封装的 Skia 路径对象
};
```

**成员变量**：
- `fPath`：存储的 `SkPath` 对象，包含所有路径数据和属性

**特点**：
- **final 类**：不可继承
- **值语义**：存储 `SkPath` 的副本（非指针）
- **属性宏**：使用 `SG_ATTRIBUTE` 生成 getter/setter

## 公共 API 函数

### Path::Make()

```cpp
static sk_sp<Path> Make();
static sk_sp<Path> Make(const SkPath& path);
```

工厂方法，创建路径节点。

**使用示例**：
```cpp
// 创建空路径
auto path_node = Path::Make();

// 从现有路径创建
SkPath sk_path;
sk_path.moveTo(0, 0);
sk_path.lineTo(100, 0);
sk_path.lineTo(100, 100);
sk_path.close();
auto triangle = Path::Make(sk_path);

// 使用 setter 修改路径
auto path = Path::Make();
SkPath new_path;
new_path.addCircle(50, 50, 25);
path->setPath(new_path);  // SG_ATTRIBUTE 生成的 setter
```

### 继承的 GeometryNode 接口

- `void clip(SkCanvas*, bool)` - 应用裁剪
- `void draw(SkCanvas*, const SkPaint&)` - 绘制路径
- `bool contains(const SkPoint&)` - 点击测试
- `SkPath asPath()` - 转换为路径（返回自身）
- `SkRect revalidate(...)` - 验证并返回边界

## 内部实现细节

### 构造函数

```cpp
Path::Path(const SkPath& path) : fPath(path) {}
```

接受 `const SkPath&` 参数，复制路径数据。这是值语义设计，确保路径节点拥有独立的路径数据，不受外部修改影响。

### onClip() - 裁剪实现

```cpp
void Path::onClip(SkCanvas* canvas, bool antiAlias) const {
    canvas->clipPath(fPath, SkClipOp::kIntersect, antiAlias);
}
```

**实现要点**：
- 使用 `SkClipOp::kIntersect` 裁剪模式（与现有裁剪区域求交集）
- 支持抗锯齿裁剪（通过 `antiAlias` 参数）
- 考虑路径的填充规则（Winding/EvenOdd/Inverse）

**使用场景**：
```cpp
// 在 ClipEffect 节点中使用
auto clip_path = Path::Make(circular_path);
auto clip_effect = ClipEffect::Make(content, clip_path);
// 渲染时会调用 clip_path->onClip(canvas, true)
```

### onDraw() - 绘制实现

```cpp
void Path::onDraw(SkCanvas* canvas, const SkPaint& paint) const {
    canvas->drawPath(fPath, paint);
}
```

最简单直接的实现，将路径绘制委托给 Skia Canvas。`paint` 参数包含所有绘制属性（颜色、描边、着色器等）。

**绘制流程**：
1. Canvas 根据 `paint.getStyle()` 决定填充或描边
2. 应用路径填充规则
3. 执行光栅化

### onContains() - 点包含测试

```cpp
bool Path::onContains(const SkPoint& p) const {
    return fPath.contains(p.x(), p.y());
}
```

**底层实现**（SkPath::contains）：
- 使用射线投射算法（Ray Casting）
- 根据填充规则判断点是否在路径内部
- 支持 Winding 和 EvenOdd 规则

**复杂度**：O(n)，其中 n 是路径段数量

**示例**：
```cpp
auto star = Path::Make(star_path);
star->contains({50, 50});  // true - 点在五角星内部
star->contains({0, 0});    // false - 点在五角星外部
```

### onRevalidate() - 边界验证

```cpp
SkRect Path::onRevalidate(InvalidationController*, const SkMatrix&) {
    SkASSERT(this->hasInval());

    const auto ft = fPath.getFillType();
    return (ft == SkPathFillType::kWinding || ft == SkPathFillType::kEvenOdd)
        // "Containing" fills have finite bounds.
        ? fPath.computeTightBounds()
        // Inverse fills are "infinite".
        : SkRectPriv::MakeLargeS32();
}
```

**关键逻辑**：

1. **普通填充规则**（Winding/EvenOdd）：
   ```cpp
   fPath.computeTightBounds()
   ```
   - 计算紧凑边界框
   - 考虑所有路径点和控制点
   - 返回能包含整个路径的最小矩形

2. **逆向填充规则**（InverseWinding/InverseEvenOdd）：
   ```cpp
   SkRectPriv::MakeLargeS32()
   ```
   - 返回一个巨大的矩形（覆盖整个可表示空间）
   - 理由：逆向填充表示路径外部的区域，理论上是无限的

**填充规则说明**：
```cpp
// 普通填充 - 有限边界
SkPathFillType::kWinding      // 非零缠绕规则
SkPathFillType::kEvenOdd      // 奇偶规则

// 逆向填充 - 无限边界
SkPathFillType::kInverseWinding
SkPathFillType::kInverseEvenOdd
```

**示例**：
```cpp
// 圆形路径 - 普通填充
SkPath circle;
circle.addCircle(50, 50, 25);
circle.setFillType(SkPathFillType::kWinding);
// bounds = {25, 25, 75, 75}

// 圆形路径 - 逆向填充（绘制圆外的区域）
circle.setFillType(SkPathFillType::kInverseWinding);
// bounds = {-INT_MAX, -INT_MAX, INT_MAX, INT_MAX}
```

### onAsPath() - 路径转换

```cpp
SkPath Path::onAsPath() const {
    return fPath;
}
```

直接返回封装的 `SkPath` 对象的副本。这是最简单的实现，因为 Path 节点本身就存储路径数据。

**对比其他几何节点**：
- **Rect::onAsPath()**：需要将矩形转换为路径
- **Plane::onAsPath()**：返回逆向填充的空路径
- **Path::onAsPath()**：直接返回（最高效）

## 依赖关系

### 头文件依赖

```cpp
#include "modules/sksg/include/SkSGPath.h"  // 公共头文件
#include "include/core/SkCanvas.h"          // 画布绘制
#include "include/core/SkClipOp.h"          // 裁剪操作枚举
#include "include/core/SkPathTypes.h"       // 路径填充类型
#include "include/core/SkPoint.h"           // 点坐标
#include "include/private/base/SkAssert.h"  // 断言宏
#include "src/core/SkRectPriv.h"            // 私有矩形工具
```

### 类依赖关系

```
SkPath (Skia 核心路径类)
    ↓
SkSGPath (Scene Graph 路径节点)
    ↓
SkSGDraw (组合路径与绘制属性)
    ↓
SkSGGroup (容器节点)
    ↓
应用层 (Skottie/Viewer)
```

### 外部使用者

- **Skottie 动画系统**：从 Lottie JSON 数据生成路径节点
- **Merge 节点**：合并多个路径
- **Trim 节点**：裁剪路径的一部分

## 设计模式与设计决策

### 值语义设计

```cpp
private:
    SkPath fPath;  // 值成员，非指针
```

**优势**：
- 避免堆分配和指针管理
- 自动管理生命周期
- 简化复制和赋值语义

**代价**：
- `SkPath` 对象较大（约 64 字节）
- 复制开销较高

**权衡**：场景图节点通常不频繁复制，值语义的简洁性优于性能开销。

### 属性宏模式

```cpp
SG_ATTRIBUTE(Path, SkPath, fPath)
```

自动生成 getter 和 setter：
```cpp
// 展开为：
const SkPath& getPath() const { return fPath; }
void setPath(const SkPath& path) {
    if (fPath != path) {
        fPath = path;
        this->invalidate();  // 触发重新验证
    }
}
```

**好处**：
- 减少样板代码
- 确保修改时正确触发失效
- 统一的命名约定

### 边界计算策略

根据填充规则选择不同的边界计算策略：

```cpp
// 策略模式
if (is_normal_fill) {
    return compute_tight_bounds();  // 策略1：紧凑边界
} else {
    return infinite_bounds();       // 策略2：无限边界
}
```

这避免了为逆向填充路径计算无意义的紧凑边界。

### 委托模式

所有实际工作委托给 `SkPath`：

```cpp
void onDraw(...)     → fPath.draw()
bool onContains(...) → fPath.contains()
SkPath onAsPath()    → return fPath
```

Path 节点是 `SkPath` 的轻量包装，提供场景图接口。

## 性能考量

### 路径数据存储

`SkPath` 内部使用动态数组存储路径段：
- **内存**：根据路径复杂度动态调整（通常几百字节）
- **复制**：深拷贝所有路径数据
- **共享**：不支持写时复制（COW）

**优化建议**：
- 避免频繁修改路径数据
- 使用 `std::move` 传递大型路径

### 紧凑边界计算

```cpp
fPath.computeTightBounds()
```

**复杂度**：O(n)，遍历所有路径点和贝塞尔曲线控制点

**优化**：
- 结果在 `onRevalidate()` 中缓存
- 仅在路径修改后重新计算

**对比**：
- `getBounds()`：O(1) - 返回缓存的粗略边界
- `computeTightBounds()`：O(n) - 计算精确边界

### 点包含测试

```cpp
fPath.contains(x, y)
```

**复杂度**：O(n)，使用射线投射算法

**性能影响**：
- 简单路径（< 100 段）：可忽略
- 复杂路径（> 1000 段）：可能成为瓶颈

**优化策略**：
- 先测试边界框（快速拒绝）
- 使用简化的碰撞几何

### 裁剪开销

```cpp
canvas->clipPath(fPath, SkClipOp::kIntersect, antiAlias)
```

**代价**：
- GPU 后端：生成裁剪遮罩纹理
- CPU 后端：光栅化裁剪路径
- 抗锯齿裁剪额外增加 30-50% 开销

**优化**：
- 尽量使用矩形裁剪（更快）
- 避免嵌套复杂路径裁剪

## 相关文件

### 头文件

- **modules/sksg/include/SkSGPath.h** - Path 节点的公共接口
- **modules/sksg/include/SkSGGeometryNode.h** - 几何节点基类
- **include/core/SkPath.h** - Skia 核心路径类

### 实现文件

- **modules/sksg/src/SkSGRect.cpp** - 矩形几何节点
- **modules/sksg/src/SkSGPlane.cpp** - 平面几何节点
- **modules/sksg/src/SkSGMerge.cpp** - 路径合并节点
- **modules/sksg/src/SkSGGeometryEffect.cpp** - 路径效果节点

### 核心依赖

- **include/core/SkPath.h** - Skia 路径接口
- **include/core/SkCanvas.h** - Skia 画布接口
- **src/core/SkRectPriv.h** - 私有矩形工具

### 使用示例

```cpp
// 创建五角星路径
SkPath star_path;
star_path.moveTo(50, 0);
star_path.lineTo(61, 38);
star_path.lineTo(98, 38);
star_path.lineTo(68, 59);
star_path.lineTo(79, 98);
star_path.lineTo(50, 75);
star_path.lineTo(21, 98);
star_path.lineTo(32, 59);
star_path.lineTo(2, 38);
star_path.lineTo(39, 38);
star_path.close();

// 创建场景图节点
auto star_geo = Path::Make(star_path);
auto yellow_paint = Color::Make(SK_ColorYELLOW);
auto star_draw = Draw::Make(star_geo, yellow_paint);

// 添加描边
auto stroke_paint = Color::Make(SK_ColorBLACK);
stroke_paint->setStyle(SkPaint::kStroke_Style);
stroke_paint->setStrokeWidth(2);
auto star_stroke = Draw::Make(star_geo, stroke_paint);

// 组合
auto group = Group::Make();
group->addChild(star_draw);    // 填充
group->addChild(star_stroke);  // 描边
```
