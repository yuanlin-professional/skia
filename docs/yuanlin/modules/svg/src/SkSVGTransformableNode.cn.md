# SkSVGTransformableNode

> 源文件: [modules/svg/src/SkSVGTransformableNode.cpp](../../../../modules/svg/src/SkSVGTransformableNode.cpp)

## 概述

`SkSVGTransformableNode` 实现了 SVG 中支持 `transform` 属性的节点基类。该类管理变换矩阵（`SkMatrix`），在渲染前将变换应用到画布，并提供路径和矩形从本地坐标系映射到父坐标系的功能。它是所有可变换 SVG 元素（如 `<g>`、`<rect>`、`<circle>`、`<image>` 等）的共同基类。

## 架构位置

```
SkSVGNode (所有 SVG 节点的基类)
  └── SkSVGTransformableNode  ← 本文件实现
        ├── SkSVGContainer (容器节点)
        ├── SkSVGShape (形状节点)
        ├── SkSVGImage (图像节点)
        └── ... (其他可变换节点)
```

`SkSVGTransformableNode` 是 SVG 节点层次结构中的关键中间层，为所有需要几何变换的节点提供统一的变换处理机制。

## 主要类与结构体

### SkSVGTransformableNode
- 继承自 `INHERITED`（`SkSVGNode`）
- 持有 `fTransform`（`SkMatrix` 类型），默认为单位矩阵
- 提供渲染前变换应用、属性设置、坐标映射和边界框计算

## 公共 API 函数

### 构造函数
```cpp
SkSVGTransformableNode(SkSVGTag tag);
```
初始化标签并将变换矩阵设为单位矩阵 `SkMatrix::I()`。

### `onPrepareToRender`
```cpp
bool onPrepareToRender(SkSVGRenderContext* ctx) const;
```
渲染准备阶段：若变换非单位矩阵，则保存渲染上下文并将变换连接（concat）到画布上。随后委托基类继续准备。

### `onSetAttribute`
```cpp
void onSetAttribute(SkSVGAttribute attr, const SkSVGValue& v);
```
处理 `kTransform` 属性的设置，将 `SkSVGTransformValue` 值应用到内部变换矩阵。

### `mapToParent`（路径版本）
```cpp
SkPath mapToParent(const SkPath& path) const;
```
使用当前变换矩阵将路径从本地坐标系映射到父坐标系。

### `mapToParent`（矩形版本）
```cpp
SkRect mapToParent(const SkRect& rect) const;
```
使用当前变换矩阵将矩形从本地坐标系映射到父坐标系。

### `onTransformableObjectBoundingBox`
```cpp
SkRect onTransformableObjectBoundingBox(const SkSVGRenderContext&) const;
```
默认实现，返回空矩形。子类应重写以提供实际的对象边界框。

### `onObjectBoundingBox`
```cpp
SkRect onObjectBoundingBox(const SkSVGRenderContext& ctx) const;
```
获取对象边界框，并在必要时应用变换映射到父坐标系。通过 `ctx.currentOBBScope().fNode` 检查是否需要变换（避免在自身 OBB 作用域内重复变换）。

## 内部实现细节

### 变换应用时机

`onPrepareToRender` 中使用惰性保存策略 `ctx->saveOnce()`，仅在变换非单位矩阵时保存上下文。这避免了不必要的状态保存/恢复操作。变换通过 `ctx->canvas()->concat(fTransform)` 应用到画布的当前变换栈上。

### OBB 作用域检查

`onObjectBoundingBox` 中的条件判断 `ctx.currentOBBScope().fNode != this` 用于处理以下场景：当节点正在计算自身的 OBB（如 `objectBoundingBox` 属性引用自身时），不应对边界框应用自身的变换。只有当在父级或其他外部上下文中请求边界框时，才应用变换。

### 属性处理

`onSetAttribute` 使用旧式的 `SkSVGValue` 类型系统（通过 `v.as<SkSVGTransformValue>()`）处理 transform 属性。这是 SVG 模块中较早的属性设置路径，与新式的 `parseAndSetAttribute` 字符串解析路径并存。

## 依赖关系

- **Skia 核心**: `SkCanvas`、`SkRect`、`SkMatrix`（通过 `SkPath::makeTransform` 和 `SkMatrix::mapRect`）
- **SVG 模块**: `SkSVGNode`（基类）、`SkSVGAttribute`、`SkSVGRenderContext`、`SkSVGValue`

## 设计模式与设计决策

1. **模板方法模式**: `onPrepareToRender` 在应用自身变换后调用基类的 `onPrepareToRender`，形成一条变换链，子类可以在此链条中插入额外的准备逻辑。

2. **惰性状态保存**: 通过 `saveOnce()` 和 `isIdentity()` 检查实现惰性保存，对于没有变换的节点（常见情况）完全跳过 save/restore 操作。

3. **坐标系映射抽象**: `mapToParent` 提供了从本地坐标系到父坐标系的统一映射接口，路径和矩形各有一个重载版本。

4. **双路径属性设置**: 同时支持旧式 `onSetAttribute`（`SkSVGValue` 类型）和新式 `parseAndSetAttribute`（字符串解析），确保向后兼容。

## 性能考量

- 单位矩阵检查（`isIdentity()`）避免了大多数节点不必要的画布变换操作。
- `SkPath::makeTransform` 创建路径的变换副本，对复杂路径可能有一定开销，但 `onAsPath` 不在常规渲染路径中。
- `SkMatrix::mapRect` 是轻量级操作，仅涉及简单的矩阵-矩形乘法。

## 相关文件

- `modules/svg/include/SkSVGTransformableNode.h` - 类声明
- `modules/svg/include/SkSVGNode.h` - 节点基类
- `modules/svg/include/SkSVGAttribute.h` - SVG 属性枚举
- `modules/svg/include/SkSVGValue.h` - SVG 属性值类型
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文
- `modules/svg/src/SkSVGContainer.cpp` - 容器节点（继承自本类）
