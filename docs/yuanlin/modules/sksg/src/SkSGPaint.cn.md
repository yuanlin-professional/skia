# SkSGPaint

> 源文件: modules/sksg/src/SkSGPaint.cpp

## 概述

SkSGPaint 是 Skia Scene Graph (SG) 模块中负责绘制属性（如颜色、着色器等）的节点实现。该文件提供了场景图中所有绘制相关节点的基础类和具体实现，包括 `PaintNode` 基类、`Color` 纯色节点以及 `ShaderPaint` 着色器节点。这些节点不直接产生几何形状，而是为几何节点提供绘制样式和属性。

Paint 节点在场景图中扮演着类似 Skia `SkPaint` 的角色，封装了抗锯齿、混合模式、描边样式等绘制属性，并通过观察者模式实现属性变化的自动失效传播。

## 架构位置

SkSGPaint 位于 Skia 的 Scene Graph 模块 (`modules/sksg`) 中，处于场景图渲染管线的属性层：

```
Skia 核心库 (include/core)
    ├── SkPaint (底层绘制属性)
    └── SkShader (着色器)
         ↓
Scene Graph 模块 (modules/sksg)
    ├── SkSGNode (节点基类)
    ├── SkSGPaint.cpp (绘制属性节点) ← 当前文件
    │   ├── PaintNode (抽象基类)
    │   ├── Color (纯色实现)
    │   └── ShaderPaint (着色器实现)
    ├── SkSGRenderNode (渲染节点)
    └── SkSGDraw (组合几何与绘制)
         ↓
上层应用 (modules/skottie)
    └── AnimationBuilder (动画构建器)
```

该文件通过继承 `Node` 基类并实现特定的绘制逻辑，为场景图提供了可组合的绘制属性系统。

## 主要类与结构体

### PaintNode

绘制节点的抽象基类，提供所有绘制属性的通用接口：

```cpp
class PaintNode : public Node {
protected:
    PaintNode();  // 构造函数，设置 kBubbleDamage_Trait 特性

public:
    SkPaint makePaint() const;  // 生成 SkPaint 对象
    virtual void onApplyToPaint(SkPaint*) const = 0;  // 子类实现具体属性应用

private:
    // 绘制属性成员
    SkScalar fOpacity;      // 不透明度 (默认 1)
    SkScalar fStrokeWidth;  // 描边宽度 (默认 1)
    SkScalar fStrokeMiter;  // 斜接限制 (默认 4)
    bool fAntiAlias;        // 抗锯齿 (默认 false)
    SkBlendMode fBlendMode; // 混合模式 (默认 kSrcOver)
    SkPaint::Style fStyle;  // 绘制样式 (默认 kFill_Style)
    SkPaint::Join fStrokeJoin;  // 描边连接方式
    SkPaint::Cap fStrokeCap;    // 描边端点样式
};
```

**关键特性**：
- 使用 `kBubbleDamage_Trait` 特性，表示损坏信息向上冒泡传递
- 不自行生成损坏区域，而是通过聚合的 Draw 节点产生损坏

### Color

纯色绘制节点的具体实现：

```cpp
class Color : public PaintNode {
public:
    static sk_sp<Color> Make(SkColor c);  // 工厂方法

    SG_ATTRIBUTE(Color, SkColor, fColor)  // 颜色属性宏定义

protected:
    explicit Color(SkColor c);
    SkRect onRevalidate(InvalidationController* ic, const SkMatrix& ctm) override;
    void onApplyToPaint(SkPaint* paint) const override;

private:
    SkColor fColor;  // 存储的 ARGB 颜色值
};
```

### ShaderPaint

基于着色器的绘制节点实现：

```cpp
class ShaderPaint final : public PaintNode {
public:
    static sk_sp<ShaderPaint> Make(sk_sp<Shader> sh);
    ~ShaderPaint() override;

protected:
    explicit ShaderPaint(sk_sp<Shader> sh);
    SkRect onRevalidate(InvalidationController* ic, const SkMatrix& ctm) override;
    void onApplyToPaint(SkPaint* paint) const override;

private:
    const sk_sp<Shader> fShader;  // 持有的着色器对象
};
```

## 公共 API 函数

### PaintNode::makePaint()

```cpp
SkPaint PaintNode::makePaint() const;
```

生成最终的 `SkPaint` 对象，用于实际绘制操作。该方法：
1. 创建新的 `SkPaint` 实例
2. 应用所有通用属性（抗锯齿、混合模式、描边等）
3. 调用 `onApplyToPaint()` 让子类应用特定属性
4. 将不透明度合成到 alpha 通道中

**注意**：方法内部使用 `SkASSERT(!this->hasInval())` 确保节点状态已经验证。

### Color::Make()

```cpp
static sk_sp<Color> Make(SkColor c);
```

创建纯色绘制节点的工厂方法。参数 `c` 是一个 32 位 ARGB 颜色值。

**使用示例**：
```cpp
auto red_paint = Color::Make(SK_ColorRED);
red_paint->setOpacity(0.5f);  // 设置半透明
```

### ShaderPaint::Make()

```cpp
static sk_sp<ShaderPaint> Make(sk_sp<Shader> sh);
```

创建着色器绘制节点的工厂方法。如果传入的着色器为空，返回 `nullptr`。该节点会自动注册为着色器的观察者，当着色器发生变化时会触发重新验证。

## 内部实现细节

### 不透明度合成机制

在 `makePaint()` 中，不透明度被合成到最终的 alpha 值：

```cpp
paint.setAlpha(SkScalarRoundToInt(paint.getAlpha() * SkTPin<SkScalar>(fOpacity, 0, 1)));
```

- 使用 `SkTPin` 将不透明度限制在 [0, 1] 范围
- 与子类设置的 alpha 值相乘，实现合成效果
- 四舍五入转换为整数 alpha 值

### 观察者模式实现

`ShaderPaint` 通过观察者模式跟踪着色器变化：

```cpp
ShaderPaint::ShaderPaint(sk_sp<Shader> sh) : fShader(std::move(sh)) {
    this->observeInval(fShader);  // 注册观察
}

ShaderPaint::~ShaderPaint() {
    this->unobserveInval(fShader);  // 注销观察
}
```

当着色器的 `revalidate()` 被调用时，`ShaderPaint` 会收到失效通知并触发自身的重新验证。

### 失效验证流程

`Color` 的验证逻辑非常简单：

```cpp
SkRect Color::onRevalidate(InvalidationController* ic, const SkMatrix& ctm) {
    SkASSERT(this->hasInval());
    return SkRect::MakeEmpty();  // 纯色不占用空间
}
```

而 `ShaderPaint` 需要传播验证到着色器：

```cpp
SkRect ShaderPaint::onRevalidate(InvalidationController* ic, const SkMatrix& ctm) {
    SkASSERT(this->hasInval());
    return fShader->revalidate(ic, ctm);  // 委托给着色器
}
```

### 属性应用钩子

子类通过 `onApplyToPaint()` 实现特定的属性设置：

```cpp
// Color 实现
void Color::onApplyToPaint(SkPaint* paint) const {
    paint->setColor(fColor);
}

// ShaderPaint 实现
void ShaderPaint::onApplyToPaint(SkPaint* paint) const {
    paint->setShader(fShader->getShader());
}
```

这种设计允许基类和子类的属性协同工作，基类负责通用属性，子类负责特定属性。

## 依赖关系

### 头文件依赖

```cpp
#include "include/core/SkShader.h"          // Skia 着色器
#include "include/private/base/SkAssert.h"  // 断言宏
#include "include/private/base/SkTPin.h"    // 值钳位工具
#include "modules/sksg/include/SkSGPaint.h" // 公共头文件
#include "modules/sksg/include/SkSGRenderEffect.h"  // 渲染效果（Shader 定义）
```

### 模块依赖关系

- **向下依赖**：依赖 Skia 核心的 `SkPaint`、`SkShader` 和 `SkColor`
- **向上依赖**：被 `SkSGDraw` 节点使用，用于组合几何和绘制属性
- **横向依赖**：与 `SkSGRenderEffect` 模块协作（Shader 基类定义在那里）

### 外部使用者

- **Skottie 动画系统**：通过 `AnimationBuilder` 创建和动画化 Color 节点
- **Scene Graph 绘制系统**：Draw 节点使用 PaintNode 生成 `SkPaint` 进行渲染

## 设计模式与设计决策

### 模板方法模式

`PaintNode::makePaint()` 使用模板方法模式：

```cpp
SkPaint PaintNode::makePaint() const {
    SkPaint paint;
    // 基类设置通用属性
    paint.setAntiAlias(fAntiAlias);
    paint.setBlendMode(fBlendMode);
    // ...

    // 调用子类钩子
    this->onApplyToPaint(&paint);

    // 后处理（不透明度合成）
    paint.setAlpha(...);
    return paint;
}
```

这确保了通用属性和特定属性的正确组合顺序。

### 工厂模式

所有具体类都提供静态工厂方法 `Make()`，返回 `sk_sp<T>` 智能指针：

```cpp
static sk_sp<Color> Make(SkColor c);
static sk_sp<ShaderPaint> Make(sk_sp<Shader> sh);
```

**优势**：
- 隐藏构造函数，强制使用智能指针管理生命周期
- 允许在创建时进行有效性检查（如 `ShaderPaint::Make` 检查空指针）
- 统一的创建接口

### 观察者模式

`ShaderPaint` 作为观察者监听 `Shader` 的变化：

```cpp
this->observeInval(fShader);   // 注册
this->unobserveInval(fShader); // 注销
```

这实现了自动失效传播，无需手动管理依赖关系。

### Bubble Damage 设计决策

Paint 节点使用 `kBubbleDamage_Trait` 特性：

```cpp
PaintNode::PaintNode() : INHERITED(kBubbleDamage_Trait) {}
```

**理由**：Paint 节点本身不产生几何区域，只有当与几何节点组合（通过 Draw 节点）时才会影响屏幕。因此损坏区域应该由聚合的祖先节点计算和传播。

## 性能考量

### 不透明度计算优化

```cpp
paint.setAlpha(SkScalarRoundToInt(paint.getAlpha() * SkTPin<SkScalar>(fOpacity, 0, 1)));
```

- 使用 `SkTPin` 进行高效的范围限制（通常编译为条件移动指令）
- 乘法和取整操作合并为单次计算
- 避免了不必要的条件分支

### 智能指针开销

使用 `sk_sp<T>` 智能指针管理生命周期：
- **优点**：自动内存管理，线程安全的引用计数
- **开销**：每次复制/移动涉及原子操作
- **优化**：在构造函数中使用 `std::move` 避免不必要的引用计数操作

```cpp
ShaderPaint::ShaderPaint(sk_sp<Shader> sh) : fShader(std::move(sh)) { ... }
```

### 失效传播效率

Paint 节点的验证操作非常轻量：
- `Color::onRevalidate()` 仅返回空矩形，几乎无开销
- `ShaderPaint::onRevalidate()` 仅转发调用到着色器
- 不执行复杂的几何计算或内存分配

### 缓存策略

`ShaderPaint` 中的着色器对象被缓存：

```cpp
const sk_sp<Shader> fShader;  // const 成员，不可更改
```

一旦创建，着色器引用不会改变，避免了重复查找和解析的开销。对于需要动态更改的场景，应该创建新的 `ShaderPaint` 节点或修改着色器节点内部的参数。

## 相关文件

- **include/core/SkPaint.h** - Skia 核心绘制类
- **include/core/SkShader.h** - Skia 着色器基类
- **modules/sksg/include/SkSGPaint.h** - 本文件的公共头文件
- **modules/sksg/include/SkSGNode.h** - 场景图节点基类
- **modules/sksg/include/SkSGRenderEffect.h** - 渲染效果和着色器节点定义
- **modules/sksg/src/SkSGDraw.cpp** - Draw 节点，组合几何和绘制属性
- **modules/skottie/src/Skottie.cpp** - Lottie 动画系统，使用 Paint 节点
