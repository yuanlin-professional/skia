# SkSVGRadialGradient

> 源文件: modules/svg/src/SkSVGRadialGradient.cpp

## 概述

`SkSVGRadialGradient.cpp` 实现了 SVG 径向渐变（radial gradient）功能，支持从中心点向外辐射的圆形颜色过渡效果。该实现比线性渐变更复杂，支持可选的焦点（focal point）参数，可以创建偏心的圆锥形渐变。当焦点与中心点重合时使用标准径向渐变，否则使用双点圆锥渐变。实现仅 64 行代码，但涵盖了 SVG 径向渐变的完整语义。

## 架构位置

- **模块路径**: `modules/svg/src/`
- **对应头文件**: `modules/svg/include/SkSVGRadialGradient.h`
- **继承层次**: `SkSVGNode` → `SkSVGHiddenContainer` → `SkSVGGradient` → `SkSVGRadialGradient`
- **功能角色**: 径向渐变定义节点，生成径向或圆锥渐变着色器

## 主要类与结构体

### 实现的方法

1. **SkSVGRadialGradient()**: 构造函数
2. **parseAndSetAttribute()**: 解析径向渐变属性
3. **onMakeShader()**: 创建渐变着色器

## 公共 API 函数

### SkSVGRadialGradient::SkSVGRadialGradient()

构造函数。

```cpp
SkSVGRadialGradient::SkSVGRadialGradient() : INHERITED(SkSVGTag::kRadialGradient) {}
```

### bool parseAndSetAttribute(const char* name, const char* value)

解析径向渐变的几何属性。

```cpp
bool SkSVGRadialGradient::parseAndSetAttribute(const char* name, const char* value) {
    return INHERITED::parseAndSetAttribute(name, value) ||
           this->setCx(SkSVGAttributeParser::parse<SkSVGLength>("cx", name, value)) ||
           this->setCy(SkSVGAttributeParser::parse<SkSVGLength>("cy", name, value)) ||
           this->setR(SkSVGAttributeParser::parse<SkSVGLength>("r", name, value)) ||
           this->setFx(SkSVGAttributeParser::parse<SkSVGLength>("fx", name, value)) ||
           this->setFy(SkSVGAttributeParser::parse<SkSVGLength>("fy", name, value));
}
```

**支持的属性**:
- **cx, cy**: 渐变圆的中心点坐标（默认 50%, 50%）
- **r**: 渐变圆的半径（默认 50%）
- **fx, fy**: 渐变焦点坐标（默认等于 cx, cy）

## 内部实现细节

### sk_sp<SkShader> onMakeShader()

创建径向或圆锥渐变着色器。

```cpp
sk_sp<SkShader> SkSVGRadialGradient::onMakeShader(
    const SkSVGRenderContext& ctx,
    const SkColor4f* colors, const SkScalar* pos,
    int count, SkTileMode tm,
    const SkMatrix& m) const
{
    // 1. 确定长度上下文
    const SkSVGLengthContext lctx =
        this->getGradientUnits().type() == SkSVGObjectBoundingBoxUnits::Type::kObjectBoundingBox
            ? SkSVGLengthContext({1, 1})
            : ctx.lengthContext();

    // 2. 解析半径（使用 kOther 类型，对角线方向）
    const auto r = lctx.resolve(fR, SkSVGLengthContext::LengthType::kOther);

    // 3. 解析中心点
    const auto center = SkPoint::Make(
        lctx.resolve(fCx, SkSVGLengthContext::LengthType::kHorizontal),
        lctx.resolve(fCy, SkSVGLengthContext::LengthType::kVertical));

    // 4. 解析焦点（如果未指定，使用中心点）
    const auto focal = SkPoint::Make(
        fFx.has_value() ? lctx.resolve(*fFx, SkSVGLengthContext::LengthType::kHorizontal)
                        : center.x(),
        fFy.has_value() ? lctx.resolve(*fFy, SkSVGLengthContext::LengthType::kVertical)
                        : center.y());

    // 5. 退化情况：半径为 0，返回最后一个颜色
    if (r == 0) {
        const auto last_color = count > 0 ? colors[count - 1] : SkColors::kBlack;
        return SkShaders::Color(last_color, nullptr);
    }

    // 6. 准备位置数组
    SkSpan<const float> positions;
    if (pos) {
        positions = {pos, (size_t)count};
    }

    // 7. 创建渐变描述符
    SkGradient grad = {{{colors, (size_t)count}, positions, tm, nullptr}, {}};

    // 8. 根据焦点位置选择渐变类型
    return center == focal
        ? SkShaders::RadialGradient(center, r, grad, &m)        // 标准径向渐变
        : SkShaders::TwoPointConicalGradient(focal, 0, center, r, grad, &m);  // 圆锥渐变
}
```

### 关键实现细节

#### 焦点处理

焦点（focal point）创建偏心效果：

- **未指定 fx/fy**: 焦点默认等于中心点，创建对称径向渐变
- **指定 fx/fy**: 焦点偏离中心，创建偏心圆锥渐变

```cpp
const auto focal = SkPoint::Make(
    fFx.has_value() ? lctx.resolve(*fFx, ...) : center.x(),
    fFy.has_value() ? lctx.resolve(*fFy, ...) : center.y()
);
```

使用 `std::optional` (`has_value()`) 判断属性是否显式设置。

#### 半径解析

半径使用 `LengthType::kOther`：

```cpp
const auto r = lctx.resolve(fR, SkSVGLengthContext::LengthType::kOther);
```

对于 `kOther` 类型，百分比相对于视口对角线长度：

```
diagonal = sqrt(width² + height²) / sqrt(2)
```

这确保了在非正方形区域中渐变的圆形特性。

#### 退化情况处理

当半径为 0 时，渐变退化为单一颜色：

```cpp
if (r == 0) {
    const auto last_color = count > 0 ? colors[count - 1] : SkColors::kBlack;
    return SkShaders::Color(last_color, nullptr);
}
```

返回最后一个停止点的颜色，符合 SVG 规范。

#### 渐变类型选择

根据焦点和中心点是否重合选择着色器：

```cpp
return center == focal
    ? SkShaders::RadialGradient(center, r, grad, &m)  // 对称径向
    : SkShaders::TwoPointConicalGradient(focal, 0, center, r, grad, &m);  // 偏心圆锥
```

**TwoPointConicalGradient 参数**:
- 起点: 焦点，半径 0
- 终点: 中心点，半径 r
- 创建从焦点向外辐射到圆周的渐变

## 依赖关系

### Skia 核心依赖

- **include/effects/SkGradientShader.h**: 渐变着色器工厂
- **include/core/SkPoint.h**: 二维点类型
- **include/core/SkShader.h**: 着色器基类

### SVG 模块依赖

- **modules/svg/include/SkSVGRadialGradient.h**: 类声明
- **modules/svg/include/SkSVGGradient.h**: 渐变基类
- **modules/svg/include/SkSVGAttributeParser.h**: 属性解析
- **modules/svg/include/SkSVGRenderContext.h**: 渲染上下文

## 设计模式与设计决策

### 策略模式

根据几何参数动态选择渐变策略：

- **对称情况**: 使用高效的标准径向渐变
- **偏心情况**: 使用更通用的圆锥渐变

这种运行时选择优化了常见情况的性能。

### 可选参数处理

使用 `std::optional` 表示可选的焦点参数：

```cpp
std::optional<SkSVGLength> fFx;
std::optional<SkSVGLength> fFy;
```

**优势**:
- 明确区分"未指定"和"指定为 0"
- 符合 SVG 规范的默认值语义
- 类型安全

### 退化情况优雅处理

对于半径为 0 的退化情况，返回简单的颜色着色器而非抛出异常，保持渲染管道的鲁棒性。

## 性能考量

### 渐变类型开销

- **RadialGradient**: 优化的对称径向渐变，性能最佳
- **TwoPointConicalGradient**: 更通用但稍慢，处理偏心情况

代码通过比较焦点和中心点自动选择最优实现。

### GPU 加速

两种渐变类型都支持 GPU 加速：
- 编译为片段着色器
- 并行计算渐变值
- 利用 GPU 的三角函数单元

### 退化情况优化

半径为 0 时直接返回颜色着色器，避免不必要的渐变计算。

## 相关文件

### 头文件

- **modules/svg/include/SkSVGRadialGradient.h**: 类声明

### 基类

- **modules/svg/include/SkSVGGradient.h**: 渐变基类
- **modules/svg/src/SkSVGGradient.cpp**: 基类实现

### 相关渐变

- **modules/svg/src/SkSVGLinearGradient.cpp**: 线性渐变实现

### Skia 渐变

- **include/effects/SkGradientShader.h**: Skia 渐变接口
- **src/shaders/gradients/**: 渐变着色器实现

### 使用示例

**基本径向渐变**:
```xml
<radialGradient id="rad1">
  <stop offset="0%" stop-color="white"/>
  <stop offset="100%" stop-color="blue"/>
</radialGradient>
<circle cx="50" cy="50" r="40" fill="url(#rad1)"/>
```

**偏心渐变（高光效果）**:
```xml
<radialGradient id="spotlight" cx="50%" cy="50%" r="50%" fx="30%" fy="30%">
  <stop offset="0%" stop-color="yellow"/>
  <stop offset="100%" stop-color="darkred"/>
</radialGradient>
```

**自定义尺寸**:
```xml
<radialGradient id="custom" cx="100" cy="100" r="80">
  <stop offset="0%" stop-color="red"/>
  <stop offset="50%" stop-color="green"/>
  <stop offset="100%" stop-color="blue"/>
</radialGradient>
```

该实现完整支持 SVG 径向渐变规范，通过智能选择渐变类型实现了性能和功能的平衡。
