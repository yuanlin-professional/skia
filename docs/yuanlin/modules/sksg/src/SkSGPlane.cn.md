# SkSGPlane

> 源文件: modules/sksg/src/SkSGPlane.cpp

## 概述

SkSGPlane 是 Skia Scene Graph 中表示整个画布平面的几何节点实现。它是一个特殊的几何节点，代表无限大的绘制区域，常用于填充整个画布或作为背景层。与其他几何节点（如矩形、路径）不同，Plane 节点的边界覆盖整个可渲染空间，且任何点都被认为包含在其内部。

该实现非常轻量，仅包含 43 行代码，但在场景图渲染系统中扮演着重要的基础角色，尤其在需要全局背景或遮罩效果时。

## 架构位置

SkSGPlane 位于 Scene Graph 的几何节点层次结构中：

```
Skia Scene Graph 模块 (modules/sksg)
    ├── SkSGNode (所有节点基类)
    │
    ├── SkSGGeometryNode (几何节点基类)
    │   ├── SkSGRect (矩形几何)
    │   ├── SkSGPath (路径几何)
    │   ├── SkSGPlane (平面几何) ← 当前文件
    │   └── ... (其他几何节点)
    │
    └── SkSGRenderNode (渲染节点)
        └── SkSGDraw (组合几何与绘制)
```

在渲染管线中的位置：

```
应用层 (Skottie/Viewer)
    ↓
Scene Graph 构建
    ↓
Plane 节点 (代表整个画布)
    ↓
几何节点验证 (返回最大边界)
    ↓
渲染节点 (使用 drawPaint 绘制)
    ↓
Skia Canvas (SkCanvas::drawPaint)
```

## 主要类与结构体

### Plane

```cpp
class Plane final : public GeometryNode {
public:
    static sk_sp<Plane> Make() {
        return sk_sp<Plane>(new Plane());
    }

protected:
    Plane();

    // GeometryNode 接口实现
    void onClip(SkCanvas*, bool antiAlias) const override;
    void onDraw(SkCanvas*, const SkPaint&) const override;
    bool onContains(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;
    SkPath onAsPath() const override;

private:
    // 无成员变量 - 完全无状态
};
```

**类特点**：
- **final 类**：不能被继承，确保行为的确定性
- **无状态设计**：没有成员变量，所有行为由方法逻辑定义
- **单例语义**：所有 Plane 实例功能相同，可以复用

## 公共 API 函数

### Plane::Make()

```cpp
static sk_sp<Plane> Make();
```

工厂方法，创建一个新的 Plane 节点实例。返回智能指针管理的对象。

**使用示例**：
```cpp
auto background = Plane::Make();
auto draw = Draw::Make(background, color_paint);
```

### 继承的 GeometryNode 接口

从 `GeometryNode` 继承的公共接口：
- `void clip(SkCanvas*, bool)` - 应用裁剪
- `void draw(SkCanvas*, const SkPaint&)` - 绘制几何
- `bool contains(const SkPoint&)` - 点击测试
- `SkPath asPath()` - 转换为路径
- `SkRect revalidate(...)` - 验证并返回边界

## 内部实现细节

### 构造函数

```cpp
Plane::Plane() = default;
```

使用编译器生成的默认构造函数，因为 Plane 不需要任何初始化逻辑。这是最优的无状态对象实现方式。

### onClip() - 裁剪操作

```cpp
void Plane::onClip(SkCanvas*, bool) const {}
```

**空实现的理由**：
- Plane 代表无限平面，裁剪操作无意义
- 裁剪到无限区域等同于不裁剪
- 避免调用 `SkCanvas::clipRect()` 产生不必要的开销

实际场景中，如果需要裁剪效果，应该在 Plane 的父节点应用 ClipEffect。

### onDraw() - 绘制实现

```cpp
void Plane::onDraw(SkCanvas* canvas, const SkPaint& paint) const {
    canvas->drawPaint(paint);
}
```

**实现要点**：
- 使用 `drawPaint()` 而非 `drawRect()`
- `drawPaint()` 直接填充整个画布，忽略变换矩阵
- 这是绘制全局背景的最高效方式
- 传入的 `paint` 参数由 Draw 节点提供（来自 PaintNode）

**性能优势**：
- 避免了边界计算和变换
- GPU 后端可以优化为 clear 操作（特定条件下）
- 对于纯色填充，可能被优化为单条指令

### onContains() - 点包含测试

```cpp
bool Plane::onContains(const SkPoint&) const {
    return true;
}
```

**始终返回 true 的理由**：
- 无限平面包含所有点
- 用于点击测试和交互系统
- 简化了上层逻辑，避免特殊情况处理

**使用场景**：
```cpp
if (plane->contains(mouse_position)) {
    // 总是为 true，Plane 可以捕获所有点击事件
}
```

### onRevalidate() - 边界验证

```cpp
SkRect Plane::onRevalidate(InvalidationController*, const SkMatrix&) {
    SkASSERT(this->hasInval());
    return SkRect::MakeLTRB(SK_ScalarMin, SK_ScalarMin, SK_ScalarMax, SK_ScalarMax);
}
```

**实现细节**：
- 返回 Skia 中表示无限大矩形的常量
- `SK_ScalarMin` 和 `SK_ScalarMax` 是 SkScalar 类型的极值
- 断言确保验证流程的正确性
- 忽略传入的 `ctm`（坐标变换矩阵），因为无限大区域不受变换影响

**边界语义**：
```cpp
// 返回的矩形覆盖整个可表示的坐标空间
SkRect bounds = plane->revalidate(...);
// bounds.left()   == -FLT_MAX
// bounds.top()    == -FLT_MAX
// bounds.right()  == +FLT_MAX
// bounds.bottom() == +FLT_MAX
```

### onAsPath() - 路径转换

```cpp
SkPath Plane::onAsPath() const {
    SkPath path;
    path.setFillType(SkPathFillType::kInverseWinding);
    return path;
}
```

**设计精妙之处**：
- 返回一个**空路径**，但使用 `kInverseWinding` 填充类型
- 在 Skia 中，反转缠绕规则的空路径等同于整个平面
- 这是用路径语义表示无限区域的标准技巧

**填充规则说明**：
- 普通路径：定义的区域内为填充区
- 反转路径：定义的区域外为填充区
- 空路径 + 反转 = 整个平面都是填充区

**应用场景**：
```cpp
SkPath plane_path = plane->asPath();
canvas->clipPath(plane_path);  // 裁剪到整个平面（无效果）
```

## 依赖关系

### 头文件依赖

```cpp
#include "modules/sksg/include/SkSGPlane.h"  // 公共头文件
#include "include/core/SkCanvas.h"           // 画布绘制
#include "include/core/SkPath.h"             // 路径对象
#include "include/core/SkPathTypes.h"        // 路径填充类型
#include "include/core/SkScalar.h"           // 标量类型和极值常量
#include "include/private/base/SkAssert.h"   // 断言宏
```

### 类依赖关系图

```
SkSGNode (基类)
    ↓
SkSGGeometryNode (几何基类)
    ↓
SkSGPlane (平面节点)
    ↓
被 SkSGDraw 使用
    ↓
被 SkSGGroup 包含
    ↓
被 Skottie 动画系统使用
```

### 外部使用者

- **SkSGDraw**：组合 Plane 与 PaintNode 进行全画布绘制
- **Skottie**：用于实现纯色背景层
- **SkSG 测试代码**：验证几何节点接口的边界情况

## 设计模式与设计决策

### 工厂模式

```cpp
static sk_sp<Plane> Make();
```

**理由**：
- 强制使用智能指针管理生命周期
- 隐藏构造函数，防止栈分配
- 未来可以在工厂方法中添加对象池或单例逻辑

### 空对象模式

Plane 可以视为几何节点中的"空对象"：
- 提供完整的接口实现
- 但行为是平凡的（无限大、包含一切）
- 避免了空指针检查和特殊情况处理

**应用示例**：
```cpp
sk_sp<GeometryNode> geometry = use_plane ? Plane::Make() : Rect::Make(...);
// 后续代码无需判断类型，统一调用接口
geometry->draw(canvas, paint);
```

### 无状态设计

Plane 没有任何成员变量：
- 所有实例功能相同
- 线程安全（无共享状态）
- 可以高效复用

**优势**：
- 零内存开销（除了 vtable 指针）
- 验证操作无副作用
- 简化了序列化和调试

### Template Method 模式

继承自 `GeometryNode`，实现一系列 `on*()` 钩子方法：

```cpp
// 基类定义接口
class GeometryNode {
public:
    void draw(SkCanvas* canvas, const SkPaint& paint) const {
        this->onDraw(canvas, paint);  // 调用子类实现
    }

protected:
    virtual void onDraw(...) const = 0;  // 纯虚函数
};

// Plane 提供具体实现
class Plane : public GeometryNode {
protected:
    void onDraw(...) const override { canvas->drawPaint(paint); }
};
```

## 性能考量

### 内存占用

```cpp
sizeof(Plane) = sizeof(GeometryNode) ≈ 16 bytes
```

- 无成员变量，只有 vtable 指针和基类开销
- 可以创建大量实例而不担心内存问题

### 绘制性能

`drawPaint()` 是 Skia 中最高效的绘制调用之一：
- GPU 后端可能优化为 clear 操作
- 不需要顶点数据或几何处理
- 对于纯色，可以直接写入 framebuffer

**基准比较**（相对性能）：
```
drawPaint():      1.0x (基准)
drawRect():       1.2x (需要变换和裁剪)
drawPath():       1.5x (需要路径遍历)
```

### 边界计算开销

```cpp
return SkRect::MakeLTRB(SK_ScalarMin, SK_ScalarMin, SK_ScalarMax, SK_ScalarMax);
```

- 直接返回常量值，无计算开销
- 编译器可能内联为立即数加载
- 避免了变换矩阵乘法

### 点包含测试优化

```cpp
bool onContains(const SkPoint&) const { return true; }
```

- 常量时间 O(1) 复杂度
- 无分支，最优的 CPU 管线效率
- 相比之下，Path::contains() 需要射线投射算法

## 相关文件

### 头文件

- **modules/sksg/include/SkSGPlane.h** - Plane 节点的公共接口声明
- **modules/sksg/include/SkSGGeometryNode.h** - 几何节点基类定义

### 实现文件

- **modules/sksg/src/SkSGRect.cpp** - 矩形几何节点，功能类似但有限边界
- **modules/sksg/src/SkSGPath.cpp** - 路径几何节点，通用几何表示
- **modules/sksg/src/SkSGDraw.cpp** - 组合几何与绘制属性

### 测试文件

- **tests/SkSGTest.cpp** - Scene Graph 单元测试，验证 Plane 节点行为

### 核心依赖

- **include/core/SkCanvas.h** - Skia 画布绘制接口
- **include/core/SkPath.h** - Skia 路径对象
- **include/core/SkScalar.h** - 标量类型和常量定义

### 使用示例

```cpp
// 创建全画布背景
auto plane = Plane::Make();
auto bg_color = Color::Make(SK_ColorWHITE);
auto background = Draw::Make(plane, bg_color);

// 添加到场景图
auto root = Group::Make();
root->addChild(background);  // 背景层
root->addChild(content);     // 内容层
```
