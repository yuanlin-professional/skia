# Adapter.h

> 源文件: `modules/skottie/src/Adapter.h`

## 概述

`Adapter.h` 定义了 Skottie 动画引擎中的适配器基类模板 `DiscardableAdapterBase`。该模板是 Skottie 内部最重要的基础设施之一，它将动画属性容器（`AnimatablePropertyContainer`）与场景图节点关联起来，实现了 Lottie 动画属性值到 Skia 场景图节点属性的自动同步。"Discardable"（可丢弃）特性意味着静态（无动画关键帧）的适配器在初始同步后可以被安全释放，从而减少运行时的内存和遍历开销。

## 架构位置

该文件位于 `modules/skottie/src/` 目录下，属于 Skottie 的内部实现层。`DiscardableAdapterBase` 在适配器层次结构中位于中间位置：

```
AnimatablePropertyContainer (animator/Animator.h)
         |
DiscardableAdapterBase<AdapterT, T> (本文件)
         |
   具体适配器 (OpacityAdapter, PathAdapter, ColorAdapter, ...)
         |
   场景图节点 (sksg::OpacityEffect, sksg::Path, sksg::Color, ...)
```

## 主要类与结构体

### `DiscardableAdapterBase<AdapterT, T>`
```cpp
template <typename AdapterT, typename T>
class DiscardableAdapterBase : public AnimatablePropertyContainer
```
- **模板参数**:
  - `AdapterT`: 具体适配器类型（CRTP 模式）
  - `T`: 关联的场景图节点类型
- **继承**: `AnimatablePropertyContainer`（动画属性容器基类，来自 `Animator.h`）
- **职责**: 为具体适配器提供统一的工厂方法、节点访问和生命周期管理。

## 公共 API 函数

### `Make(Args&&... args)`
```cpp
template <typename... Args>
static sk_sp<AdapterT> Make(Args&&... args);
```
- **功能**: 工厂方法，创建具体适配器实例。
- **实现**: 使用 `new AdapterT(std::forward<Args>(args)...)` 创建实例，然后调用 `shrink_to_fit()` 优化内存使用。
- **说明**: 使用 CRTP（Curiously Recurring Template Pattern）实现静态多态，返回正确的具体类型。

### `node() const`
```cpp
const sk_sp<T>& node() const;
```
- **功能**: 获取关联的场景图节点。
- **返回**: 节点的 `sk_sp` 常量引用。

## 内部实现细节

- **CRTP 模式**: `DiscardableAdapterBase<AdapterT, T>` 中的 `AdapterT` 是具体子类自身，这允许 `Make()` 直接 `new AdapterT(...)`，无需虚函数即可实现多态工厂。
- **两种构造方式**:
  - 默认构造: `DiscardableAdapterBase()` -- 调用 `T::Make()` 创建默认节点
  - 显式构造: `DiscardableAdapterBase(sk_sp<T> node)` -- 使用提供的节点
- **shrink_to_fit()**: `Make()` 工厂方法在构建适配器后调用 `shrink_to_fit()`（来自 `AnimatablePropertyContainer`），释放属性绑定列表中多余的内存。
- **可丢弃语义**: 通过 `isStatic()` 方法（继承自基类）判断适配器是否为静态。静态适配器可以在一次 `seek(0)` 同步后被丢弃，因为其值永远不变。这在 `AnimationBuilder::attachDiscardableAdapter` 中实现。

## 依赖关系

- **`modules/skottie/src/animator/Animator.h`**: 基类 `AnimatablePropertyContainer`，提供属性绑定、seek 和静态检测能力。

## 设计模式与设计决策

- **CRTP（奇异递归模板模式）**: 使 `Make()` 能直接构造正确的具体类型，避免了虚函数调度的开销。
- **模板方法模式**: 基类定义了构造和节点管理的框架，具体适配器只需实现 `onSync()`（在基类的 `seek()` 中被调用）来定义同步逻辑。
- **静态工厂方法**: 统一使用 `Make()` 而非公共构造函数创建实例，确保 `shrink_to_fit()` 始终被调用。
- **可丢弃设计**: 通过区分静态和动态适配器，优化了运行时的动画器遍历——静态适配器不会被添加到动画器列表中。
- **最小化接口**: 该模板仅暴露 `Make()` 和 `node()` 两个公共方法，保持接口的简洁性。

## 性能考量

- **shrink_to_fit**: 在构造后立即释放多余的属性绑定内存，对于大型动画（数百个适配器）有显著的内存节省。
- **静态适配器丢弃**: 大量 Lottie 属性是静态的（无动画关键帧），将这些适配器从运行时遍历列表中移除，可以显著减少 `seekFrame()` 的执行时间。
- **零虚函数开销**: CRTP 避免了工厂方法中的虚函数调用，虽然 `AnimatablePropertyContainer` 本身有虚函数 (`onSync`)。
- **引用返回**: `node()` 返回 `const sk_sp<T>&` 而非值拷贝，避免引用计数操作。

## 相关文件

- `modules/skottie/src/animator/Animator.h` -- `AnimatablePropertyContainer` 基类
- `modules/skottie/src/Skottie.cpp` -- `OpacityAdapter` 等具体适配器的实现
- `modules/skottie/src/Path.cpp` -- `PathAdapter` 的实现
- `modules/skottie/src/SkottiePriv.h` -- `AnimationBuilder::attachDiscardableAdapter` 使用该模板
- `modules/sksg/include/SkSGPath.h` -- 场景图路径节点（常见的 T 参数类型之一）
