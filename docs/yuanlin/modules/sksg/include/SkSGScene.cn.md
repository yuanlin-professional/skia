# SkSGScene -- 场景图根节点容器

> 源文件: `modules/sksg/include/SkSGScene.h`

## 概述

`SkSGScene.h` 定义了 Skia Scene Graph 模块的顶层入口类 `Scene`。`Scene` 持有场景图的根渲染节点（`RenderNode`），并提供高层级的渲染（`render`）、重新验证（`revalidate`）和命中测试（`nodeAt`）接口。它是客户端与场景图交互的主要门面（Facade），封装了场景图遍历和状态管理的复杂性。

## 架构位置

`Scene` 位于 sksg 架构的最顶层，是客户端代码与场景图 DAG 之间的桥梁：

```
客户端代码
    ↓
  Scene  ← 顶层门面
    ↓
  RenderNode (root)
    ↓
  [场景图 DAG: Group, EffectNode, Draw, ...]
```

客户端通过 `Scene` 进行渲染和命中测试，无需直接操作场景图的内部节点遍历机制。`Scene` 使用 `std::unique_ptr` 管理生命周期，表明每个场景拥有唯一的所有权。

## 主要类与结构体

### `Scene`
```cpp
class Scene final {
public:
    static std::unique_ptr<Scene> Make(sk_sp<RenderNode> root);
    ~Scene();
    Scene(const Scene&) = delete;
    Scene& operator=(const Scene&) = delete;

    void render(SkCanvas*) const;
    void revalidate(InvalidationController* = nullptr);
    const RenderNode* nodeAt(const SkPoint&) const;

private:
    explicit Scene(sk_sp<RenderNode> root);
    const sk_sp<RenderNode> fRoot;
};
```

`Scene` 被标记为 `final`，不可继承。禁用了拷贝构造和赋值，强制唯一所有权。根节点以 `const sk_sp<RenderNode>` 存储，创建后不可替换。

## 公共 API 函数

### `Scene::Make(root)`
工厂方法，创建一个持有指定根节点的 Scene 实例。返回 `std::unique_ptr<Scene>`，明确表达所有权语义。

### `Scene::render(canvas)`
将整个场景图渲染到指定的 `SkCanvas` 上。调用根节点的 `render()` 方法，触发整个 DAG 的递归渲染。此方法为 `const`，渲染不改变场景状态。

### `Scene::revalidate(ic)`
对场景图进行重新验证，更新所有失效节点的缓存数据和边界信息。可选地接受一个 `InvalidationController` 来收集失效区域。通常在渲染之前调用。

### `Scene::nodeAt(point)`
在指定位置进行前向到后向的命中测试，返回位于该点的 `RenderNode`。用于实现交互功能如点击检测。

## 内部实现细节

- 构造函数为 `private`，只能通过 `Make` 工厂方法创建，确保参数有效性检查。
- `fRoot` 为 `const`，场景创建后根节点不可更改，保证结构稳定性。
- `revalidate` 的 `InvalidationController` 参数默认为 `nullptr`，表示不收集失效区域信息。
- `render` 为 `const` 方法，意味着渲染过程不修改场景图状态（所有状态更新应在 `revalidate` 中完成）。

## 依赖关系

- `include/core/SkRefCnt.h` -- `sk_sp` 智能指针
- `include/core/SkTypes.h` -- Skia 基础类型
- `modules/sksg/include/SkSGRenderNode.h` -- 根节点类型 `RenderNode`（前向声明）
- `modules/sksg/include/SkSGInvalidationController.h` -- 失效控制器（前向声明）

## 设计模式与设计决策

1. **门面模式 (Facade)**：Scene 封装了场景图遍历的复杂性，提供简洁的 render/revalidate/nodeAt 三个高层接口。

2. **不可拷贝的唯一所有权**：使用 `unique_ptr` + 删除拷贝操作，明确每个 Scene 实例独占其根节点。

3. **验证与渲染分离**：`revalidate` 和 `render` 分为两个独立步骤，允许客户端在渲染前执行验证并收集失效信息，也支持只验证不渲染的场景。

4. **工厂方法模式**：私有构造函数 + 静态 `Make` 方法，统一对象创建入口。

## 性能考量

- Scene 本身几乎没有性能开销，只是一个轻量级的根节点包装器。
- `revalidate` 利用场景图的增量失效机制，只更新实际发生变化的节点子树。
- `render` 的性能取决于场景图的复杂度和 Canvas 后端。
- `nodeAt` 执行前向到后向遍历，最坏情况需要遍历所有叶节点。

## 相关文件

- `modules/sksg/src/SkSGScene.cpp` -- Scene 的实现文件
- `modules/sksg/include/SkSGRenderNode.h` -- RenderNode 基类
- `modules/sksg/include/SkSGInvalidationController.h` -- 失效区域收集器
- `modules/sksg/slides/SVGPongSlide.cpp` -- Scene 使用示例（Pong 游戏）
