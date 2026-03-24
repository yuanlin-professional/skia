# SkSVGFeFlood

> 源文件: modules/svg/include/SkSVGFeFlood.h

## 概述

`SkSVGFeFlood` 实现了 SVG 滤镜原语 `<feFlood>`，用于在滤镜区域内填充统一的颜色。该原语是滤镜系统中最简单的一种，它创建一个纯色矩形图像，常用于生成阴影、背景或作为其他滤镜效果的输入源。`<feFlood>` 不依赖任何输入图像，而是根据 `flood-color` 和 `flood-opacity` 属性直接生成输出，是构建复杂滤镜效果的基础构件之一。

## 架构位置

`SkSVGFeFlood` 在 Skia SVG 滤镜架构中的位置：

- **模块路径**: `modules/svg/include/`
- **继承层次**: `SkSVGNode` → `SkSVGFe` → `SkSVGFeFlood`
- **功能角色**: 滤镜原语，生成纯色填充效果
- **依赖关系**: 无输入依赖，是独立的颜色源

在滤镜原语家族中，`SkSVGFeFlood` 是少数几个不需要输入图像的原语之一，与 `<feImage>` 和 `<feTurbulence>` 类似。

## 主要类与结构体

### SkSVGFeFlood 类定义

```cpp
class SK_API SkSVGFeFlood : public SkSVGFe {
public:
    // 工厂方法：创建 feFlood 实例
    static sk_sp<SkSVGFeFlood> Make();

protected:
    // 创建对应的 SkImageFilter
    sk_sp<SkImageFilter> onMakeImageFilter(const SkSVGRenderContext&,
                                           const SkSVGFilterContext&) const override;

    // 返回空输入列表（无需输入）
    std::vector<SkSVGFeInputType> getInputs() const override { return {}; }

private:
    SkSVGFeFlood() : INHERITED(SkSVGTag::kFeFlood) {}

    // 解析渲染上下文中的洪水填充颜色
    SkColor resolveFloodColor(const SkSVGRenderContext&) const;
};
```

### 关键特性

1. **无输入依赖**: `getInputs()` 返回空向量，表示不依赖其他滤镜原语的输出
2. **颜色解析**: 通过 `resolveFloodColor` 从渲染上下文获取最终颜色
3. **简单性**: 类定义非常简洁，核心逻辑集中在颜色解析和滤镜创建

## 公共 API 函数

### static sk_sp<SkSVGFeFlood> Make()

创建 `SkSVGFeFlood` 实例的工厂方法。

**返回值**: 智能指针 `sk_sp<SkSVGFeFlood>`。

**用途**: 在 SVG 解析器遇到 `<feFlood>` 标签时调用。

**XML 示例**:
```xml
<feFlood flood-color="blue" flood-opacity="0.5" result="flood"/>
```

## 内部实现细节

### onMakeImageFilter 实现

该方法创建实际的 `SkImageFilter` 对象：

**核心逻辑**:
1. 调用 `resolveFloodColor()` 获取最终的 ARGB 颜色
2. 调用 `resolveFilterSubregion()` 获取滤镜应用区域
3. 使用 `SkImageFilters::Color()` 创建颜色填充滤镜
4. 可能需要处理 `flood-opacity` 的 alpha 合成

**参数说明**:
- `SkSVGRenderContext&`: 提供属性访问和坐标解析
- `SkSVGFilterContext&`: 提供滤镜上下文，包括区域信息

**返回值**: 指向 `SkImageFilter` 的智能指针，通常是 `SkColorFilterImageFilter`。

### resolveFloodColor 实现

解析最终的填充颜色，需要考虑多个属性：

**颜色来源**:
1. **flood-color 属性**: 可以是颜色名称、十六进制值或 `currentColor`
2. **flood-opacity 属性**: 独立的透明度值（0.0-1.0）
3. **继承颜色**: 如果使用 `currentColor`，需要从上下文获取当前颜色

**解析步骤**:
```cpp
SkColor resolveFloodColor(const SkSVGRenderContext& ctx) const {
    // 1. 获取 flood-color 属性值（RGB 部分）
    SkSVGColor floodColor = ctx.presentationContext().fFloodColor;

    // 2. 获取 flood-opacity 属性值（Alpha 部分）
    SkScalar opacity = ctx.presentationContext().fFloodOpacity;

    // 3. 组合 RGB 和 Alpha
    return SkColorSetARGB(
        SkScalarRoundToInt(opacity * 255),
        SkColorGetR(floodColor),
        SkColorGetG(floodColor),
        SkColorGetB(floodColor)
    );
}
```

### getInputs 实现

```cpp
std::vector<SkSVGFeInputType> getInputs() const override {
    return {};  // 返回空向量，无输入依赖
}
```

这告诉滤镜构建系统，`<feFlood>` 是一个独立的颜色源，不需要在 DAG 中连接输入节点。

## 依赖关系

### 直接依赖

- **SkSVGFe**: 滤镜原语基类，提供通用接口
- **SkColor**: Skia 颜色类型，表示 ARGB 颜色
- **SkImageFilter**: Skia 图像滤镜基础设施
- **SkSVGRenderContext**: 渲染上下文，提供属性访问
- **SkSVGFilterContext**: 滤镜上下文，提供区域和输入管理

### 属性依赖

虽然类定义中没有显式声明属性，但实际使用以下表示属性：

- **flood-color**: 填充颜色（默认黑色）
- **flood-opacity**: 填充透明度（默认 1.0）
- **通用滤镜属性**: `x`, `y`, `width`, `height`, `result` 等

### Skia 核心依赖

- **include/effects/SkImageFilters.h**: 提供 `SkImageFilters::Color()` 等工厂方法
- **include/core/SkColorFilter.h**: 可能使用颜色滤镜实现填充效果

## 设计模式与设计决策

### 策略模式（Strategy Pattern）

`SkSVGFeFlood` 实现了滤镜原语接口，作为一种生成策略：

- **接口**: `onMakeImageFilter()` 定义统一的滤镜生成接口
- **具体策略**: 生成纯色填充滤镜
- **可替换性**: 可以与其他滤镜原语组合使用

### 属性分离

将颜色和透明度分为两个属性的设计决策：

**优势**:
- **灵活性**: 可以独立动画化颜色和透明度
- **CSS 兼容**: 符合 CSS 属性分离的传统
- **重用性**: `flood-opacity` 可以独立于颜色值设置

**实现复杂性**: 需要在解析时合并两个属性为单一 ARGB 值。

### 无输入设计

作为源原语的设计优势：

1. **简化依赖**: 不需要等待输入准备，可以独立计算
2. **并行性**: 可以与其他原语并行执行
3. **确定性**: 输出完全由属性决定，易于缓存

### 裁剪区域

虽然生成的是纯色图像，仍然需要遵守滤镜子区域：

- **高效性**: 只生成必要区域的像素
- **一致性**: 与其他滤镜原语保持接口一致
- **组合性**: 确保在滤镜链中正确裁剪

## 性能考量

### 轻量级操作

`<feFlood>` 是最高效的滤镜原语之一：

- **无输入读取**: 不需要采样输入图像
- **简单计算**: 只是填充纯色，无复杂数学运算
- **GPU 友好**: 可以用简单的片段着色器实现

### 内存占用

生成的图像大小取决于滤镜区域：

```
内存 = width × height × 4 bytes (RGBA)
```

对于小区域，几乎可以忽略不计。对于大区域，可能需要优化为常量纹理。

### GPU 实现

在 GPU 上，`<feFlood>` 可以极其高效地实现：

```glsl
// 片段着色器伪代码
vec4 main() {
    return flood_color;  // 常量输出
}
```

GPU 可以并行生成所有像素，几乎无开销。

### 优化机会

1. **常量优化**: 编译器可能识别出纯色填充并优化后续计算
2. **延迟生成**: 如果输出未被使用，可以完全跳过生成
3. **尺寸优化**: 对于大面积纯色，可以使用压缩表示

## 相关文件

### 核心依赖

- **modules/svg/include/SkSVGFe.h**: 滤镜原语基类
- **modules/svg/include/SkSVGRenderContext.h**: 渲染上下文
- **modules/svg/include/SkSVGFilterContext.h**: 滤镜上下文

### 实现文件

- **modules/svg/src/SkSVGFeFlood.cpp**: `SkSVGFeFlood` 的完整实现，包含颜色解析和滤镜创建逻辑

### 相关滤镜原语

- **modules/svg/include/SkSVGFeImage.h**: 另一个源原语，加载外部图像
- **modules/svg/include/SkSVGFeTurbulence.h**: 生成噪声纹理的源原语
- **modules/svg/include/SkSVGFeComposite.h**: 常与 feFlood 组合使用，实现混合效果

### Skia 滤镜基础设施

- **include/core/SkImageFilter.h**: 图像滤镜基类
- **include/effects/SkImageFilters.h**: 滤镜工厂方法
- **include/core/SkColorFilter.h**: 颜色滤镜，可能用于实现 feFlood

### 使用示例

典型的 `<feFlood>` 应用场景：

**1. 阴影背景**:
```xml
<filter id="drop-shadow">
  <feFlood flood-color="black" flood-opacity="0.5"/>
  <feComposite in="SourceGraphic"/>
</filter>
```

**2. 背景填充**:
```xml
<filter id="background">
  <feFlood flood-color="white"/>
  <feMerge>
    <feMergeNode/>
    <feMergeNode in="SourceGraphic"/>
  </feMerge>
</filter>
```

**3. 颜色叠加**:
```xml
<filter id="tint">
  <feFlood flood-color="blue" flood-opacity="0.3" result="color"/>
  <feBlend in="SourceGraphic" in2="color" mode="multiply"/>
</filter>
```

该类虽然简单，但在 SVG 滤镜系统中扮演着重要的基础角色，是许多复杂效果的构建基础。
