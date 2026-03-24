# SkSGPath -- 路径几何节点

> 源文件: `modules/sksg/include/SkSGPath.h`

## 概述

`SkSGPath.h` 定义了 Skia Scene Graph 中的路径几何节点 `Path`。该节点是 `SkPath` 的场景图包装器，是最基本也是最通用的几何节点之一。它允许在场景图中使用任意的 Skia 路径，支持动态修改路径数据和填充类型，并通过场景图的失效/重新验证机制实现高效的增量更新。

## 架构位置

```
Node
└── GeometryNode
    ├── Path  ← 当前文件
    ├── Rect
    ├── RRect
    ├── Plane
    ├── Text
    └── GeometryEffect (效果链)
```

`Path` 是最灵活的叶几何节点，可以表示任意形状。它常作为几何效果链的起始节点，也是 Lottie 动画中矢量形状的主要载体。与 `Rect`/`RRect` 等专用几何节点相比，`Path` 更通用但也更重量级。

## 主要类与结构体

### `Path`
```cpp
class Path final : public GeometryNode {
public:
    static sk_sp<Path> Make();
    static sk_sp<Path> Make(const SkPath& r);

    SG_ATTRIBUTE(Path, SkPath, fPath)

    SkPathFillType getFillType() const;
    void setFillType(SkPathFillType fillType);

protected:
    void onClip(SkCanvas*, bool antiAlias) const override;
    void onDraw(SkCanvas*, const SkPaint&) const override;
    bool onContains(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;
    SkPath onAsPath() const override;

private:
    explicit Path(const SkPath&);
    SkPath fPath;
};
```

## 公共 API 函数

### `Path::Make()`
创建空路径节点。

### `Path::Make(const SkPath& r)`
创建包含指定路径数据的节点。

### `getPath() / setPath(const SkPath&)`
通过 `SG_ATTRIBUTE(Path, SkPath, fPath)` 自动生成的路径数据访问器。`setPath` 在路径实际发生变化时触发节点失效。

### `getFillType() / setFillType(SkPathFillType)`
手动内联实现的填充类型访问器（注释说明是为 `SkPathFillType` 暂存阶段临时内联的）。`setFillType` 在填充类型变化时直接修改内部路径的填充类型并触发失效。

## 内部实现细节

- **FillType 特殊处理**：代码注释指出 `SG_MAPPED_ATTRIBUTE(FillType, SkPathFillType, fPath)` 是被注释掉的原始实现，当前使用内联的 getter/setter 替代。这是因为 `SkPathFillType` 的 staging（过渡期）API 变化导致的临时方案。

- **GeometryNode 接口**：
  - `onClip` -- 将路径设为 Canvas 裁剪区域
  - `onDraw` -- 使用路径绘制到 Canvas
  - `onContains` -- 路径点包含测试
  - `onRevalidate` -- 返回路径的边界矩形
  - `onAsPath` -- 直接返回内部路径的拷贝

- `fPath` 直接存储 `SkPath` 对象，没有额外的缓存层（路径本身就是最终的几何表示）。

## 依赖关系

- `include/core/SkPath.h` -- 核心路径类
- `include/core/SkPathTypes.h` -- `SkPathFillType` 枚举
- `modules/sksg/include/SkSGGeometryNode.h` -- 基类
- `modules/sksg/include/SkSGNode.h` -- SG_ATTRIBUTE 宏

## 设计模式与设计决策

1. **轻量包装器**：Path 节点是 SkPath 的轻量场景图包装，几乎没有额外开销。所有几何操作直接委托给内部的 SkPath。

2. **双工厂方法**：提供无参和有参两个 Make 方法，空路径版本方便后续通过 setPath 动态设置。

3. **FillType 独立访问**：将填充类型作为独立的属性暴露（而非只通过 setPath 间接设置），允许在不替换整个路径的情况下更改填充规则。

4. **SG_ATTRIBUTE 值比较**：`setPath` 使用 SkPath 的 `operator==` 进行比较，只有路径真正变化时才触发失效，避免无谓的重新验证。

## 性能考量

- `SkPath::operator==` 的比较可能较慢（需要逐点比较），对于频繁更新的动画路径，这个检查本身可能成为瓶颈。
- `onAsPath` 返回路径拷贝，SkPath 使用写时复制（COW）语义，拷贝通常是廉价的。
- 路径的边界矩形由 SkPath 内部缓存，`onRevalidate` 不需要重新计算。
- 作为叶节点，Path 的 revalidate 非常轻量，主要开销在于调用方获取 SkPath 时的逻辑。

## 相关文件

- `modules/sksg/src/SkSGPath.cpp` -- Path 节点的实现
- `modules/sksg/include/SkSGGeometryNode.h` -- GeometryNode 基类
- `modules/sksg/include/SkSGGeometryEffect.h` -- 可应用于 Path 的几何效果
- `modules/sksg/include/SkSGDraw.h` -- Draw 节点
- `modules/sksg/include/SkSGRect.h` -- 同级的矩形几何节点
