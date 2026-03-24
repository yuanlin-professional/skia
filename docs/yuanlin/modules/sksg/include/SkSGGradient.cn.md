# SkSGGradient

> 源文件: modules/sksg/include/SkSGGradient.h

## 概述

SkSGGradient 模块定义了 Skia 场景图中的渐变着色器节点，提供线性渐变（LinearGradient）和径向渐变（RadialGradient）两种实现。渐变节点继承自 Shader 基类，可与 ShaderPaint 配合使用，为几何图形提供渐变填充或描边效果。

该模块实现了颜色在空间上的平滑过渡，支持多色阶渐变、不同的平铺模式以及动态修改渐变参数。渐变是矢量图形和现代 UI 设计中的核心视觉元素。

## 架构位置

在 Skia 场景图架构中的位置：

- **继承关系**:
  - Gradient → Shader → Node（推测）
  - LinearGradient → Gradient
  - RadialGradient → Gradient
- **功能定位**: 着色器节点，提供渐变填充能力
- **协作关系**: 与 ShaderPaint 组合，应用到几何节点
- **模块位置**: modules/sksg/include，场景图渲染效果模块

Gradient 是抽象基类，封装渐变的通用属性（色标、平铺模式），具体子类实现不同的渐变类型。

## 主要类与结构体

### ColorStop 结构体

```cpp
struct ColorStop {
    SkScalar  fPosition;  // 位置（0.0 - 1.0）
    SkColor4f fColor;     // 颜色（RGBA，浮点格式）

    bool operator==(const ColorStop& other) const;
};
```

定义渐变中的单个色标，包括位置和颜色。多个 ColorStop 定义渐变的颜色分布。

### Gradient 基类

```cpp
class Gradient : public Shader {
public:
    SG_ATTRIBUTE(ColorStops, std::vector<ColorStop>, fColorStops)
    SG_ATTRIBUTE(TileMode, SkTileMode, fTileMode)

protected:
    sk_sp<SkShader> onRevalidateShader() final;

    virtual sk_sp<SkShader> onMakeShader(
        const std::vector<SkColor4f>& colors,
        const std::vector<SkScalar>& positions) const = 0;

protected:
    Gradient() = default;

private:
    std::vector<ColorStop> fColorStops;
    SkTileMode             fTileMode = SkTileMode::kClamp;

    using INHERITED = Shader;
};
```

**关键成员**:
- `fColorStops`: 色标数组，定义渐变的颜色分布
- `fTileMode`: 平铺模式（Clamp、Repeat、Mirror、Decal）

### LinearGradient 类

```cpp
class LinearGradient final : public Gradient {
public:
    static sk_sp<LinearGradient> Make();

    SG_ATTRIBUTE(StartPoint, SkPoint, fStartPoint)
    SG_ATTRIBUTE(EndPoint, SkPoint, fEndPoint)

protected:
    sk_sp<SkShader> onMakeShader(
        const std::vector<SkColor4f>&,
        const std::vector<SkScalar>&) const override;

private:
    LinearGradient() = default;

    SkPoint fStartPoint = SkPoint::Make(0, 0);
    SkPoint fEndPoint   = SkPoint::Make(0, 0);

    using INHERITED = Gradient;
};
```

**关键成员**:
- `fStartPoint`: 渐变起点坐标
- `fEndPoint`: 渐变终点坐标

### RadialGradient 类

```cpp
class RadialGradient final : public Gradient {
public:
    static sk_sp<RadialGradient> Make();

    SG_ATTRIBUTE(StartCenter, SkPoint, fStartCenter)
    SG_ATTRIBUTE(EndCenter, SkPoint, fEndCenter)
    SG_ATTRIBUTE(StartRadius, SkScalar, fStartRadius)
    SG_ATTRIBUTE(EndRadius, SkScalar, fEndRadius)

protected:
    sk_sp<SkShader> onMakeShader(
        const std::vector<SkColor4f>&,
        const std::vector<SkScalar>&) const override;

private:
    RadialGradient() = default;

    SkPoint  fStartCenter = SkPoint::Make(0, 0);
    SkPoint  fEndCenter   = SkPoint::Make(0, 0);
    SkScalar fStartRadius = 0;
    SkScalar fEndRadius   = 0;

    using INHERITED = Gradient;
};
```

**关键成员**:
- `fStartCenter` / `fEndCenter`: 起始/结束圆心
- `fStartRadius` / `fEndRadius`: 起始/结束半径

支持双焦点径向渐变（two-point radial gradient）。

## 公共 API 函数

### Gradient 基类 API

#### getColorStops() / setColorStops()
```cpp
const std::vector<ColorStop>& getColorStops() const;
void setColorStops(const std::vector<ColorStop>& v);
void setColorStops(std::vector<ColorStop>&& v);
```
获取或设置渐变色标数组。

**使用示例**:
```cpp
gradient->setColorStops({
    {0.0f, SkColors::kRed},
    {0.5f, SkColors::kYellow},
    {1.0f, SkColors::kBlue}
});
```

#### getTileMode() / setTileMode()
```cpp
SkTileMode getTileMode() const;
void setTileMode(SkTileMode v);
```
设置平铺模式：
- `kClamp`: 边缘颜色延伸（默认）
- `kRepeat`: 重复渐变
- `kMirror`: 镜像重复
- `kDecal`: 边界外透明

### LinearGradient API

#### Make()
```cpp
static sk_sp<LinearGradient> Make();
```
创建线性渐变节点，初始为默认参数（起点和终点都为原点）。

#### getStartPoint() / setStartPoint()
```cpp
SkPoint getStartPoint() const;
void setStartPoint(const SkPoint& v);
```
设置渐变起点。

#### getEndPoint() / setEndPoint()
```cpp
SkPoint getEndPoint() const;
void setEndPoint(const SkPoint& v);
```
设置渐变终点。

**使用示例**:
```cpp
auto gradient = sksg::LinearGradient::Make();
gradient->setStartPoint(SkPoint::Make(0, 0));
gradient->setEndPoint(SkPoint::Make(100, 100));  // 左上到右下
gradient->setColorStops({{0, SK_ColorWHITE}, {1, SK_ColorBLACK}});
```

### RadialGradient API

#### Make()
```cpp
static sk_sp<RadialGradient> Make();
```
创建径向渐变节点。

#### StartCenter / EndCenter / StartRadius / EndRadius
通过 SG_ATTRIBUTE 宏生成的访问器，控制双焦点径向渐变参数。

**使用示例**:
```cpp
auto gradient = sksg::RadialGradient::Make();
gradient->setStartCenter(SkPoint::Make(50, 50));
gradient->setStartRadius(0);    // 从中心点开始
gradient->setEndCenter(SkPoint::Make(50, 50));
gradient->setEndRadius(50);     // 半径50的圆
gradient->setColorStops({{0, SK_ColorRED}, {1, SK_ColorBLUE}});
```

## 内部实现细节

### 着色器重验证 (onRevalidateShader)

Gradient 基类实现 onRevalidateShader()：
1. 从 fColorStops 提取颜色和位置到分离的数组
2. 调用子类的 onMakeShader() 创建具体着色器
3. 返回 SkShader 智能指针

这是模板方法模式，基类处理通用逻辑，子类实现特定逻辑。

### LinearGradient 着色器创建

```cpp
sk_sp<SkShader> LinearGradient::onMakeShader(...) const {
    SkPoint pts[2] = {fStartPoint, fEndPoint};
    return SkGradientShader::MakeLinear(
        pts, colors.data(), positions.data(),
        colors.size(), fTileMode
    );
}
```

调用 Skia 核心库的线性渐变着色器工厂。

### RadialGradient 着色器创建

```cpp
sk_sp<SkShader> RadialGradient::onMakeShader(...) const {
    return SkGradientShader::MakeTwoPointConical(
        fStartCenter, fStartRadius,
        fEndCenter, fEndRadius,
        colors.data(), positions.data(),
        colors.size(), fTileMode
    );
}
```

使用双焦点圆锥渐变（two-point conical gradient），可实现：
- 简单径向渐变（起点终点相同，起始半径为0）
- 复杂的焦点偏移渐变

### 色标验证和排序

实现中可能包含：
- 色标位置排序（确保单调递增）
- 位置范围检查（0.0 - 1.0）
- 处理重复位置（颜色突变）

### 失效机制

设置任何属性（色标、平铺模式、几何参数）都触发：
1. SG_ATTRIBUTE 宏调用 invalidate()
2. 节点标记为失效
3. 下次渲染前重新创建着色器

## 依赖关系

### 核心依赖
- **include/core/SkColor.h**: 颜色定义
- **include/core/SkPoint.h**: 点坐标
- **include/core/SkRefCnt.h**: 引用计数
- **include/core/SkScalar.h**: 标量类型
- **include/core/SkTileMode.h**: 平铺模式枚举

### 着色器依赖
- **SkShader**: Skia 着色器基类（前向声明）
- **SkGradientShader**: Skia 渐变着色器工厂（隐式依赖）

### 场景图依赖
- **modules/sksg/include/SkSGNode.h**: SG_ATTRIBUTE 宏
- **modules/sksg/include/SkSGRenderEffect.h**: Shader 基类

### 标准库
- **<vector>**: 色标和数组存储

## 设计模式与设计决策

### 1. 模板方法模式
Gradient 基类定义 onRevalidateShader() 流程，子类实现 onMakeShader()：
- 色标处理逻辑复用
- 子类专注于几何参数
- 扩展新渐变类型方便

### 2. 双焦点径向渐变
RadialGradient 使用双焦点设计：
- 更强大，可模拟简单径向渐变
- 支持焦点偏移的艺术效果
- 符合 SVG 和 CSS 规范

### 3. SkColor4f vs SkColor
使用浮点颜色格式：
- 更高精度（HDR 支持）
- 线性色彩空间插值更准确
- 现代图形 API 趋势

### 4. 终态子类
LinearGradient 和 RadialGradient 声明为 final：
- 渐变类型相对固定
- 简化虚函数调用
- 明确不可扩展

### 5. 默认参数
构造函数提供合理默认值：
- 起点终点为原点（需要显式设置）
- TileMode 为 Clamp（最常用）
- 简化初始化代码

## 性能考量

### 1. 着色器创建开销
每次失效都重新创建 SkShader：
- 涉及内存分配和初始化
- 色标数组拷贝
- 考虑缓存机制（Shader 基类可能实现）

### 2. 色标数量影响
更多色标增加渲染复杂度：
- GPU 需要更多插值计算
- 着色器编译更复杂
- 通常 2-5 个色标足够

### 3. 平铺模式性能
不同平铺模式开销不同：
- Clamp: 最快（边缘检测简单）
- Repeat/Mirror: 中等（需要取模运算）
- Decal: 可能略慢（额外透明度处理）

### 4. 渐变类型性能
- 线性渐变: 最快（简单线性插值）
- 径向渐变: 较慢（涉及距离计算）
- 现代 GPU 都有高效实现

### 5. 动画优化
频繁改变渐变参数：
- 每次改变触发着色器重建
- 考虑预计算关键帧
- GPU 纹理方式可能更高效（对于静态色标）

## 相关文件

### 头文件
- **modules/sksg/include/SkSGRenderEffect.h**: Shader 基类（推测）
- **modules/sksg/include/SkSGNode.h**: Node 基类和宏
- **modules/sksg/include/SkSGPaint.h**: ShaderPaint 节点

### 实现文件
- **modules/sksg/src/SkSGGradient.cpp**: Gradient 类实现

### Skia 核心库
- **include/effects/SkGradientShader.h**: Skia 渐变着色器工厂
- **include/core/SkShader.h**: 着色器基类

### 相关节点
- **SkSGPaint.h**: ShaderPaint 使用 Gradient
- **SkSGDraw.h**: 绘制节点组合几何和渐变

### 使用场景
- **modules/skottie**: Lottie 动画中的渐变填充
- UI 背景渐变
- 按钮和图标的渐变效果
- 数据可视化中的颜色映射

### 示例用法
```cpp
// 线性渐变填充矩形
auto rect = sksg::Rect::Make(SkRect::MakeXYWH(0, 0, 200, 100));
auto gradient = sksg::LinearGradient::Make();
gradient->setStartPoint(SkPoint::Make(0, 0));
gradient->setEndPoint(SkPoint::Make(200, 0));  // 水平渐变
gradient->setColorStops({
    {0.0f, SkColors::kRed},
    {1.0f, SkColors::kBlue}
});

auto shaderPaint = sksg::ShaderPaint::Make(gradient);
auto draw = sksg::Draw::Make(rect, shaderPaint);

// 径向渐变（放射状）
auto radial = sksg::RadialGradient::Make();
radial->setStartCenter(SkPoint::Make(100, 100));
radial->setStartRadius(0);
radial->setEndCenter(SkPoint::Make(100, 100));
radial->setEndRadius(100);
radial->setColorStops({
    {0.0f, SkColors::kWhite},
    {0.7f, SkColors::kYellow},
    {1.0f, SkColors::kRed}
});
radial->setTileMode(SkTileMode::kRepeat);

// 动画渐变
void animateGradient(float t) {
    gradient->setColorStops({
        {0.0f, interpolateColor(color1, color2, t)},
        {1.0f, interpolateColor(color3, color4, t)}
    });
}
```
