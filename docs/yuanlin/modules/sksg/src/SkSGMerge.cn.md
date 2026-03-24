# SkSGMerge - 场景图路径合并几何节点

> 源文件: `modules/sksg/src/SkSGMerge.cpp`

## 概述

`SkSGMerge.cpp` 实现了 Skia 场景图 (sksg) 中的 `Merge` 类，用于将多个几何节点的路径通过布尔运算或简单追加的方式合并为一个路径。支持六种合并模式：Merge（追加）、Union（并集）、Intersect（交集）、Difference（差集）、ReverseDifference（反向差集）和 XOR（异或）。该类在 Skottie 中用于实现 After Effects 的 "Merge Paths" 形状修饰器。

该文件包含 118 行代码，核心逻辑在 `onRevalidate` 方法中，使用 `SkOpBuilder` 进行批量路径布尔运算，同时支持简单追加模式的混合使用。

## 架构位置

`Merge` 位于 sksg 模块的几何节点层，继承自 `GeometryNode`。它是一个几何组合器，接收多个子几何节点并将其路径合并为单一路径。在场景图中处于几何节点和绘制节点之间，将复合几何提供给填充或描边等绘制操作。

在 Skottie 的场景图中，`Merge` 节点的典型位置如下：
```
Draw
  ├─ PaintNode (填充/描边)
  └─ Merge (合并后的几何)
       ├─ Rec{GeometryNode, kMerge}     // 第一个形状 (追加)
       ├─ Rec{GeometryNode, kUnion}     // 第二个形状 (并集)
       └─ Rec{GeometryNode, kIntersect} // 第三个形状 (交集)
```

## 主要类与结构体

### `Merge`
```cpp
Merge::Merge(std::vector<Rec>&& recs) : fRecs(std::move(recs)) {
    for (const auto& rec : fRecs) {
        this->observeInval(rec.fGeo);
    }
}
```

### `Merge::Rec`（在头文件中定义）
每条记录包含一个几何节点引用和一个合并模式。

### `Merge::Mode` 枚举
- `kMerge` — 简单路径追加
- `kUnion` — 并集布尔运算
- `kIntersect` — 交集布尔运算
- `kDifference` — 差集布尔运算
- `kReverseDifference` — 反向差集
- `kXOR` — 异或布尔运算

## 公共 API 函数

| 方法 | 说明 |
|------|------|
| `Merge(std::vector<Rec>&&)` | 构造函数，注册所有子几何节点的失效观察 |
| `~Merge()` | 析构函数，取消所有失效观察 |
| `void onClip(SkCanvas*, bool) const` | 使用合并后的路径进行裁剪 |
| `void onDraw(SkCanvas*, const SkPaint&) const` | 绘制合并后的路径 |
| `bool onContains(const SkPoint&) const` | 合并路径的点包含测试 |
| `SkPath onAsPath() const` | 返回合并后的路径 |
| `SkRect onRevalidate(InvalidationController*, const SkMatrix&)` | 执行路径合并并返回边界 |

## 内部实现细节

### 路径合并算法 (`onRevalidate`)
合并算法使用 `SkOpBuilder` 进行批量布尔运算，并通过 `SkPathBuilder` 处理简单的 Merge（追加）操作：

```cpp
for (const auto& rec : fRecs) {
    rec.fGeo->revalidate(ic, ctm);
    if (rec.fMode == Mode::kMerge) {
        append(rec.fGeo->asPath());     // 简单追加
    } else {
        builder.add(rec.fGeo->asPath(), mode_to_op(rec.fMode)); // 布尔运算
    }
}
```

关键流程：
1. 遍历所有记录，先逐一重新验证子几何节点
2. `kMerge` 模式使用 `SkPathBuilder::addPath()` 简单追加路径
3. 布尔运算模式通过 `SkOpBuilder` 批量累积
4. 在遇到 Merge 模式时，先 resolve 之前累积的布尔运算结果，再追加
5. 最终调用 `builder.resolve()` 获取最终结果

### `append` lambda
```cpp
auto append = [&](const SkPath& path) {
    if (in_builder) {
        if (auto result = builder.resolve()) { merger = *result; }
        in_builder = false;
    }
    // 第一个路径决定填充类型
    if (merger.isEmpty()) { merger = path; }
    else { merger.addPath(path); }
};
```

### 模式映射
```cpp
static SkPathOp mode_to_op(Merge::Mode mode) {
    switch (mode) {
    case Merge::Mode::kUnion:             return kUnion_SkPathOp;
    case Merge::Mode::kIntersect:         return kIntersect_SkPathOp;
    case Merge::Mode::kDifference:        return kDifference_SkPathOp;
    case Merge::Mode::kReverseDifference: return kReverseDifference_SkPathOp;
    case Merge::Mode::kXOR:              return kXOR_SkPathOp;
    default:                              return kUnion_SkPathOp;
    }
}
```
将 `Merge::Mode` 映射到 `SkPathOp` 枚举值。`kMerge` 模式不经过此函数（在调用方已被过滤），默认值为 `kUnion_SkPathOp` 作为安全回退。

## 依赖关系

- **直接依赖**:
  - `SkSGMerge.h` — 类声明、`Rec` 结构体和 `Mode` 枚举
  - `SkCanvas.h` — 绘制和裁剪 API
  - `SkClipOp.h` — `kIntersect` 裁剪操作
  - `SkPathBuilder.h` — 路径构建器（用于 Merge 模式的路径追加）
  - `SkPoint.h` — 点类型（用于 `onContains`）
  - `SkPathOps.h` — 布尔路径运算 API（`SkOpBuilder`、`SkPathOp` 枚举）
  - `SkAssert.h` — 断言宏
  - `SkSGNode.h` — 节点基类（`InvalidationController`）
- **前向声明**: `SkMatrix` — 仅在函数签名中使用
- **观察者**: 通过 `observeInval`/`unobserveInval` 监听所有子几何节点的失效事件
- **被使用**: Skottie 中的 "Merge Paths" 形状修饰器

## 设计模式与设计决策

- **组合模式**: `Merge` 组合多个 `GeometryNode` 子节点，将其路径统一为一个几何形状。与 `GeometryEffect`（单子节点装饰器）不同，`Merge` 管理一个可变长度的子节点列表
- **延迟求值**: 路径合并仅在 `onRevalidate` 时执行，利用场景图的失效/重新验证机制避免重复计算。在动画中，如果子节点属性未变化，合并操作会被完全跳过
- **混合策略**: 同一 Merge 节点中可以混合使用 Merge（简单追加）和布尔运算模式。算法通过 `in_builder` 状态标志在两种模式间切换，在遇到 Merge 操作时先 resolve 已累积的布尔运算结果
- **填充类型继承**: 第一个 Merge 路径决定最终路径的填充类型（winding 或 even-odd），后续路径追加到同一 `SkPathBuilder` 中继承此填充规则
- **`SkOpBuilder` vs 逐对 `Op()`**: 选择 `SkOpBuilder` 的批量接口而非逐对执行 `Op()` 函数，因为前者可以在内部进行全局优化，减少中间路径对象的创建
- **`optional` 返回值处理**: `builder.resolve()` 返回 `std::optional<SkPath>`，代码使用 `.value_or(SkPath())` 处理可能的失败情况（例如当所有输入路径为空时）

## 性能考量

- **SkOpBuilder 批量处理**: 使用 `SkOpBuilder` 批量累积布尔运算比逐对执行 `Op()` 更高效。`SkOpBuilder` 可以对多个操作进行全局优化，减少中间路径的分配和计算
- **路径操作开销**: 布尔路径运算 (pathops) 的计算复杂度与路径的几何复杂度成正比，对于包含大量线段或曲线的复杂路径可能成为性能瓶颈。在 Lottie 动画中，形状通常较简单，这不是主要问题
- **紧凑边界计算**: 使用 `computeTightBounds()` 而非 `getBounds()` 获取精确边界。前者遍历所有路径控制点计算精确边界，后者可能返回更松散的包围盒。精确边界减少了后续渲染中不必要的像素处理
- **缓存合并结果**: `fMerged` 路径被缓存在成员变量中，仅在任一子节点失效时重新计算。对于静态或缓慢变化的几何，这避免了每帧重复执行昂贵的路径运算
- **内存分配**: `SkOpBuilder` 和 `SkPathBuilder` 在 `onRevalidate` 中作为局部变量创建，每次重新验证都会分配和释放。对于频繁重新验证的场景，可以考虑将它们缓存为成员变量
- **Merge 模式快速路径**: `kMerge`（简单追加）不使用 `SkOpBuilder`，仅通过 `SkPathBuilder::addPath()` 追加路径，计算开销远低于布尔运算模式

## 相关文件

- `modules/sksg/include/SkSGMerge.h` — 类声明、`Rec` 结构体和 `Mode` 枚举定义
- `include/pathops/SkPathOps.h` — 路径布尔运算 API (`SkOpBuilder`、`Op()`、`SkPathOp`)
- `include/core/SkPathBuilder.h` — 路径构建器
- `include/core/SkClipOp.h` — 裁剪操作枚举
- `modules/sksg/src/SkSGGeometryEffect.cpp` — 其他几何效果节点实现（`OffsetEffect` 也使用 pathops）
- `modules/sksg/include/SkSGGeometryNode.h` — 几何节点基类定义
- `modules/skottie/src/shapes/` — Skottie 形状层中使用 Merge 的代码
