# SkSVGFeOffset

> 源文件: modules/svg/src/SkSVGFeOffset.cpp

## 概述

`SkSVGFeOffset.cpp` 实现了 SVG 滤镜原语 `<feOffset>`，用于对输入图像应用空间偏移。该滤镜将图像内容平移指定的距离，常用于创建阴影效果、多层叠加和位置调整。实现极其简洁，仅 34 行代码，展示了简单滤镜原语的典型实现模式。该滤镜不修改图像内容，只改变图像的空间位置，是构建复杂滤镜效果的基础构件之一。

## 架构位置

- **模块路径**: `modules/svg/src/`
- **对应头文件**: `modules/svg/include/SkSVGFeOffset.h`
- **继承层次**: `SkSVGNode` → `SkSVGFe` → `SkSVGFeOffset`
- **功能角色**: 滤镜原语，执行图像空间偏移

## 主要类与结构体

### 实现的方法

1. **parseAndSetAttribute()**: 解析 `dx` 和 `dy` 属性
2. **onMakeImageFilter()**: 创建偏移图像滤镜

## 公共 API 函数

### bool parseAndSetAttribute(const char* name, const char* value)

解析偏移滤镜的属性。

```cpp
bool SkSVGFeOffset::parseAndSetAttribute(const char* name, const char* value) {
    return INHERITED::parseAndSetAttribute(name, value) ||
           this->setDx(SkSVGAttributeParser::parse<SkSVGNumberType>("dx", name, value)) ||
           this->setDy(SkSVGAttributeParser::parse<SkSVGNumberType>("dy", name, value));
}
```

**支持的属性**:
- **dx**: 水平偏移量（数字，可以为负）
- **dy**: 垂直偏移量（数字，可以为负）

**默认值**: dx=0, dy=0（无偏移）

## 内部实现细节

### sk_sp<SkImageFilter> onMakeImageFilter()

创建偏移图像滤镜。

```cpp
sk_sp<SkImageFilter> SkSVGFeOffset::onMakeImageFilter(
    const SkSVGRenderContext& ctx,
    const SkSVGFilterContext& fctx) const
{
    // 1. 计算变换后的偏移量
    const auto d = SkV2{this->getDx(), this->getDy()}
                 * ctx.transformForCurrentOBB(fctx.primitiveUnits()).scale;

    // 2. 解析输入图像
    sk_sp<SkImageFilter> in =
        fctx.resolveInput(ctx, this->getIn(), this->resolveColorspace(ctx, fctx));

    // 3. 创建偏移滤镜
    return SkImageFilters::Offset(
        d.x, d.y, std::move(in), this->resolveFilterSubregion(ctx, fctx));
}
```

### 详细步骤解析

#### 1. 偏移量计算

```cpp
const auto d = SkV2{this->getDx(), this->getDy()}
             * ctx.transformForCurrentOBB(fctx.primitiveUnits()).scale;
```

**坐标系统变换**:
- 获取 `dx` 和 `dy` 原始值
- 创建二维向量 `SkV2{dx, dy}`
- 乘以当前坐标变换的缩放因子

**为什么需要变换**:
- 如果 `primitiveUnits` 为 `objectBoundingBox`，偏移量是相对于对象大小的
- 如果为 `userSpaceOnUse`，使用用户空间单位
- 缩放因子确保偏移量在正确的坐标系统中

**示例**:
```xml
<feOffset dx="0.1" dy="0.1"/>  <!-- 对象边界框单位：10% 偏移 -->
<feOffset dx="10" dy="10"/>    <!-- 用户空间单位：10 像素偏移 -->
```

#### 2. 输入解析

```cpp
sk_sp<SkImageFilter> in =
    fctx.resolveInput(ctx, this->getIn(), this->resolveColorspace(ctx, fctx));
```

**输入来源**:
- `this->getIn()`: 输入引用（如 "SourceGraphic"、"result1" 等）
- `resolveColorspace()`: 解析所需的颜色空间
- `fctx.resolveInput()`: 从滤镜上下文获取输入滤镜

**常见输入**:
- `SourceGraphic`: 原始图形内容
- `SourceAlpha`: 原始图形的 alpha 通道
- 前一个滤镜的输出

#### 3. 滤镜创建

```cpp
return SkImageFilters::Offset(
    d.x, d.y, std::move(in), this->resolveFilterSubregion(ctx, fctx));
```

**SkImageFilters::Offset 参数**:
- `d.x`: 水平偏移量（像素）
- `d.y`: 垂直偏移量（像素）
- `in`: 输入图像滤镜
- `cropRect`: 滤镜子区域（裁剪边界）

**偏移效果**:
- 正 dx: 向右移动
- 负 dx: 向左移动
- 正 dy: 向下移动
- 负 dy: 向上移动

## 依赖关系

### Skia 核心依赖

- **include/core/SkImageFilter.h**: 图像滤镜基类
- **include/core/SkM44.h**: 4x4 矩阵（用于坐标变换）
- **include/effects/SkImageFilters.h**: 提供 `Offset()` 工厂方法

### SVG 模块依赖

- **modules/svg/include/SkSVGFeOffset.h**: 类声明
- **modules/svg/include/SkSVGAttributeParser.h**: 属性解析
- **modules/svg/include/SkSVGFilterContext.h**: 滤镜上下文
- **modules/svg/include/SkSVGRenderContext.h**: 渲染上下文

## 设计模式与设计决策

### 最小接口

`<feOffset>` 只有两个参数，实现极其简洁：

```cpp
this->setDx(...) || this->setDy(...)
```

这种简单性使其易于理解、实现和组合。

### 链式滤镜

通过接受输入滤镜并返回新滤镜，支持滤镜链：

```cpp
Input → Offset → Output
```

可以与其他滤镜组合：

```cpp
Input → Blur → Offset → Output  // 先模糊后偏移
Input → Offset → Blur → Output  // 先偏移后模糊
```

### 坐标系统适配

通过变换缩放因子，同一代码适用于不同的坐标系统：

```cpp
d * scale  // 自适应 objectBoundingBox 或 userSpaceOnUse
```

## 性能考量

### 轻量级操作

偏移是最简单的图像操作之一：
- 不修改像素值
- 只改变采样位置
- GPU 上几乎零开销

### GPU 实现

在 GPU 上，偏移通过纹理坐标偏移实现：

```glsl
vec4 main() {
    return texture(input, texCoord - offset);  // 简单的坐标偏移
}
```

GPU 可以并行处理所有像素，偏移操作不会成为瓶颈。

### 内存使用

偏移不需要额外的中间缓冲区，只是改变了图像的逻辑位置。

## 相关文件

### 头文件

- **modules/svg/include/SkSVGFeOffset.h**: 类声明

### 相关滤镜原语

- **modules/svg/src/SkSVGFeGaussianBlur.cpp**: 模糊滤镜，常与偏移组合创建阴影
- **modules/svg/src/SkSVGFeMerge.cpp**: 合并滤镜，组合偏移后的图像

### Skia 滤镜

- **include/effects/SkImageFilters.h**: `Offset()` 工厂方法声明
- **src/effects/imagefilters/**: 偏移滤镜的底层实现

### 使用示例

**基本偏移**:
```xml
<feOffset dx="10" dy="10" in="SourceGraphic"/>
```

**创建阴影效果**:
```xml
<filter id="shadow">
  <feGaussianBlur in="SourceAlpha" stdDeviation="3" result="blur"/>
  <feOffset in="blur" dx="4" dy="4" result="offsetBlur"/>
  <feMerge>
    <feMergeNode in="offsetBlur"/>
    <feMergeNode in="SourceGraphic"/>
  </feMerge>
</filter>
```

**负偏移**:
```xml
<feOffset dx="-5" dy="-5" in="SourceGraphic"/>
```

**与颜色组合**:
```xml
<filter id="colored-shadow">
  <feOffset in="SourceAlpha" dx="5" dy="5" result="offset"/>
  <feFlood flood-color="red" result="color"/>
  <feComposite in="color" in2="offset" operator="in"/>
</filter>
```

**边界框单位**:
```xml
<filter id="proportional" primitiveUnits="objectBoundingBox">
  <feOffset dx="0.05" dy="0.05"/>  <!-- 5% 偏移 -->
</filter>
```

该实现简洁高效，是 SVG 滤镜系统中最基础但最实用的原语之一，常用于创建阴影和多层效果。
