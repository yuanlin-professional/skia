# SkSVGUse

> 源文件: modules/svg/include/SkSVGUse.h

## 概述

`SkSVGUse` 实现了 SVG 规范中的 `<use>` 元素，该元素允许在文档中重复使用已定义的图形元素。通过引用其他元素的 ID，`<use>` 元素可以实例化并渲染模板内容，支持位置偏移和变换。这种机制是 SVG 中实现图形复用的核心功能，可以显著减少文档大小并提高渲染效率。该类继承自 `SkSVGTransformableNode`，支持完整的变换操作，并实现了延迟引用解析和渲染管道集成。

## 架构位置

`SkSVGUse` 在 Skia SVG 架构中的定位：

- **模块路径**: `modules/svg/include/`
- **继承层次**: `SkSVGNode` → `SkSVGTransformableNode` → `SkSVGUse`
- **功能角色**: 引用节点，实现 SVG 元素的实例化和复用机制
- **W3C 规范**: 实现 SVG 1.1 规范中的 `<use>` 元素 (https://www.w3.org/TR/SVG11/struct.html#UseElement)

在节点层次结构中，`SkSVGUse` 属于结构元素，与 `<g>` 和 `<symbol>` 等元素协同工作，提供灵活的内容组织和复用能力。

## 主要类与结构体

### SkSVGUse 类定义

```cpp
class SK_API SkSVGUse final : public SkSVGTransformableNode {
public:
    // 工厂方法：创建 use 元素实例
    static sk_sp<SkSVGUse> Make();

    // 重写子节点管理（use 元素不直接包含子节点）
    void appendChild(sk_sp<SkSVGNode>) override;

    // 属性定义宏：定义 x, y, href 属性
    SVG_ATTR(X   , SkSVGLength, SkSVGLength(0))
    SVG_ATTR(Y   , SkSVGLength, SkSVGLength(0))
    SVG_ATTR(Href, SkSVGIRI   , SkSVGIRI())

protected:
    // 渲染准备：解析引用并设置上下文
    bool onPrepareToRender(SkSVGRenderContext*) const override;

    // 渲染实现：绘制引用的元素
    void onRender(const SkSVGRenderContext&) const override;

    // 路径转换：获取引用元素的路径表示
    SkPath onAsPath(const SkSVGRenderContext&) const override;

    // 边界框计算：考虑偏移的对象边界框
    SkRect onTransformableObjectBoundingBox(const SkSVGRenderContext&) const override;

private:
    SkSVGUse();
    bool parseAndSetAttribute(const char*, const char*) override;
};
```

### 关键属性

1. **X 和 Y 属性**:
   - 类型: `SkSVGLength`
   - 默认值: `SkSVGLength(0)`
   - 作用: 定义引用元素的偏移位置

2. **Href 属性**:
   - 类型: `SkSVGIRI` (Internationalized Resource Identifier)
   - 默认值: 空引用
   - 作用: 指向被引用元素的 ID

## 公共 API 函数

### static sk_sp<SkSVGUse> Make()

创建 `SkSVGUse` 实例的工厂方法。

**返回值**: 智能指针 `sk_sp<SkSVGUse>`，管理新创建的对象生命周期。

**用途**: 在 SVG DOM 构建过程中，解析到 `<use>` 标签时调用该方法创建节点。

**使用场景**: SVG 解析器遇到 `<use x="10" y="20" href="#myShape"/>` 时创建节点实例。

### void appendChild(sk_sp<SkSVGNode>) override

重写的子节点添加方法，`<use>` 元素不支持直接子节点。

**参数**: `sk_sp<SkSVGNode>` 待添加的子节点（将被忽略或拒绝）

**行为**: 根据实现可能为空操作或断言失败，因为 `<use>` 的内容来自引用而非直接子节点。

### 属性访问器（通过 SVG_ATTR 宏生成）

```cpp
void setX(const SkSVGLength& x);
const SkSVGLength& getX() const;

void setY(const SkSVGLength& y);
const SkSVGLength& getY() const;

void setHref(const SkSVGIRI& href);
const SkSVGIRI& getHref() const;
```

这些方法用于在解析阶段设置属性值，在渲染阶段读取属性值。

## 内部实现细节

### 渲染流程

#### 1. onPrepareToRender

在渲染前调用，执行引用解析和上下文准备：

```cpp
bool onPrepareToRender(SkSVGRenderContext* ctx) const override {
    // 1. 解析 href 引用，查找目标元素
    // 2. 应用 x, y 偏移变换
    // 3. 设置渲染上下文状态
    // 4. 返回 true 表示可以继续渲染，false 表示跳过
}
```

**关键步骤**:
- 从 DOM 树中查找 `href` 指向的元素
- 如果引用无效，返回 `false` 终止渲染
- 在渲染上下文中应用平移变换 `translate(x, y)`
- 可能需要处理循环引用和深度限制

#### 2. onRender

执行实际的渲染操作：

```cpp
void onRender(const SkSVGRenderContext& ctx) const override {
    // 1. 获取引用的目标元素
    // 2. 在当前上下文中渲染目标元素
    // 3. 目标元素继承 use 元素的样式和变换
}
```

**渲染逻辑**:
- 目标元素使用 `<use>` 的表示属性（如 `fill`、`stroke`）
- 应用了 `x`、`y` 偏移后的坐标系统
- 继承 `<use>` 元素的变换矩阵

#### 3. onAsPath

将引用的元素转换为路径表示：

```cpp
SkPath onAsPath(const SkSVGRenderContext& ctx) const override {
    // 1. 获取引用元素的路径
    // 2. 应用 x, y 偏移变换
    // 3. 应用 use 元素自身的变换
    // 4. 返回组合路径
}
```

**用途**: 用于路径操作、碰撞检测、蒙版生成等场景。

#### 4. onTransformableObjectBoundingBox

计算考虑偏移的对象边界框：

```cpp
SkRect onTransformableObjectBoundingBox(const SkSVGRenderContext& ctx) const override {
    // 1. 获取引用元素的边界框
    // 2. 应用 x, y 偏移
    // 3. 不包括 use 元素的 transform 属性
    // 4. 返回变换后的边界框
}
```

**边界框语义**: 遵循 SVG 规范中的对象边界框定义，用于百分比计算和渐变坐标系统。

### 引用解析机制

引用解析通常在渲染准备阶段进行：

1. **IRI 解析**: 将 `href` 属性中的 `#id` 转换为实际的节点指针
2. **循环检测**: 防止 `<use>` 元素直接或间接引用自身
3. **深度限制**: 限制引用链的深度，避免栈溢出
4. **缓存优化**: 可能缓存解析结果以提高多次渲染的性能

### 坐标变换处理

`<use>` 元素涉及多层变换：

```
最终变换 = use.transform × translate(x, y) × 引用元素的内部变换
```

这种变换层次确保了引用元素在正确位置渲染，同时保持其内部结构的完整性。

### 样式继承

`<use>` 元素的样式继承规则：

- **表示属性**: `fill`、`stroke` 等属性从 `<use>` 继承到引用内容
- **几何属性**: 引用元素保留其原始几何属性
- **变换属性**: 叠加而非覆盖

## 依赖关系

### 直接依赖

- **SkSVGTransformableNode**: 父类，提供变换支持
- **SkSVGTypes.h**: 定义 `SkSVGLength` 和 `SkSVGIRI` 类型
- **SkSVGRenderContext**: 渲染上下文，包含 DOM 树访问接口
- **SkPath**: 路径表示和操作
- **SkRect**: 边界框计算

### 系统依赖

- **SVG DOM**: 需要访问文档树以解析 `href` 引用
- **ID 管理系统**: 需要 ID 到节点的映射表
- **渲染管道**: 集成到渲染遍历过程

### 被依赖模块

- **SVG 解析器**: 创建和配置 `SkSVGUse` 实例
- **渲染系统**: 在场景树遍历时调用渲染方法
- **路径提取工具**: 使用 `onAsPath` 获取几何表示

## 设计模式与设计决策

### 代理模式（Proxy Pattern）

`SkSVGUse` 实现了代理模式：

- **代理对象**: `SkSVGUse` 实例
- **真实对象**: 被引用的 SVG 元素
- **透明性**: 渲染时 `SkSVGUse` 表现得像真实元素一样

这种模式允许在不复制数据的情况下实现元素复用。

### 延迟绑定（Lazy Binding）

引用解析采用延迟绑定策略：

- **构建时**: 只存储 `href` 字符串
- **渲染时**: 首次需要时解析引用
- **优势**: 支持前向引用，允许引用在 DOM 树后面定义的元素

### 不可变引用

引用的元素不会被修改，`<use>` 只是创建了一个实例视图：

- **原始元素**: 保持不变，可以被多个 `<use>` 引用
- **实例化**: 每个 `<use>` 创建独立的渲染实例，有自己的位置和样式

### 循环引用防护

实现必须处理潜在的循环引用：

```xml
<defs>
  <g id="a"><use href="#b"/></g>
  <g id="b"><use href="#a"/></g>
</defs>
```

防护措施可能包括：
- 渲染深度计数器
- 已访问节点集合
- 引用链长度限制

## 性能考量

### 内存效率

- **引用语义**: 不复制被引用元素的数据，多个 `<use>` 共享同一份数据
- **小对象**: `SkSVGUse` 本身只存储三个属性，内存占用很小
- **DOM 复用**: 大型图标库可以定义一次，多处使用

### 渲染性能

- **引用解析开销**: 首次渲染时需要查找元素，可通过缓存优化
- **变换组合**: 额外的坐标变换层可能增加矩阵运算
- **样式计算**: 需要合并 `<use>` 和引用元素的样式

### 优化策略

1. **引用缓存**: 缓存已解析的引用，避免重复查找
2. **变换合并**: 在可能的情况下预计算组合变换矩阵
3. **裁剪优化**: 使用边界框快速剔除不可见的 `<use>` 实例

### 潜在瓶颈

- **深度嵌套**: `<use>` 引用另一个包含 `<use>` 的组，可能导致深度递归
- **大量实例**: 数千个 `<use>` 实例可能增加遍历开销
- **动态引用**: 频繁改变 `href` 属性会失效缓存

## 相关文件

### 核心依赖

- **modules/svg/include/SkSVGNode.h**: 节点基类定义
- **modules/svg/include/SkSVGTransformableNode.h**: 可变换节点父类
- **modules/svg/include/SkSVGTypes.h**: `SkSVGLength` 和 `SkSVGIRI` 类型定义

### 实现文件

- **modules/svg/src/SkSVGUse.cpp**: `SkSVGUse` 的具体实现，包含引用解析和渲染逻辑

### 相关节点类型

- **modules/svg/include/SkSVGDefs.h**: `<defs>` 元素，常用于定义被 `<use>` 引用的模板
- **modules/svg/include/SkSVGSymbol.h**: `<symbol>` 元素，专门设计用于被 `<use>` 引用
- **modules/svg/include/SkSVGG.h**: `<g>` 分组元素，经常被 `<use>` 引用

### 渲染相关

- **modules/svg/include/SkSVGRenderContext.h**: 提供 DOM 访问和渲染状态管理
- **modules/svg/src/SkSVGDOM.cpp**: DOM 树管理，提供 ID 查找功能

### 属性解析

- **modules/svg/include/SkSVGAttributeParser.h**: 解析 `x`、`y`、`href` 属性

### 测试和示例

- **modules/svg/tests/**: SVG 模块的单元测试，可能包含 `<use>` 元素的测试用例
- **resources/svg/**: SVG 示例文件，演示 `<use>` 元素的各种用法

该类是 SVG 内容复用机制的核心实现，通过引用和实例化模式提供高效的图形重用能力。
