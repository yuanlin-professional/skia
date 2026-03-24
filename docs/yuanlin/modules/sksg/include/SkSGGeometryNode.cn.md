# SkSGGeometryNode

> 源文件: modules/sksg/include/SkSGGeometryNode.h

## 概述

SkSGGeometryNode 是 Skia 场景图系统中所有几何节点的抽象基类。它定义了几何图形的通用接口，包括绘制、裁剪、包含测试和路径转换等核心操作。GeometryNode 提供"绘制什么"的抽象，与 PaintNode（"如何绘制"）形成对偶关系。

该类是纯接口定义，不包含具体几何数据，所有方法都是纯虚函数。具体的几何类型（如矩形、路径、圆形等）继承此类并实现各自的几何逻辑。

## 架构位置

在 Skia 场景图架构中的位置：

- **继承关系**: GeometryNode → Node
- **派生类型**:
  - Path: 任意路径几何
  - Rect: 矩形几何
  - RRect: 圆角矩形
  - Circle: 圆形
  - Merge: 组合几何
- **协作关系**: 与 PaintNode 通过 Draw 节点组合使用
- **模块位置**: modules/sksg 核心模块

GeometryNode 是场景图几何系统的基石，定义了统一的几何抽象接口。

## 主要类与结构体

### GeometryNode 类

```cpp
class GeometryNode : public Node {
public:
    // 公共接口
    void clip(SkCanvas*, bool antiAlias) const;
    void draw(SkCanvas*, const SkPaint&) const;
    bool contains(const SkPoint&) const;
    SkPath asPath() const;

protected:
    GeometryNode();

    // 纯虚函数：子类必须实现
    virtual void onClip(SkCanvas*, bool antiAlias) const = 0;
    virtual void onDraw(SkCanvas*, const SkPaint&) const = 0;
    virtual bool onContains(const SkPoint&) const = 0;
    virtual SkPath onAsPath() const = 0;

private:
    friend class Draw;  // Draw 节点需要访问缓存边界

    using INHERITED = Node;
};
```

**设计特点**:
- 所有几何操作都有公共包装和虚函数实现
- 公共方法提供统一接口
- 虚函数允许子类优化实现

## 公共 API 函数

### clip()
```cpp
void clip(SkCanvas*, bool antiAlias) const;
```
将几何形状应用为画布裁剪区域。

**参数**:
- `SkCanvas*`: 目标画布
- `antiAlias`: 是否启用抗锯齿裁剪边缘

**用途**:
- 限制后续绘制的可见区域
- 创建复杂形状的视口
- 配合 ClipEffect 节点使用

**内部实现**: 调用 onClip() 虚函数

### draw()
```cpp
void draw(SkCanvas*, const SkPaint&) const;
```
使用指定的绘制属性绘制几何形状。

**参数**:
- `SkCanvas*`: 目标画布
- `const SkPaint&`: 绘制属性（颜色、描边、着色器等）

**用途**:
- 由 Draw 节点调用，组合几何和绘制属性
- 直接渲染几何形状

**内部实现**: 调用 onDraw() 虚函数

### contains()
```cpp
bool contains(const SkPoint&) const;
```
测试点是否在几何形状内部。

**参数**: 待测试的点坐标

**返回**: true 表示点在形状内，false 表示在外

**用途**:
- 命中测试（点击检测）
- 交互区域判断
- 拾取操作

**内部实现**: 调用 onContains() 虚函数

### asPath()
```cpp
SkPath asPath() const;
```
将几何形状转换为 SkPath 表示。

**返回**: 等价的 SkPath 对象

**用途**:
- 统一几何表示
- 路径布尔运算（Merge 节点）
- 高级路径操作
- 序列化和调试

**内部实现**: 调用 onAsPath() 虚函数

## 内部实现细节

### 纯虚函数设计

所有核心操作都定义为纯虚函数，强制子类实现：

#### onClip()
子类实现应调用适当的 SkCanvas 裁剪方法：
- 矩形: `canvas->clipRect()`
- 路径: `canvas->clipPath()`
- 圆角矩形: `canvas->clipRRect()`

#### onDraw()
子类实现应调用适当的 SkCanvas 绘制方法：
- 矩形: `canvas->drawRect()`
- 路径: `canvas->drawPath()`
- 圆形: `canvas->drawCircle()`

#### onContains()
子类实现通常：
- 简单几何: 直接数学计算（如点在矩形内）
- 复杂几何: 转换为路径后使用 SkPath::contains()

#### onAsPath()
子类实现构造等价的 SkPath：
- 矩形: `path.addRect()`
- 圆形: `path.addCircle()`
- 已是路径: 直接返回

### Draw 友元访问

Draw 类被声明为友元，可访问：
- 缓存的边界框（通过 Node::bounds()）
- 用于优化绘制决策（如视锥体剔除）

### 公共包装方法

公共方法（clip、draw、contains、asPath）提供：
- 统一的调用接口
- 未来可插入日志、性能追踪等
- 保持虚函数为 protected，封装实现细节

## 依赖关系

### 核心依赖
- **modules/sksg/include/SkSGNode.h**: Node 基类

### 前向声明
- **SkCanvas**: 画布（绘制和裁剪）
- **SkPaint**: 绘制属性
- **SkPath**: 路径表示
- **SkPoint**: 点坐标

### 被派生关系
- **SkSGPath**: 任意路径几何
- **SkSGRect**: 矩形几何
- **SkSGMerge**: 组合几何
- 其他具体几何类型

### 协作关系
- **SkSGDraw**: 组合 GeometryNode 和 PaintNode
- **SkSGClipEffect**: 使用几何作为裁剪
- **SkSGGeometryEffect**: 几何变换效果

## 设计模式与设计决策

### 1. 模板方法模式
公共方法定义接口框架，虚函数由子类实现：
- 统一的调用方式
- 灵活的实现扩展
- 封装变化点

### 2. 纯接口设计
所有核心方法都是纯虚函数：
- 强制子类实现完整功能
- 无默认行为（避免不正确的默认实现）
- 明确抽象基类的定位

### 3. 路径作为通用表示
asPath() 提供统一的几何表示：
- 任何几何都可转换为路径
- 支持通用算法和操作
- 简化跨几何类型的处理

### 4. 友元最小化
仅 Draw 类为友元：
- 精确控制访问权限
- Draw 是几何节点的主要使用者
- 避免过度暴露内部状态

### 5. 抗锯齿参数化
clip() 方法显式接受抗锯齿参数：
- 允许调用者控制质量/性能权衡
- 不同几何可能有不同的默认策略
- 明确而非隐式的行为

## 性能考量

### 1. 虚函数调用开销
所有操作都通过虚函数：
- 间接调用有一定成本
- 现代 CPU 分支预测减轻影响
- 灵活性价值超过开销

### 2. asPath() 转换成本
将几何转换为路径可能昂贵：
- 简单几何（矩形）转换快
- 复杂几何可能已存储为路径
- 考虑缓存转换结果（子类决定）

### 3. contains() 精度 vs 性能
包含测试实现策略：
- 快速边界框测试（粗略但快）
- 精确几何测试（准确但慢）
- 子类根据形状复杂度选择

### 4. 边界框缓存
Node 基类缓存边界框：
- 避免重复计算
- GeometryNode 复用该机制
- 只在失效时重新计算

### 5. 特化优化机会
子类可利用几何特性优化：
- 矩形裁剪比路径裁剪快
- 圆形包含测试为简单距离计算
- 特定几何的硬件加速路径

## 相关文件

### 头文件
- **modules/sksg/include/SkSGNode.h**: Node 基类定义
- **include/core/SkPath.h**: 路径 API
- **include/core/SkCanvas.h**: 画布 API
- **include/core/SkPaint.h**: 绘制属性

### 具体几何节点
- **SkSGPath.h**: 路径几何节点
- **SkSGRect.h**: 矩形几何节点
- **SkSGMerge.h**: 组合几何节点
- **SkSGPlane.h**: 平面几何（可能）

### 使用节点
- **SkSGDraw.h**: 组合几何和绘制
- **SkSGClipEffect.h**: 几何裁剪效果
- **SkSGGeometryEffect.h**: 几何变换效果

### 实现文件
- **modules/sksg/src/SkSGGeometryNode.cpp**: GeometryNode 实现

### 使用场景
- **modules/skottie**: Lottie 动画中的形状层
- 矢量图形渲染
- 2D 游戏中的碰撞检测
- UI 图形绘制

### 示例用法
```cpp
// 通过 Draw 节点组合几何和绘制
auto rect = sksg::Rect::Make(SkRect::MakeXYWH(10, 10, 100, 50));
auto paint = sksg::Color::Make(SK_ColorRED);
auto draw = sksg::Draw::Make(rect, paint);

// 使用几何作为裁剪
auto circle = sksg::Circle::Make(center, radius);
circle->clip(canvas, true);  // 抗锯齿裁剪

// 包含测试
if (rect->contains(clickPoint)) {
    // 处理点击事件
}

// 转换为路径用于布尔运算
SkPath rectPath = rect->asPath();
```
