# SkSVGUse 实现

> 源文件: modules/svg/src/SkSVGUse.cpp

## 概述

`SkSVGUse.cpp` 实现了 SVG `<use>` 元素的具体功能，包括引用解析、坐标偏移、渲染代理和路径转换。该实现通过查找和委托被引用元素的渲染逻辑，实现了 SVG 的内容复用机制。核心设计采用代理模式，将实际的渲染工作转发给被引用的目标节点，同时应用 `x` 和 `y` 偏移变换。实现简洁高效，只有 78 行代码，但提供了完整的引用功能。

## 架构位置

该实现文件是 `SkSVGUse` 类的具体实现，位于 SVG 模块的源代码目录：

- **模块路径**: `modules/svg/src/`
- **对应头文件**: `modules/svg/include/SkSVGUse.h`
- **功能层次**: 节点实现层，处理运行时行为
- **交互对象**: `SkSVGRenderContext`（查找引用）、`SkCanvas`（应用变换）、被引用节点（委托渲染）

该文件是 SVG 节点系统的一个典型实现，展示了如何将声明式的 SVG 属性转换为动态的渲染行为。

## 主要类与结构体

该文件只包含 `SkSVGUse` 类的方法实现，没有定义新的类或结构体。

### 实现的方法

1. **SkSVGUse()**: 构造函数
2. **appendChild()**: 子节点管理（禁止添加）
3. **parseAndSetAttribute()**: 属性解析
4. **onPrepareToRender()**: 渲染准备
5. **onRender()**: 渲染执行
6. **onAsPath()**: 路径转换
7. **onTransformableObjectBoundingBox()**: 边界框计算

## 公共 API 函数

### SkSVGUse::SkSVGUse()

构造函数，初始化为 `<use>` 元素类型。

```cpp
SkSVGUse::SkSVGUse() : INHERITED(SkSVGTag::kUse) {}
```

**初始化**: 设置节点标签为 `kUse`，用于类型识别和调试输出。

### void appendChild(sk_sp<SkSVGNode>)

禁止向 `<use>` 元素添加子节点。

```cpp
void SkSVGUse::appendChild(sk_sp<SkSVGNode>) {
    SkDEBUGF("cannot append child nodes to this element.\n");
}
```

**设计决策**: `<use>` 元素的内容来自引用，不应直接包含子节点。该方法在调试构建中输出警告，但不中断程序执行。

### bool parseAndSetAttribute(const char* n, const char* v)

解析 `<use>` 元素的属性。

```cpp
bool SkSVGUse::parseAndSetAttribute(const char* n, const char* v) {
    return INHERITED::parseAndSetAttribute(n, v) ||
           this->setX(SkSVGAttributeParser::parse<SkSVGLength>("x", n, v)) ||
           this->setY(SkSVGAttributeParser::parse<SkSVGLength>("y", n, v)) ||
           this->setHref(SkSVGAttributeParser::parse<SkSVGIRI>("xlink:href", n, v));
}
```

**支持的属性**:
- **x**: 水平偏移（`SkSVGLength` 类型）
- **y**: 垂直偏移（`SkSVGLength` 类型）
- **xlink:href**: 引用 IRI（Internationalized Resource Identifier）

**注意**: 使用 `xlink:href` 而非 `href`，符合 SVG 1.1 规范（SVG 2 支持简化的 `href`）。

## 内部实现细节

### bool onPrepareToRender(SkSVGRenderContext* ctx) const

在渲染前执行准备工作，包括引用验证和偏移变换。

```cpp
bool SkSVGUse::onPrepareToRender(SkSVGRenderContext* ctx) const {
    // 1. 验证引用非空且父类准备成功
    if (fHref.iri().isEmpty() || !INHERITED::onPrepareToRender(ctx)) {
        return false;
    }

    // 2. 如果有偏移，应用平移变换
    if (fX.value() || fY.value()) {
        // 保存画布状态，当局部上下文离开作用域时恢复
        ctx->saveOnce();
        ctx->canvas()->translate(fX.value(), fY.value());
    }

    // TODO: 支持对 <svg> 目标的宽度/高度覆盖

    return true;
}
```

**关键步骤**:

1. **引用验证**: 检查 `href` 是否为空，空引用直接返回 `false`
2. **父类准备**: 调用 `INHERITED::onPrepareToRender()` 处理通用逻辑（样式、变换等）
3. **偏移应用**: 如果 `x` 或 `y` 非零，应用平移变换
4. **状态保存**: 使用 `saveOnce()` 确保画布状态正确保存和恢复

**性能优化**: 只在有偏移时才调用 `saveOnce()` 和 `translate()`，避免不必要的画布操作。

**未完成功能**: 注释中提到的 `width`/`height` 覆盖功能尚未实现，这是 SVG 规范中的高级特性。

### void onRender(const SkSVGRenderContext& ctx) const

执行实际的渲染操作，通过委托给被引用节点。

```cpp
void SkSVGUse::onRender(const SkSVGRenderContext& ctx) const {
    // 1. 从上下文查找被引用的节点
    const auto ref = ctx.findNodeById(fHref);
    if (!ref) {
        return;  // 引用无效，静默失败
    }

    // 2. 委托渲染给被引用节点
    ref->render(ctx);
}
```

**渲染流程**:

1. **引用查找**: 调用 `ctx.findNodeById()` 根据 IRI 查找目标节点
2. **有效性检查**: 如果引用无效（节点不存在），静默返回
3. **委托渲染**: 调用目标节点的 `render()` 方法，传递当前上下文

**上下文继承**: 被引用节点使用相同的 `SkSVGRenderContext`，因此继承了：
- 当前的画布变换（包括 `x`、`y` 偏移）
- 样式属性（从 `<use>` 继承）
- 裁剪路径和蒙版

### SkPath onAsPath(const SkSVGRenderContext& ctx) const

将 `<use>` 元素转换为路径表示。

```cpp
SkPath SkSVGUse::onAsPath(const SkSVGRenderContext& ctx) const {
    // 1. 查找被引用节点
    const auto ref = ctx.findNodeById(fHref);
    if (!ref) {
        return SkPath();  // 返回空路径
    }

    // 2. 获取被引用节点的路径
    return ref->asPath(ctx);
}
```

**注意**: 该方法**不应用**偏移变换。偏移由父类的 `mapToParent()` 在更高层次处理。

**用途**:
- 裁剪路径定义
- 路径操作（布尔运算）
- 碰撞检测
- 蒙版生成

### SkRect onTransformableObjectBoundingBox(const SkSVGRenderContext& ctx) const

计算考虑偏移的对象边界框。

```cpp
SkRect SkSVGUse::onTransformableObjectBoundingBox(const SkSVGRenderContext& ctx) const {
    // 1. 查找被引用节点
    const auto ref = ctx.findNodeById(fHref);
    if (!ref) {
        return SkRect::MakeEmpty();
    }

    // 2. 解析偏移值
    const SkSVGLengthContext& lctx = ctx.lengthContext();
    const SkScalar x = lctx.resolve(fX, SkSVGLengthContext::LengthType::kHorizontal);
    const SkScalar y = lctx.resolve(fY, SkSVGLengthContext::LengthType::kVertical);

    // 3. 获取被引用节点的边界框并应用偏移
    SkRect bounds = ref->objectBoundingBox(ctx);
    bounds.offset(x, y);

    return bounds;
}
```

**实现细节**:

1. **引用查找**: 获取目标节点，失败时返回空矩形
2. **偏移解析**: 使用长度上下文将 `SkSVGLength` 转换为像素值
3. **边界框获取**: 调用目标节点的 `objectBoundingBox()`
4. **偏移应用**: 使用 `offset()` 平移边界框

**用途**: 对象边界框用于：
- 百分比单位计算（如渐变坐标）
- 滤镜区域定义
- 布局和对齐
- 交互式编辑器中的选择框

## 依赖关系

### Skia 核心依赖

- **include/core/SkCanvas.h**: 画布变换操作（`translate()`）
- **include/core/SkScalar.h**: 浮点数类型定义

### SVG 模块依赖

- **modules/svg/include/SkSVGUse.h**: 类声明
- **modules/svg/include/SkSVGAttributeParser.h**: 属性解析
- **modules/svg/include/SkSVGRenderContext.h**: 渲染上下文，提供节点查找和长度解析

### 调试依赖

- **include/private/base/SkDebug.h**: 调试输出宏（`SkDEBUGF`）

## 设计模式与设计决策

### 代理模式（Proxy Pattern）

`SkSVGUse` 是一个经典的代理实现：

**代理对象**: `SkSVGUse` 实例
**真实对象**: 被引用的 SVG 节点
**代理职责**:
- 管理对真实对象的引用（`fHref`）
- 应用额外的变换（`x`、`y` 偏移）
- 委托所有实际工作给真实对象

这种设计实现了对象复用，同时保持了实现的简洁性。

### 延迟绑定（Lazy Binding）

引用解析发生在渲染时而非构建时：

```cpp
const auto ref = ctx.findNodeById(fHref);
```

**优势**:
- 支持前向引用（引用后定义的元素）
- 允许动态修改文档结构
- 减少初始化时间

**劣势**:
- 每次渲染都需要查找（可通过缓存优化）
- 无法在构建时检测无效引用

### 静默失败

当引用无效时，方法静默返回而不抛出异常：

```cpp
if (!ref) {
    return;  // 或返回空路径/空矩形
}
```

**设计理由**:
- 符合 Web 容错原则
- 避免单个错误影响整个文档渲染
- 简化错误处理逻辑

生产环境中可能需要添加警告日志。

### 条件变换

只在必要时应用偏移变换：

```cpp
if (fX.value() || fY.value()) {
    ctx->saveOnce();
    ctx->canvas()->translate(fX.value(), fY.value());
}
```

**性能优化**: 避免不必要的画布状态保存和恢复操作。

## 性能考量

### 引用查找开销

`ctx.findNodeById()` 可能涉及：
- 哈希表查找（O(1) 平均情况）
- 或树遍历（O(n) 最坏情况）

**优化策略**:
- 实现节点缓存
- 使用哈希映射存储 ID 到节点的映射
- 在文档构建时预计算引用表

### 画布状态管理

`saveOnce()` 和自动恢复：

```cpp
ctx->saveOnce();  // 延迟保存
// ... 渲染操作 ...
// 上下文析构时自动恢复
```

**成本**: 每次 `save()`/`restore()` 涉及状态拷贝，对于深度嵌套的 `<use>` 可能累积。

### 委托开销

每次调用 `ref->render(ctx)` 涉及：
- 虚函数调用开销
- 被引用节点的完整渲染管道

对于复杂的被引用内容，这是合理的；对于简单形状，可能考虑内联优化。

### 边界框计算

`objectBoundingBox()` 可能递归计算子树：

```cpp
SkRect bounds = ref->objectBoundingBox(ctx);
```

对于复杂的被引用树，可能需要缓存边界框结果。

## 相关文件

### 头文件

- **modules/svg/include/SkSVGUse.h**: 类声明和公共接口

### 渲染上下文

- **modules/svg/include/SkSVGRenderContext.h**: 提供 `findNodeById()` 和长度解析
- **modules/svg/src/SkSVGRenderContext.cpp**: 上下文实现，包括节点查找逻辑

### 基类

- **modules/svg/include/SkSVGTransformableNode.h**: 可变换节点基类
- **modules/svg/src/SkSVGTransformableNode.cpp**: 变换处理实现

### 相关元素

- **modules/svg/src/SkSVGDefs.cpp**: `<defs>` 元素，常用于定义被引用的内容
- **modules/svg/src/SkSVGSymbol.cpp**: `<symbol>` 元素，专为 `<use>` 引用设计
- **modules/svg/src/SkSVGG.cpp**: `<g>` 分组元素，经常被 `<use>` 引用

### 属性解析

- **modules/svg/src/SkSVGAttributeParser.cpp**: 实现 `SkSVGLength` 和 `SkSVGIRI` 解析

### 测试

- **modules/svg/tests/**: SVG 单元测试，应包括 `<use>` 元素的测试用例

### 使用示例

**基本引用**:
```xml
<defs>
  <circle id="dot" cx="5" cy="5" r="5" fill="blue"/>
</defs>
<use href="#dot" x="10" y="20"/>
<use href="#dot" x="30" y="40"/>
```

**引用组**:
```xml
<defs>
  <g id="icon">
    <rect width="10" height="10"/>
    <circle cx="5" cy="5" r="3"/>
  </g>
</defs>
<use href="#icon" x="0" y="0"/>
```

**嵌套引用**:
```xml
<defs>
  <g id="pattern">
    <use href="#dot" x="0" y="0"/>
    <use href="#dot" x="10" y="0"/>
  </g>
</defs>
<use href="#pattern" x="0" y="0"/>
```

该实现简洁高效，通过代理模式和延迟绑定实现了 SVG 内容复用的核心功能。
