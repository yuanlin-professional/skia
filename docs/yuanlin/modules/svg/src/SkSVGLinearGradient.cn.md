# SkSVGLinearGradient

> 源文件: modules/svg/src/SkSVGLinearGradient.cpp

## 概述

`SkSVGLinearGradient.cpp` 实现了 SVG 线性渐变的具体功能。线性渐变在两个点之间创建平滑的颜色过渡，是 SVG 中最常用的填充效果之一。该实现继承自 `SkSVGGradient` 基类，专门处理线性渐变的几何参数（起点和终点），并使用 Skia 的 `SkShaders::LinearGradient` 创建渐变着色器。实现简洁高效，只有53行代码，展示了如何将 SVG 渐变定义转换为 Skia 的渲染原语。

## 架构位置

- **模块路径**: `modules/svg/src/`
- **对应头文件**: `modules/svg/include/SkSVGLinearGradient.h`
- **继承层次**: `SkSVGNode` → `SkSVGHiddenContainer` → `SkSVGGradient` → `SkSVGLinearGradient`
- **功能角色**: 渐变定义节点，生成线性渐变着色器

## 主要类与结构体

该文件实现 `SkSVGLinearGradient` 的三个核心方法。

### 实现的方法

1. **SkSVGLinearGradient()**: 构造函数
2. **parseAndSetAttribute()**: 解析属性
3. **onMakeShader()**: 创建渐变着色器

## 公共 API 函数

### SkSVGLinearGradient::SkSVGLinearGradient()

构造函数，初始化为线性渐变类型。

```cpp
SkSVGLinearGradient::SkSVGLinearGradient() : INHERITED(SkSVGTag::kLinearGradient) {}
```

### bool parseAndSetAttribute(const char* name, const char* value)

解析线性渐变的几何属性。

```cpp
bool SkSVGLinearGradient::parseAndSetAttribute(const char* name, const char* value) {
    return INHERITED::parseAndSetAttribute(name, value) ||
           this->setX1(SkSVGAttributeParser::parse<SkSVGLength>("x1", name, value)) ||
           this->setY1(SkSVGAttributeParser::parse<SkSVGLength>("y1", name, value)) ||
           this->setX2(SkSVGAttributeParser::parse<SkSVGLength>("x2", name, value)) ||
           this->setY2(SkSVGAttributeParser::parse<SkSVGLength>("y2", name, value));
}
```

**支持的属性**:
- **x1, y1**: 渐变起点坐标
- **x2, y2**: 渐变终点坐标

**默认值**（SVG 规范）: x1=0%, y1=0%, x2=100%, y2=0%（水平渐变）

## 内部实现细节

### sk_sp<SkShader> onMakeShader()

创建 Skia 线性渐变着色器。

```cpp
sk_sp<SkShader> SkSVGLinearGradient::onMakeShader(
    const SkSVGRenderContext& ctx,
    const SkColor4f* colors, const SkScalar* pos,
    int count, SkTileMode tm,
    const SkMatrix& localMatrix) const
{
    // 1. 确定长度上下文
    const SkSVGLengthContext lctx =
        this->getGradientUnits().type() == SkSVGObjectBoundingBoxUnits::Type::kObjectBoundingBox
            ? SkSVGLengthContext({1, 1})  // 对象边界框：0-1范围
            : ctx.lengthContext();         // 用户空间：实际坐标

    // 2. 解析端点坐标
    const auto x1 = lctx.resolve(fX1, SkSVGLengthContext::LengthType::kHorizontal);
    const auto y1 = lctx.resolve(fY1, SkSVGLengthContext::LengthType::kVertical);
    const auto x2 = lctx.resolve(fX2, SkSVGLengthContext::LengthType::kHorizontal);
    const auto y2 = lctx.resolve(fY2, SkSVGLengthContext::LengthType::kVertical);

    // 3. 构造端点数组
    const SkPoint pts[2] = { {x1, y1}, {x2, y2} };

    // 4. 准备位置数组（可选）
    SkSpan<const float> positions;
    if (pos) {
        positions = {pos, (size_t)count};
    }

    // 5. 创建渐变描述符
    SkGradient grad = {{{colors, (size_t)count}, positions, tm, nullptr}, {}};

    // 6. 创建线性渐变着色器
    return SkShaders::LinearGradient(pts, grad, &localMatrix);
}
```

### 关键实现细节

#### 坐标系统处理

根据 `gradientUnits` 属性选择长度上下文：

- **objectBoundingBox**: 使用 1×1 的虚拟视口，坐标 0-1 映射到对象边界框
- **userSpaceOnUse**: 使用当前的用户空间坐标系统

#### 端点定义

线性渐变由两个点定义渐变方向和范围：
- 起点 (x1, y1): 颜色数组中第一个颜色的位置
- 终点 (x2, y2): 最后一个颜色的位置

#### 颜色和位置

- **colors**: 渐变停止点的颜色数组（由基类收集）
- **pos**: 每个颜色的位置（0.0-1.0范围），可选
- 如果 `pos` 为空，颜色均匀分布

#### 平铺模式

`SkTileMode tm` 定义渐变范围外的行为：
- **kClamp**: 延伸端点颜色
- **kRepeat**: 重复渐变
- **kMirror**: 镜像重复

#### 局部变换矩阵

`localMatrix` 应用渐变自身的变换（通过 `gradientTransform` 属性指定）。

## 依赖关系

### Skia 核心依赖

- **include/effects/SkGradientShader.h**: 渐变着色器工厂
- **include/core/SkPoint.h**: 二维点类型

### SVG 模块依赖

- **modules/svg/include/SkSVGLinearGradient.h**: 类声明
- **modules/svg/include/SkSVGGradient.h**: 渐变基类
- **modules/svg/include/SkSVGAttributeParser.h**: 属性解析
- **modules/svg/include/SkSVGRenderContext.h**: 渲染上下文

## 设计模式与设计决策

### 模板方法模式

基类 `SkSVGGradient` 定义渲染流程，`onMakeShader()` 提供具体实现：

1. 基类收集渐变停止点（颜色和位置）
2. 基类调用 `onMakeShader()` 创建着色器
3. 派生类提供几何参数（线性、径向等）

### 坐标系统抽象

通过 `SkSVGLengthContext` 抽象不同的坐标系统，使相同的解析代码适用于：
- 对象边界框坐标（比例值）
- 用户空间坐标（绝对值）

### 简洁实现

线性渐变的几何定义非常简单（两个点），实现专注于坐标转换，将复杂性委托给 Skia 渐变着色器。

## 性能考量

### 着色器创建

`SkShaders::LinearGradient()` 创建开销：
- 轻量级：只分配着色器对象和拷贝参数
- 延迟计算：实际渐变计算发生在绘制时

### GPU 加速

Skia 的线性渐变完全支持 GPU：
- 编译为片段着色器
- 并行计算每个像素的渐变值
- 使用纹理或数学插值

### 缓存机会

相同参数的渐变可以缓存着色器对象，避免重复创建。

## 相关文件

### 头文件

- **modules/svg/include/SkSVGLinearGradient.h**: 类声明

### 基类

- **modules/svg/include/SkSVGGradient.h**: 渐变基类
- **modules/svg/src/SkSVGGradient.cpp**: 基类实现，处理停止点

### 相关渐变

- **modules/svg/src/SkSVGRadialGradient.cpp**: 径向渐变实现

### Skia 渐变

- **include/effects/SkGradientShader.h**: Skia 渐变接口
- **src/shaders/gradients/**: Skia 渐变着色器实现

### 使用示例

**基本线性渐变**:
```xml
<linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
  <stop offset="0%" stop-color="red"/>
  <stop offset="100%" stop-color="blue"/>
</linearGradient>
<rect width="200" height="100" fill="url(#grad1)"/>
```

**对角渐变**:
```xml
<linearGradient id="grad2" x1="0%" y1="0%" x2="100%" y2="100%">
  <stop offset="0%" stop-color="yellow"/>
  <stop offset="100%" stop-color="green"/>
</linearGradient>
```

**多色渐变**:
```xml
<linearGradient id="rainbow">
  <stop offset="0%" stop-color="red"/>
  <stop offset="33%" stop-color="yellow"/>
  <stop offset="66%" stop-color="blue"/>
  <stop offset="100%" stop-color="green"/>
</linearGradient>
```

该实现简洁高效，完整支持 SVG 线性渐变规范，并充分利用了 Skia 的渐变渲染能力。
