# SkSGPaint

> 源文件: modules/sksg/include/SkSGPaint.h

## 概述

SkSGPaint 模块为 Skia 场景图（Scene Graph）系统提供绘制属性节点的抽象和实现。该模块定义了绘制相关的节点类型，包括基础的 PaintNode 抽象类以及具体的 Color 和 ShaderPaint 实现。这些节点负责为几何图形提供颜色、着色器等绘制属性，类似于 Skia 核心库中的 SkPaint 功能。

PaintNode 封装了抗锯齿、不透明度、混合模式、描边等常见的绘制属性，并通过虚函数允许子类定制具体的绘制行为。Color 节点提供纯色填充能力，而 ShaderPaint 节点则支持更复杂的着色器效果（如渐变、图案等）。

## 架构位置

在 Skia 场景图架构中，SkSGPaint 位于节点层次结构的重要位置：

- **继承关系**: PaintNode 继承自 sksg::Node 基类，是场景图节点系统的一部分
- **模块位置**: 位于 modules/sksg 模块，属于 Skottie 动画引擎的场景图实现
- **协作关系**: 与 GeometryNode（几何节点）配合使用，通过 Draw 节点将几何和绘制属性组合
- **依赖关系**: 依赖于 Skia 核心库的 SkPaint、SkColor、SkBlendMode 等类型

该模块是场景图绘制系统的核心组件，提供了描述"如何绘制"的抽象，而 GeometryNode 提供"绘制什么"的抽象。

## 主要类与结构体

### PaintNode 类

抽象基类，为所有绘制节点提供通用功能：

```cpp
class PaintNode : public Node {
public:
    SkPaint makePaint() const;

    // 属性访问器（通过 SG_ATTRIBUTE 宏定义）
    SG_ATTRIBUTE(AntiAlias, bool, fAntiAlias)
    SG_ATTRIBUTE(Opacity, SkScalar, fOpacity)
    SG_ATTRIBUTE(BlendMode, SkBlendMode, fBlendMode)
    SG_ATTRIBUTE(StrokeWidth, SkScalar, fStrokeWidth)
    SG_ATTRIBUTE(StrokeMiter, SkScalar, fStrokeMiter)
    SG_ATTRIBUTE(Style, SkPaint::Style, fStyle)
    SG_ATTRIBUTE(StrokeJoin, SkPaint::Join, fStrokeJoin)
    SG_ATTRIBUTE(StrokeCap, SkPaint::Cap, fStrokeCap)

protected:
    virtual void onApplyToPaint(SkPaint*) const = 0;
};
```

**关键成员**:
- `fOpacity`: 不透明度（默认 1.0）
- `fAntiAlias`: 抗锯齿开关（默认 false）
- `fBlendMode`: 混合模式（默认 kSrcOver）
- `fStyle`: 绘制样式（填充或描边，默认填充）
- `fStrokeWidth`: 描边宽度（默认 1.0）
- `fStrokeMiter`: 斜接限制（默认 4.0）
- `fStrokeJoin`: 描边连接方式（默认斜接）
- `fStrokeCap`: 描边端点样式（默认平头）

### Color 类

具体实现，封装纯色绘制：

```cpp
class Color : public PaintNode {
public:
    static sk_sp<Color> Make(SkColor c);
    SG_ATTRIBUTE(Color, SkColor, fColor)

protected:
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;
    void onApplyToPaint(SkPaint*) const override;

private:
    explicit Color(SkColor);
    SkColor fColor;
};
```

### ShaderPaint 类

支持着色器的绘制节点：

```cpp
class ShaderPaint final : public PaintNode {
public:
    static sk_sp<ShaderPaint> Make(sk_sp<Shader>);

protected:
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;
    void onApplyToPaint(SkPaint*) const override;

private:
    explicit ShaderPaint(sk_sp<Shader>);
    const sk_sp<Shader> fShader;
};
```

## 公共 API 函数

### PaintNode::makePaint()
```cpp
SkPaint makePaint() const;
```
创建并返回配置好的 SkPaint 对象，包含所有设置的属性。该方法会调用 `onApplyToPaint()` 让子类应用特定的绘制属性。

### Color::Make()
```cpp
static sk_sp<Color> Make(SkColor c);
```
静态工厂方法，创建纯色绘制节点。参数 `c` 指定颜色值。

### ShaderPaint::Make()
```cpp
static sk_sp<ShaderPaint> Make(sk_sp<Shader>);
```
静态工厂方法，创建着色器绘制节点。参数为 sksg::Shader 智能指针。

### 属性访问器

通过 SG_ATTRIBUTE 宏生成的 getter/setter 方法：
- `getAntiAlias()/setAntiAlias()`: 控制抗锯齿
- `getOpacity()/setOpacity()`: 控制不透明度（0.0-1.0）
- `getBlendMode()/setBlendMode()`: 设置混合模式
- `getStrokeWidth()/setStrokeWidth()`: 设置描边宽度
- `getStyle()/setStyle()`: 设置填充或描边样式
- 其他描边相关属性访问器

## 内部实现细节

### 属性宏机制

使用 SG_ATTRIBUTE 宏简化属性的声明和实现：
```cpp
#define SG_ATTRIBUTE(attr_name, attr_type, attr_container)
```
该宏自动生成：
- `get##attr_name()`: 返回属性的常量引用
- `set##attr_name(const attr_type&)`: 设置属性并触发失效
- `set##attr_name(attr_type&&)`: 移动语义版本

设置属性时会自动调用 `this->invalidate()` 标记节点需要重新验证，触发场景图的增量更新机制。

### 虚函数模板方法

PaintNode 使用模板方法模式：
- `makePaint()` 公共方法构造 SkPaint 并设置通用属性
- 调用纯虚函数 `onApplyToPaint()` 让子类应用特定属性
- Color 子类在 `onApplyToPaint()` 中设置颜色
- ShaderPaint 子类设置着色器

### 重验证机制

两个具体类都重写 `onRevalidate()` 方法：
- Color 节点通常返回空边界框（因为颜色本身没有几何信息）
- ShaderPaint 依赖着色器节点的边界

## 依赖关系

### 外部依赖
- **include/core/SkBlendMode.h**: 混合模式枚举
- **include/core/SkColor.h**: 颜色定义
- **include/core/SkPaint.h**: Skia 绘制对象
- **include/core/SkRect.h**: 矩形边界
- **include/core/SkRefCnt.h**: 引用计数基类
- **include/core/SkScalar.h**: 标量类型

### 内部依赖
- **modules/sksg/include/SkSGNode.h**: 场景图节点基类
- **sksg::Shader**: 着色器节点（前向声明）
- **sksg::InvalidationController**: 失效控制器

### 被依赖关系
- 被 skottie::internal::AnimationBuilder 使用（通过友元访问）
- 被 Draw 节点引用，组合几何和绘制属性
- 被动画系统用于动态修改绘制属性

## 设计模式与设计决策

### 1. 模板方法模式
PaintNode 定义 `makePaint()` 框架，子类通过 `onApplyToPaint()` 定制行为。这确保了通用属性处理的一致性，同时允许特定绘制逻辑的灵活性。

### 2. 工厂方法模式
Color 和 ShaderPaint 都提供静态 Make() 方法，隐藏构造细节，返回智能指针，确保对象始终通过引用计数管理。

### 3. 属性宏抽象
SG_ATTRIBUTE 宏减少样板代码，统一属性访问模式，并自动集成失效机制。这是对大量属性的高效管理方式。

### 4. 不可变着色器引用
ShaderPaint 中的 fShader 成员声明为 const，防止着色器在节点生命周期内被替换。这简化了依赖跟踪和失效逻辑。

### 5. 组合优于继承
绘制节点持有 Shader 对象而非继承，提供更灵活的着色器组合能力。

### 6. 友元访问控制
Color 类将 AnimationBuilder 声明为友元，允许动画系统直接构造节点而不暴露构造函数，保持了封装性。

## 性能考量

### 1. 延迟计算
SkPaint 对象通过 `makePaint()` 按需创建，而非预先存储。这减少了内存占用，但需要注意在渲染循环中重复调用的开销。

### 2. 属性比较优化
SG_ATTRIBUTE 宏在设置新值前会检查值是否改变（`if (attr_container == v) return;`），避免不必要的失效通知。

### 3. 引用计数开销
使用 sk_sp 智能指针管理生命周期，涉及引用计数操作。对于频繁创建销毁的场景，可能产生性能影响。

### 4. 虚函数调用
`onApplyToPaint()` 和 `onRevalidate()` 的虚函数调用在热路径上可能影响性能，但提供的灵活性通常值得这个代价。

### 5. 着色器共享
ShaderPaint 持有 Shader 的智能指针，支持多个绘制节点共享同一着色器实例，减少内存和计算开销。

## 相关文件

### 头文件
- **modules/sksg/include/SkSGNode.h**: 节点基类定义
- **modules/sksg/include/SkSGRenderEffect.h**: Shader 节点定义
- **modules/sksg/include/SkSGGeometryNode.h**: 几何节点定义

### 实现文件
- **modules/sksg/src/SkSGPaint.cpp**: PaintNode、Color、ShaderPaint 的实现

### 使用示例
- **modules/skottie**: Lottie 动画引擎中的绘制属性动画
- **modules/sksg/include/SkSGDraw.h**: 组合几何和绘制节点

### 相关节点
- **SkSGGradient.h**: 渐变着色器实现
- **SkSGGroup.h**: 组合多个渲染节点
- **SkSGRenderNode.h**: 渲染节点基类
