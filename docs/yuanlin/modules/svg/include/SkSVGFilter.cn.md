# SkSVGFilter

> 源文件: modules/svg/include/SkSVGFilter.h

## 概述

`SkSVGFilter` 实现了 SVG 规范中的 `<filter>` 元素，用于定义可应用于图形对象的滤镜效果。滤镜是 SVG 中最强大的特性之一，可以创建模糊、光照、变形等复杂视觉效果。`SkSVGFilter` 作为滤镜容器，管理滤镜原语（如模糊、颜色矩阵、合成等）的集合，并将这些原语组织成有向无环图（DAG）以构建最终的图像滤镜管道。该类继承自 `SkSVGHiddenContainer`，默认不直接渲染，只有在被其他元素引用时才生效。

## 架构位置

`SkSVGFilter` 在 Skia SVG 架构中的位置：

- **模块路径**: `modules/svg/include/`
- **继承层次**: `SkSVGNode` → `SkSVGHiddenContainer` → `SkSVGFilter`
- **功能角色**: 滤镜定义容器，管理滤镜原语并构建滤镜效果图
- **渲染阶段**: 定义阶段（不直接渲染），在其他元素应用滤镜时执行

在 SVG 架构中，`SkSVGFilter` 与滤镜原语节点（`SkSVGFe*` 系列类）协同工作，提供滤镜效果的声明和应用机制。

## 主要类与结构体

### SkSVGFilter 类定义

```cpp
class SK_API SkSVGFilter final : public SkSVGHiddenContainer {
public:
    // 工厂方法：创建滤镜容器
    static sk_sp<SkSVGFilter> Make();

    // 应用继承的表示属性到渲染上下文
    void applyProperties(SkSVGRenderContext*) const;

    // 构建滤镜效果的有向无环图（DAG）
    sk_sp<SkImageFilter> buildFilterDAG(const SkSVGRenderContext&) const;

    // 滤镜区域属性（百分比或绝对值）
    SVG_ATTR(X, SkSVGLength, SkSVGLength(-10, SkSVGLength::Unit::kPercentage))
    SVG_ATTR(Y, SkSVGLength, SkSVGLength(-10, SkSVGLength::Unit::kPercentage))
    SVG_ATTR(Width, SkSVGLength, SkSVGLength(120, SkSVGLength::Unit::kPercentage))
    SVG_ATTR(Height, SkSVGLength, SkSVGLength(120, SkSVGLength::Unit::kPercentage))

    // 坐标系统属性
    SVG_ATTR(FilterUnits, SkSVGObjectBoundingBoxUnits,
             SkSVGObjectBoundingBoxUnits(Type::kObjectBoundingBox))
    SVG_ATTR(PrimitiveUnits, SkSVGObjectBoundingBoxUnits,
             SkSVGObjectBoundingBoxUnits(Type::kUserSpaceOnUse))

private:
    SkSVGFilter() : INHERITED(SkSVGTag::kFilter) {}
    bool parseAndSetAttribute(const char*, const char*) override;
};
```

### 关键属性说明

1. **滤镜区域属性 (X, Y, Width, Height)**:
   - 默认值：`(-10%, -10%, 120%, 120%)`，比对象边界框略大
   - 作用：定义滤镜效果的应用区域，超出此区域的效果被裁剪
   - 原因：默认值留出边距以容纳模糊等扩展效果

2. **FilterUnits**:
   - 默认值：`kObjectBoundingBox`（相对于目标对象的边界框）
   - 作用：定义 x, y, width, height 属性的坐标系统
   - 选项：对象边界框（0-1 比例）或用户空间（绝对坐标）

3. **PrimitiveUnits**:
   - 默认值：`kUserSpaceOnUse`（用户空间坐标）
   - 作用：定义滤镜原语内部使用的坐标系统
   - 影响：滤镜原语的长度值和半径值的解释方式

## 公共 API 函数

### static sk_sp<SkSVGFilter> Make()

创建 `SkSVGFilter` 实例的工厂方法。

**返回值**: 智能指针 `sk_sp<SkSVGFilter>`，管理滤镜对象生命周期。

**用途**: 在 SVG 解析过程中遇到 `<filter>` 标签时调用。

**示例**:
```xml
<filter id="blur" x="-10%" y="-10%" width="120%" height="120%">
  <feGaussianBlur in="SourceGraphic" stdDeviation="5"/>
</filter>
```

### void applyProperties(SkSVGRenderContext*) const

将继承的表示属性传播到渲染上下文。

**参数**: `SkSVGRenderContext*` 当前渲染上下文的可变指针。

**作用**: 确保滤镜原语可以访问从父节点继承的样式属性（如 `color`、`flood-color` 等）。

**调用时机**: 在构建滤镜 DAG 之前调用，设置正确的属性上下文。

### sk_sp<SkImageFilter> buildFilterDAG(const SkSVGRenderContext&) const

构建表示滤镜效果的 `SkImageFilter` 有向无环图。

**参数**: `const SkSVGRenderContext&` 只读渲染上下文，提供坐标系统和属性访问。

**返回值**: `sk_sp<SkImageFilter>` 滤镜链的根节点，可直接应用于 `SkPaint`。

**核心逻辑**:
1. 遍历子节点（滤镜原语）
2. 解析原语间的输入输出依赖关系
3. 构建滤镜效果的组合链
4. 处理 `in` 和 `result` 属性建立连接

**返回的滤镜图**:
```
SourceGraphic → feGaussianBlur → feColorMatrix → 输出
```

### 属性访问器（通过 SVG_ATTR 宏生成）

```cpp
void setX(const SkSVGLength& x);
const SkSVGLength& getX() const;
// ... Y, Width, Height 类似

void setFilterUnits(const SkSVGObjectBoundingBoxUnits& units);
const SkSVGObjectBoundingBoxUnits& getFilterUnits() const;

void setPrimitiveUnits(const SkSVGObjectBoundingBoxUnits& units);
const SkSVGObjectBoundingBoxUnits& getPrimitiveUnits() const;
```

## 内部实现细节

### 滤镜 DAG 构建

滤镜的核心是有向无环图的构建，涉及以下步骤：

#### 1. 输入输出管理

每个滤镜原语都有输入和输出：

- **命名输入**: `in="SourceGraphic"`、`in="SourceAlpha"`、`in="result1"`
- **默认输入**: 前一个原语的输出
- **命名输出**: `result="blur1"` 用于后续原语引用
- **隐式输出**: 未命名的输出传递给下一个原语

#### 2. 特殊输入源

SVG 规范定义的内置输入：

- **SourceGraphic**: 原始图形内容
- **SourceAlpha**: 原始图形的 alpha 通道
- **BackgroundImage**: 背景图像（较少支持）
- **BackgroundAlpha**: 背景的 alpha 通道
- **FillPaint**: 填充颜色作为图像
- **StrokePaint**: 描边颜色作为图像

#### 3. 图构建算法

```
1. 初始化输入表：SourceGraphic, SourceAlpha 等
2. 按顺序遍历子节点（滤镜原语）
3. 对于每个原语：
   a. 解析其 in 属性，从输入表获取 SkImageFilter
   b. 调用原语的 makeImageFilter() 创建滤镜节点
   c. 如果有 result 属性，将输出存入输入表
   d. 否则，更新默认输出
4. 返回最后一个原语的输出作为最终滤镜
```

### 坐标系统转换

#### FilterUnits 的作用

当 `filterUnits="objectBoundingBox"` 时：

```
绝对坐标 = bbox.x + x * bbox.width
绝对坐标 = bbox.y + y * bbox.height
```

当 `filterUnits="userSpaceOnUse"` 时，x 和 y 直接使用用户空间坐标。

#### PrimitiveUnits 的作用

影响滤镜原语内部的长度解析：

- **objectBoundingBox**: 原语的 `stdDeviation="0.05"` 表示边界框的 5%
- **userSpaceOnUse**: `stdDeviation="5"` 表示用户空间的 5 个单位

### 滤镜区域裁剪

滤镜效果被限制在 `(x, y, width, height)` 定义的区域内：

1. **计算绝对区域**: 根据 `filterUnits` 解析为像素坐标
2. **应用裁剪**: 滤镜输出超出区域的部分被裁剪
3. **性能优化**: 限制滤镜计算范围，避免无限扩展

默认的 120% 尺寸确保模糊等效果有足够的边距。

### 隐藏容器特性

继承自 `SkSVGHiddenContainer`，具有以下特性：

- **不渲染**: `onRender` 方法为空，不参与正常渲染遍历
- **定义用途**: 只在 `<defs>` 或其他非渲染上下文中有效
- **按需使用**: 通过 `filter="url(#filterId)"` 引用时才生效

## 依赖关系

### 直接依赖

- **SkSVGHiddenContainer**: 父类，提供隐藏容器语义
- **SkSVGTypes.h**: 定义 `SkSVGLength` 和 `SkSVGObjectBoundingBoxUnits`
- **SkImageFilter**: Skia 的图像滤镜基础设施
- **SkSVGRenderContext**: 提供坐标解析和属性访问

### 滤镜原语依赖

- **SkSVGFe.h**: 滤镜原语基类
- **SkSVGFeGaussianBlur.h**: 模糊效果
- **SkSVGFeColorMatrix.h**: 颜色矩阵变换
- **SkSVGFeComposite.h**: 图像合成
- **SkSVGFeMorphology.h**: 形态学操作（膨胀/腐蚀）
- **SkSVGFeOffset.h**: 偏移效果
- 以及其他 `SkSVGFe*` 类

### 系统集成

- **SkSVGFilterContext**: 滤镜构建时的上下文，管理输入输出映射
- **SkPaint**: 应用滤镜到绘图操作
- **SkCanvas**: 通过 paint 将滤镜效果应用到渲染

## 设计模式与设计决策

### 组合模式（Composite Pattern）

滤镜系统使用组合模式：

- **容器**: `SkSVGFilter` 作为组合节点
- **叶子节点**: 各个滤镜原语（`SkSVGFe*`）
- **统一接口**: 所有节点都实现 `makeImageFilter()`
- **层次结构**: 滤镜链形成树状或 DAG 结构

### 构建器模式（Builder Pattern）

滤镜 DAG 的构建过程类似构建器模式：

- **逐步构建**: 按顺序添加滤镜原语
- **中间状态**: 维护输入输出映射表
- **最终产物**: 完整的 `SkImageFilter` 图

### 延迟计算（Lazy Evaluation）

滤镜定义和应用分离：

- **定义时**: 只解析和存储滤镜配置
- **应用时**: 当图形对象引用滤镜时才构建 DAG
- **优势**: 支持条件应用和动态滤镜切换

### 声明式 API

SVG 滤镜是声明式的：

```xml
<filter id="shadow">
  <feGaussianBlur in="SourceAlpha" stdDeviation="3"/>
  <feOffset dx="4" dy="4" result="offsetBlur"/>
  <feMerge>
    <feMergeNode in="offsetBlur"/>
    <feMergeNode in="SourceGraphic"/>
  </feMerge>
</filter>
```

声明式设计使得滤镜定义直观、可复用且易于优化。

## 性能考量

### DAG 构建开销

- **一次性构建**: 滤镜 DAG 通常只构建一次，然后缓存
- **复杂度**: O(n)，其中 n 是滤镜原语数量
- **优化空间**: 可以缓存构建结果，避免重复构建

### 滤镜执行开销

- **GPU 加速**: Skia 的 `SkImageFilter` 支持 GPU 后端，滤镜可在 GPU 上高效执行
- **区域限制**: 通过 `filterRegion` 限制计算范围
- **早期裁剪**: 如果滤镜区域不与视口相交，可跳过计算

### 内存使用

- **中间缓冲**: 复杂滤镜链可能需要多个中间缓冲区
- **区域优化**: 限制滤镜区域可减少缓冲区大小
- **共享输入**: 多个原语引用同一输入时避免重复计算

### 优化策略

1. **滤镜合并**: 某些滤镜原语可以合并为单个着色器
2. **边界框预测**: 提前计算滤镜输出边界，避免无用计算
3. **缓存机制**: 缓存静态滤镜的结果，特别是在动画场景中

## 相关文件

### 核心依赖

- **modules/svg/include/SkSVGHiddenContainer.h**: 隐藏容器基类
- **modules/svg/include/SkSVGTypes.h**: 类型定义
- **include/core/SkImageFilter.h**: Skia 图像滤镜基础设施

### 滤镜原语

- **modules/svg/include/SkSVGFe.h**: 滤镜原语基类
- **modules/svg/include/SkSVGFeGaussianBlur.h**: 高斯模糊
- **modules/svg/include/SkSVGFeColorMatrix.h**: 颜色矩阵
- **modules/svg/include/SkSVGFeBlend.h**: 混合模式
- **modules/svg/include/SkSVGFeComposite.h**: 图像合成
- **modules/svg/include/SkSVGFeMorphology.h**: 形态学滤镜
- **modules/svg/include/SkSVGFeOffset.h**: 偏移滤镜

### 实现文件

- **modules/svg/src/SkSVGFilter.cpp**: 滤镜容器的实现，包含 DAG 构建逻辑
- **modules/svg/src/SkSVGFilterContext.cpp**: 滤镜构建上下文的管理

### 应用机制

- **modules/svg/include/SkSVGRenderContext.h**: 渲染上下文，处理滤镜引用
- **modules/svg/src/SkSVGNode.cpp**: 节点基类，应用滤镜到绘图操作

### 相关节点

- **modules/svg/include/SkSVGDefs.h**: 通常用于定义滤镜
- **modules/svg/include/SkSVGShape.h**: 形状节点，可以应用滤镜

该类是 SVG 滤镜系统的核心，通过组织滤镜原语和构建滤镜 DAG，实现了丰富的视觉效果功能。
