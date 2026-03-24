# SkSGNodePriv - 场景图节点私有访问辅助类

> 源文件: `modules/sksg/src/SkSGNodePriv.h`

## 概述

`SkSGNodePriv.h` 定义了 `NodePriv` 辅助类，用于在 sksg 模块内部访问 `Node` 类的私有/受保护方法。这是 Skia 中常见的 "Priv" 模式的实现，允许实现代码在不暴露公共 API 的情况下访问节点的内部状态。该文件仅有 27 行，是一个非常精简的内部工具头文件。

在 Skia 场景图的失效/重新验证（invalidation/revalidation）机制中，`NodePriv` 提供了查询节点是否有待处理失效事件的能力，这是场景图增量更新的核心机制之一。

## 架构位置

`NodePriv` 位于 Skia 场景图 (Scene Graph, sksg) 模块的内部实现层。在 sksg 的分层架构中：

- **公共接口层**: `modules/sksg/include/` — 对外暴露的 API
- **内部实现层**: `modules/sksg/src/` — 模块内部使用的辅助代码

`NodePriv` 属于内部实现层，是 `SkSGNode` 类的"友元式"访问桥梁。它用于在模块内部需要查询节点失效状态时提供便捷接口，而不需要将 `hasInval()` 方法暴露为公共 API。该类主要被 `CustomRenderNode` 使用，用于检查子节点是否有未处理的失效标记。

## 主要类与结构体

### `NodePriv`
```cpp
class NodePriv final {
public:
    static bool HasInval(const sk_sp<Node>& node) { return node->hasInval(); }
private:
    NodePriv() = delete;
};
```

关键设计特点：
- **`final` 修饰**: 禁止继承，明确表示这是一个终端工具类
- **设计为不可实例化**: 构造函数被 `delete`，强制仅通过静态方法使用
- **`HasInval()`**: 唯一的静态方法，检查给定节点是否有待处理的失效标记 (invalidation)
- **参数类型**: 接受 `const sk_sp<Node>&`，使用 Skia 的引用计数智能指针

## 公共 API 函数

此文件不提供公共 API。`NodePriv` 是一个纯内部辅助类，所有方法均为模块内部使用。

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `static bool HasInval(const sk_sp<Node>& node)` | 场景图节点的智能指针引用 | `bool` | 检查节点是否含有未处理的失效标记 |

## 内部实现细节

### 失效查询机制

`HasInval()` 方法直接委托给 `Node::hasInval()`，这是 `Node` 类的一个非公开方法。在场景图的生命周期中，节点状态遵循以下流程：

1. 节点的某个属性发生变化
2. 节点调用 `invalidate()` 标记自身需要更新
3. 失效信号沿着场景图向上传播到根节点
4. 在下一帧渲染前，`revalidate()` 从根节点向下清除失效标记并更新缓存数据
5. `hasInval()` 用于查询节点是否处于"已失效但尚未重新验证"的状态

### 使用场景

该方法在 `SkSGRenderNode.cpp` 中被 `CustomRenderNode::hasChildrenInval()` 使用：

```cpp
bool CustomRenderNode::hasChildrenInval() const {
    for (const auto& child : fChildren) {
        if (NodePriv::HasInval(child)) {
            return true;
        }
    }
    return false;
}
```

此方法遍历所有子节点，检查是否有任何子节点存在待处理的失效。这对于自定义渲染节点决定是否需要更新其缓存或重绘内容至关重要。

## 依赖关系

- **直接依赖**: `modules/sksg/include/SkSGNode.h` — 提供 `Node` 基类定义及 `hasInval()` 方法
- **被依赖**: `modules/sksg/src/SkSGRenderNode.cpp` — 在 `CustomRenderNode::hasChildrenInval()` 中使用
- **头文件保护**: 使用 `#ifndef SkSGNodePriv_DEFINED` 防止重复包含
- **命名空间**: 位于 `sksg` 命名空间中

## 设计模式与设计决策

- **Priv 模式 (Private Access Pattern)**: Skia 广泛使用此模式来替代 C++ 的 `friend` 声明。通过一个独立的 `*Priv` 类，将对私有方法的访问集中在一处，使得代码的访问控制更加清晰和可维护。相比 `friend`，Priv 模式有以下优势：
  - 访问权限集中在一个文件中，便于审查
  - 不需要修改被访问类的头文件
  - 可以在 src/ 目录中单独管理，不污染公共 API
- **不可实例化设计**: 通过 `delete` 构造函数，确保该类仅作为静态方法的命名空间使用，避免误用
- **`final` 修饰**: 防止继承，强调这是一个纯工具类
- **内联实现**: 整个类的实现都在头文件中内联完成，无需对应的 `.cpp` 文件

## 性能考量

- **零运行时开销**: 所有方法均为内联的静态函数，在编译时会被完全优化掉，等价于直接调用 `node->hasInval()`
- **O(1) 复杂度**: `HasInval()` 本身仅是一个布尔值检查，不涉及任何遍历或计算
- **编译时零开销**: 头文件仅包含一个头文件依赖 (`SkSGNode.h`)，不会显著增加编译时间
- **无内存分配**: 该类无任何成员变量，不存在实例创建

## 相关文件

- `modules/sksg/include/SkSGNode.h` — `Node` 基类定义，包含 `hasInval()` 和 `invalidate()` 方法
- `modules/sksg/src/SkSGRenderNode.cpp` — 使用 `NodePriv::HasInval` 的实现文件（`CustomRenderNode`）
- `modules/sksg/src/SkSGTransformPriv.h` — 类似的 Priv 模式实现，用于 `Transform` 类的私有方法访问
- `modules/sksg/include/SkSGRenderNode.h` — `CustomRenderNode` 的声明，依赖 `NodePriv` 进行子节点失效检查
