# SkSVGFeMorphology

> 源文件: modules/svg/src/SkSVGFeMorphology.cpp

## 概述

`SkSVGFeMorphology` 实现了 SVG 滤镜原语 `<feMorphology>`，用于对输入图像执行形态学操作。该滤镜支持两种操作模式：腐蚀（erode）和膨胀（dilate），通过调整图像边缘的像素来实现边缘收缩或扩展效果。这些操作在图像处理中常用于噪声去除、边缘检测、轮廓提取等场景。在 SVG 中，形态学滤镜常用于创建粗体文字效果、阴影边缘处理和形状变形等视觉效果。

## 架构位置

`SkSVGFeMorphology` 在 Skia SVG 滤镜架构中的位置：

- **模块路径**: `modules/svg/src/`
- **继承层次**: `SkSVGNode` → `SkSVGFe` → `SkSVGFeMorphology`
- **功能角色**: 形态学滤镜原语，提供腐蚀和膨胀操作
- **依赖**: 依赖单个输入图像，输出变形后的图像

在滤镜原语家族中，`SkSVGFeMorphology` 属于像素操作类滤镜，与 `feGaussianBlur`、`feConvolveMatrix` 等共同构成图像处理工具集。

## 主要类与结构体

### Operator 枚举

```cpp
enum class Operator {
    kErode,   // 腐蚀：收缩明亮区域
    kDilate   // 膨胀：扩展明亮区域
};
```

### Radius 结构体

```cpp
struct Radius {
    SkSVGNumberType fX;  // 水平方向半径
    SkSVGNumberType fY;  // 垂直方向半径
};
```

**用途**: 定义形态学操作的影响范围，支持非均匀的椭圆形核。

## 公共 API 函数

### bool parseAndSetAttribute(const char* name, const char* value)

解析并设置 `<feMorphology>` 的特定属性。

**参数**:
- `name`: 属性名称
- `value`: 属性值字符串

**支持的属性**:
- **operator**: 操作类型（"erode" 或 "dilate"）
- **radius**: 形态学半径（单个数字或两个数字）

**返回值**: 如果成功解析并设置属性返回 `true`，否则返回 `false`。

**解析逻辑**:
```cpp
this->setOperator(SkSVGAttributeParser::parse<Operator>("operator", name, value))
this->setRadius(SkSVGAttributeParser::parse<Radius>("radius", name, value))
```

### sk_sp<SkImageFilter> onMakeImageFilter(const SkSVGRenderContext&, const SkSVGFilterContext&) const

创建对应的 Skia 图像滤镜。

**实现步骤**:
1. 解析滤镜子区域（`resolveFilterSubregion`）
2. 解析色彩空间（`resolveColorspace`）
3. 解析输入图像（`resolveInput`）
4. 计算实际半径（考虑坐标变换）
5. 根据操作类型创建腐蚀或膨胀滤镜

**返回值**: 指向 `SkImageFilter` 的智能指针。

## 内部实现细节

### onMakeImageFilter 实现

```cpp
sk_sp<SkImageFilter> SkSVGFeMorphology::onMakeImageFilter(
    const SkSVGRenderContext& ctx,
    const SkSVGFilterContext& fctx) const
{
    // 1. 获取裁剪区域
    const SkRect cropRect = this->resolveFilterSubregion(ctx, fctx);

    // 2. 解析色彩空间
    const SkSVGColorspace colorspace = this->resolveColorspace(ctx, fctx);

    // 3. 获取输入滤镜
    sk_sp<SkImageFilter> input = fctx.resolveInput(ctx, this->getIn(), colorspace);

    // 4. 计算变换后的半径
    const auto r = SkV2{fRadius.fX, fRadius.fY}
                 * ctx.transformForCurrentOBB(fctx.primitiveUnits()).scale;

    // 5. 根据操作类型创建滤镜
    switch (fOperator) {
        case Operator::kErode:
            return SkImageFilters::Erode(r.x, r.y, input, cropRect);
        case Operator::kDilate:
            return SkImageFilters::Dilate(r.x, r.y, input, cropRect);
    }
}
```

### 半径计算

半径值需要考虑坐标系统的变换：

```cpp
const auto r = SkV2{fRadius.fX, fRadius.fY}
             * ctx.transformForCurrentOBB(fctx.primitiveUnits()).scale;
```

**变换逻辑**:
- 如果 `primitiveUnits` 为 `objectBoundingBox`，半径相对于对象边界框
- 如果为 `userSpaceOnUse`，半径使用用户空间单位
- 乘以当前变换的缩放因子得到像素空间的半径

### Operator 解析

```cpp
template <>
bool SkSVGAttributeParser::parse<SkSVGFeMorphology::Operator>(
    SkSVGFeMorphology::Operator* op)
{
    static constexpr std::tuple<const char*, SkSVGFeMorphology::Operator> gMap[] = {
        { "dilate", SkSVGFeMorphology::Operator::kDilate },
        { "erode" , SkSVGFeMorphology::Operator::kErode  },
    };

    return this->parseEnumMap(gMap, op) && this->parseEOSToken();
}
```

**枚举映射**: 将 XML 属性字符串映射到枚举值。

### Radius 解析

```cpp
template <>
bool SkSVGAttributeParser::parse<SkSVGFeMorphology::Radius>(
    SkSVGFeMorphology::Radius* radius)
{
    std::vector<SkSVGNumberType> values;
    if (!this->parse(&values)) {
        return false;
    }

    radius->fX = values[0];
    radius->fY = values.size() > 1 ? values[1] : values[0];
    return true;
}
```

**解析规则**:
- 单个数字: 水平和垂直半径相同（圆形）
- 两个数字: 分别指定水平和垂直半径（椭圆形）

**示例**:
- `radius="5"` → fX=5, fY=5
- `radius="10 5"` → fX=10, fY=5

## 依赖关系

### Skia 核心依赖

- **include/effects/SkImageFilters.h**: 提供 `Erode()` 和 `Dilate()` 工厂方法
- **include/core/SkImageFilter.h**: 图像滤镜基类
- **include/core/SkRect.h**: 矩形区域定义
- **include/core/SkM44.h**: 4x4 矩阵变换（用于坐标变换）

### SVG 模块依赖

- **modules/svg/include/SkSVGFeMorphology.h**: 类声明
- **modules/svg/include/SkSVGAttributeParser.h**: 属性解析器
- **modules/svg/include/SkSVGFilterContext.h**: 滤镜上下文
- **modules/svg/include/SkSVGRenderContext.h**: 渲染上下文

### 私有基础设施

- **include/private/base/SkAssert.h**: 断言宏

## 设计模式与设计决策

### 策略模式

通过 `Operator` 枚举实现两种算法策略：

```cpp
switch (fOperator) {
    case Operator::kErode:
        return SkImageFilters::Erode(...);
    case Operator::kDilate:
        return SkImageFilters::Dilate(...);
}
```

这种设计允许运行时选择操作类型，保持代码简洁。

### 非均匀核支持

支持椭圆形形态学核：

```cpp
struct Radius {
    SkSVGNumberType fX;  // 可以不同于 fY
    SkSVGNumberType fY;
};
```

**优势**:
- **灵活性**: 可以独立控制水平和垂直方向的影响范围
- **艺术效果**: 创建定向的形态学效果
- **性能**: 在某些情况下可以减少计算量

### 坐标空间自适应

半径计算考虑了不同的坐标系统：

```cpp
r = radius * transformScale
```

**适应性**: 确保在不同的 `primitiveUnits` 设置下都能正确工作。

### 模板特化解析

为自定义类型提供模板特化的解析器：

```cpp
template <>
bool SkSVGAttributeParser::parse<SkSVGFeMorphology::Operator>(...)

template <>
bool SkSVGAttributeParser::parse<SkSVGFeMorphology::Radius>(...)
```

**优势**: 将类型定义与解析逻辑分离，保持代码模块化。

## 性能考量

### 形态学操作的复杂度

形态学操作的时间复杂度：

```
O(width × height × radius_x × radius_y)
```

对于大半径，计算成本显著增加。

### GPU 加速

Skia 的 `SkImageFilters::Erode` 和 `Dilate` 支持 GPU 加速：

- **并行性**: GPU 可以并行处理所有像素
- **优化算法**: 使用分离卷积等技术减少计算量
- **着色器实现**: 将形态学操作编译为高效的片段着色器

### 半径优化

**大半径优化**:
- 对于圆形核，某些算法可以在常数时间内计算（如积分图方法）
- 对于椭圆核，可以使用分离操作（先水平后垂直）

**小半径快速路径**:
- 半径为 0 时直接返回输入图像
- 半径为 1 时使用简化的 3x3 卷积核

### 内存使用

形态学操作通常需要中间缓冲区：

```
内存 = width × height × bytesPerPixel
```

对于大图像，可能需要数十兆字节的临时内存。

## 相关文件

### 头文件

- **modules/svg/include/SkSVGFeMorphology.h**: 类声明和接口定义

### 相关滤镜原语

- **modules/svg/src/SkSVGFeGaussianBlur.cpp**: 另一种邻域操作滤镜
- **modules/svg/src/SkSVGFeConvolveMatrix.cpp**: 通用卷积滤镜
- **modules/svg/src/SkSVGFeComponentTransfer.cpp**: 像素级颜色变换

### Skia 滤镜实现

- **include/effects/SkImageFilters.h**: 声明 `Erode()` 和 `Dilate()` 工厂方法
- **src/effects/imagefilters/**: 形态学滤镜的底层实现（可能包括 CPU 和 GPU 路径）

### 解析器

- **modules/svg/include/SkSVGAttributeParser.h**: 属性解析器接口
- **modules/svg/src/SkSVGAttributeParser.cpp**: 解析器实现，包含模板特化

### 使用示例

**腐蚀效果（细化边缘）**:
```xml
<feMorphology operator="erode" radius="2" in="SourceGraphic"/>
```

**膨胀效果（加粗边缘）**:
```xml
<feMorphology operator="dilate" radius="3" in="SourceAlpha"/>
```

**椭圆形核**:
```xml
<feMorphology operator="dilate" radius="5 2" in="SourceGraphic"/>
```

**创建轮廓效果**:
```xml
<filter id="outline">
  <feMorphology operator="dilate" radius="2" in="SourceAlpha" result="dilated"/>
  <feMorphology operator="erode" radius="1" in="SourceAlpha" result="eroded"/>
  <feComposite in="dilated" in2="eroded" operator="out" result="outline"/>
  <feFlood flood-color="black"/>
  <feComposite in2="outline" operator="in"/>
</filter>
```

该实现提供了高效的形态学操作，是 SVG 滤镜系统中创建边缘效果的重要工具。
