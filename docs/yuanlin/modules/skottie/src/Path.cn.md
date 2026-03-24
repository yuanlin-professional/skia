# Path.cpp

> 源文件: `modules/skottie/src/Path.cpp`

## 概述

`Path.cpp` 实现了 Skottie 动画引擎中路径（Path）属性的动画适配器。该文件定义了 `PathAdapter` 类，负责将 Lottie JSON 中的路径关键帧数据与场景图中的 `sksg::Path` 节点关联起来。路径适配器是形状图层（Shape Layer）中所有路径相关元素（如矩形、椭圆、自由路径等）的基础构建块。

## 架构位置

该文件位于 `modules/skottie/src/` 目录下，属于 Skottie 的内部实现层。在形状图层的构建管线中：

```
Lottie JSON 路径数据 -> AnimationBuilder::attachPath()
    -> PathAdapter (本文件)
    -> sksg::Path 场景图节点
    -> 渲染
```

## 主要类与结构体

### `PathAdapter`
```cpp
class PathAdapter final : public DiscardableAdapterBase<PathAdapter, sksg::Path>
```
- **继承**: `DiscardableAdapterBase<PathAdapter, sksg::Path>`
- **职责**: 将 Lottie 路径关键帧数据同步到 `sksg::Path` 场景图节点。
- **成员**:
  - `fShape`: `ShapeValue` 类型，存储当前帧的路径数据（由关键帧插值器更新）。

## 公共 API 函数

### `AnimationBuilder::attachPath(const skjson::Value&)`
```cpp
sk_sp<sksg::Path> AnimationBuilder::attachPath(const skjson::Value& jpath) const;
```
- **功能**: 从 JSON 路径值创建动画路径节点。
- **参数**: `jpath` -- Lottie JSON 中的路径数据（包含关键帧或静态值）。
- **返回值**: `sk_sp<sksg::Path>` 场景图路径节点。
- **实现**: 委托给 `attachDiscardableAdapter<PathAdapter>(jpath, *this)`，利用模板自动创建适配器并提取节点。

## 内部实现细节

### PathAdapter 构造
```cpp
PathAdapter(const skjson::Value& jpath, const AnimationBuilder& abuilder)
    : INHERITED(sksg::Path::Make()) {
    this->bind(abuilder, jpath, fShape);
}
```
- 创建一个空的 `sksg::Path` 节点。
- 调用 `bind()` 将 JSON 路径数据与 `fShape` 关联，注册关键帧插值器（如果有动画关键帧）。

### onSync() 同步逻辑
```cpp
void onSync() override {
    const auto& path_node = this->node();
    SkPath path = fShape;                          // ShapeValue -> SkPath 隐式转换
    path.setFillType(path_node->getFillType());    // 保留场景图节点的填充类型
    path.setIsVolatile(!this->isStatic());         // 动态路径标记为易变
    path_node->setPath(path);
}
```
- **ShapeValue 转换**: `fShape` 通过 `ShapeValue::operator SkPath()` 隐式转换为 `SkPath`。
- **FillType 保留**: 填充类型（`SkPathFillType`，如 winding/evenodd）存储在场景图节点上而非关键帧中，因此在每次同步时需要从节点读取并重新设置，避免被关键帧插值覆盖。
- **Volatile 标记**: 如果适配器不是静态的（即路径有动画），将 `SkPath` 标记为 volatile，提示 Skia 不要缓存该路径的光栅化结果（因为每帧都会变化）。

## 依赖关系

- **`include/core/SkPath.h`**: `SkPath` 路径类
- **`include/core/SkRefCnt.h`**: 引用计数支持
- **`modules/jsonreader/SkJSONReader.h`**: JSON 值类型
- **`modules/skottie/src/Adapter.h`**: `DiscardableAdapterBase` 基类模板
- **`modules/skottie/src/SkottiePriv.h`**: `AnimationBuilder` 类
- **`modules/skottie/src/SkottieValue.h`**: `ShapeValue` 值类型
- **`modules/sksg/include/SkSGPath.h`**: `sksg::Path` 场景图节点

## 设计模式与设计决策

- **CRTP 适配器**: `PathAdapter` 使用 `DiscardableAdapterBase` 的 CRTP 模式，继承工厂方法和节点管理能力。
- **关注点分离**: FillType 存储在场景图节点上而非关键帧数据中，因为 Lottie 中填充规则是形状的静态属性，不参与关键帧动画。
- **volatile 优化提示**: 动态路径标记为 volatile 是一个向渲染管线传递的优化提示，避免不必要的路径缓存。
- **attachDiscardableAdapter 模板**: `attachPath` 使用 `attachDiscardableAdapter<PathAdapter>` 一行完成适配器创建、节点提取和生命周期管理。

## 性能考量

- **ShapeValue -> SkPath 转换**: 每次 `onSync()` 都会将 `ShapeValue`（float 数组）转换为 `SkPath` 对象，涉及贝塞尔控制点的解析和路径构建。对于复杂路径（大量控制点），这可能有一定开销。
- **Volatile 路径**: 动态路径标记为 volatile，避免 Skia 缓存其光栅化结果（如 GPU 上的距离场或路径蒙版），减少了缓存管理开销但增加了每帧重新光栅化的成本。
- **静态路径优化**: 静态路径的 `PathAdapter` 在构建后被丢弃（`DiscardableAdapterBase` 的可丢弃特性），不占用 `seekFrame` 遍历时间。
- **FillType 保留的开销**: 每次同步需要从节点读取 FillType 再设回，虽然是 O(1) 操作但增加了代码复杂度。

## 相关文件

- `modules/skottie/src/Adapter.h` -- `DiscardableAdapterBase` 基类
- `modules/skottie/src/SkottiePriv.h` -- `AnimationBuilder::attachPath` 声明
- `modules/skottie/src/SkottieValue.h` -- `ShapeValue` 定义
- `modules/sksg/include/SkSGPath.h` -- `sksg::Path` 场景图节点
- `modules/skottie/src/animator/Animator.h` -- `AnimatablePropertyContainer::bind()` 方法
