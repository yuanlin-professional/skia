# SkSGTransform 实现 -- 场景图变换节点实现

> 源文件: `modules/sksg/src/SkSGTransform.cpp`

## 概述

`SkSGTransform.cpp` 实现了 Skia Scene Graph 变换体系的完整运行时逻辑，包括模板特化的矩阵转换、内部的 `Concat`（组合变换）和 `Inverse`（逆变换）类、`Transform` 基类的工厂方法以及 `TransformEffect` 的渲染和验证逻辑。这个文件是 sksg 变换系统的核心实现，处理了 2D（SkMatrix）和 3D（SkM44）矩阵类型之间的转换和组合。

## 架构位置

本文件实现了 `SkSGTransform.h` 中声明的所有类的行为逻辑。在 sksg 的编译单元中，它提供了：

- `Matrix<SkMatrix>` 和 `Matrix<SkM44>` 的模板特化
- `Concat<T>` 和 `Inverse<T>` 两个匿名命名空间内部类
- `Transform` 基类的静态工厂方法
- `TransformEffect` 的渲染、命中测试和验证实现

## 主要类与结构体

### `Concat<T>` (匿名命名空间)
```cpp
template <typename T>
class Concat final : public Transform {
    const sk_sp<Transform> fA, fB;
    T fComposed;  // 缓存的组合结果
protected:
    SkRect onRevalidate(InvalidationController* ic, const SkMatrix& ctm) override;
    SkMatrix asMatrix() const override;
    SkM44 asM44() const override;
};
```
变换组合节点，持有两个子变换 A 和 B，在 revalidate 时计算 `fComposed = A * B` 并缓存。根据 `T` 的类型决定使用 3x3 还是 4x4 矩阵运算。

### `Inverse<T>` (匿名命名空间)
```cpp
template <typename T>
class Inverse final : public Transform {
    const sk_sp<Transform> fT;
    T fInverted;  // 缓存的逆矩阵
protected:
    SkRect onRevalidate(InvalidationController* ic, const SkMatrix& ctm) override;
    SkMatrix asMatrix() const override;
    SkM44 asM44() const override;
};
```
逆变换节点，持有源变换 T，在 revalidate 时计算其逆矩阵并缓存。如果矩阵不可逆，回退为单位矩阵。

### 辅助模板函数
```cpp
template <typename T> SkMatrix AsSkMatrix(const T&);
template <typename T> SkM44 AsSkM44(const T&);
```
类型转换辅助函数，处理 SkMatrix <-> SkM44 之间的双向转换。

## 公共 API 函数

### `Transform::MakeConcat(a, b)`
实现了组合变换的创建逻辑：
1. 如果 `a` 为空，返回 `b`（反之亦然）
2. 如果 `a` 或 `b` 任一为 4x4 类型（`TransformPriv::Is44`），创建 `Concat<SkM44>`
3. 否则创建 `Concat<SkMatrix>`

### `Transform::MakeInverse(t)`
实现了逆变换的创建逻辑：
1. 如果 `t` 为空，返回 nullptr
2. 根据 `t` 的类型创建 `Inverse<SkM44>` 或 `Inverse<SkMatrix>`

## 内部实现细节

### 矩阵类型转换特化

```cpp
template <> SkMatrix AsSkMatrix<SkMatrix>(const SkMatrix& m) { return m; }     // 恒等
template <> SkMatrix AsSkMatrix<SkM44>(const SkM44& m) { return m.asM33(); }   // 4x4 -> 3x3
template <> SkM44 AsSkM44<SkMatrix>(const SkMatrix& m) { return SkM44(m); }    // 3x3 -> 4x4
template <> SkM44 AsSkM44<SkM44>(const SkM44& m) { return m; }                 // 恒等
```

### Matrix<T> 模板特化

```cpp
template <> SkMatrix Matrix<SkMatrix>::asMatrix() const { return fMatrix; }
template <> SkM44    Matrix<SkMatrix>::asM44()    const { return SkM44(fMatrix); }
template <> SkMatrix Matrix<SkM44>::asMatrix()    const { return fMatrix.asM33(); }
template <> SkM44    Matrix<SkM44>::asM44()       const { return fMatrix; }
```
四种组合的特化实现，处理存储类型与请求类型之间的转换。

### Transform 基类构造

```cpp
Transform::Transform() : INHERITED(kBubbleDamage_Trait) {}
```
Transform 节点使用 `kBubbleDamage_Trait`，表示自身不直接生成损坏区域，而是通过祖先 TransformEffect 传播。

### TransformEffect 渲染

```cpp
void TransformEffect::onRender(SkCanvas* canvas, const RenderContext* ctx) const {
    SkAutoCanvasRestore acr(canvas, true);
    canvas->concat(TransformPriv::As<SkM44>(fTransform));
    this->INHERITED::onRender(canvas, ctx);
}
```
渲染时保存 Canvas 状态，将变换矩阵（始终以 4x4 形式）concat 到 Canvas 上，然后渲染子节点。

### TransformEffect 命中测试

```cpp
const RenderNode* TransformEffect::onNodeAt(const SkPoint& p) const {
    const auto p4 = TransformPriv::As<SkM44>(fTransform).map(p.fX, p.fY, 0, 0);
    return this->INHERITED::onNodeAt({p4.x, p4.y});
}
```
将测试点通过变换矩阵映射后传递给子节点。使用 4x4 映射确保 3D 变换也能正确处理。

### TransformEffect 重新验证

```cpp
SkRect TransformEffect::onRevalidate(InvalidationController* ic, const SkMatrix& ctm) {
    fTransform->revalidate(ic, ctm);
    const auto m = TransformPriv::As<SkMatrix>(fTransform);
    auto bounds = this->INHERITED::onRevalidate(ic, SkMatrix::Concat(ctm, m));
    m.mapRect(&bounds);
    return bounds;
}
```
1. 先 revalidate 变换节点
2. 以组合后的 CTM（ctm * m）revalidate 子节点
3. 用变换矩阵映射子节点边界（从本地坐标转到父坐标）

注意 TODO 注释表明当前的 revalidation 管道尚未完全支持 4x4 矩阵。

### Concat 的失效管理

```cpp
Concat(sk_sp<Transform> a, sk_sp<Transform> b) {
    this->observeInval(fA);
    this->observeInval(fB);
}
~Concat() {
    this->unobserveInval(fA);
    this->unobserveInval(fB);
}
```
Concat 监听两个子变换的失效事件。Inverse 类似，只监听一个。

### 逆矩阵容错

```cpp
if (!TransformPriv::As<T>(fT).invert(&fInverted)) {
    fInverted.setIdentity();
}
```
当矩阵不可逆时（如退化矩阵），回退为单位矩阵而非崩溃。

## 依赖关系

- `modules/sksg/include/SkSGTransform.h` -- 头文件声明
- `modules/sksg/src/SkSGTransformPriv.h` -- TransformPriv 辅助类（As<T>/Is44）
- `include/core/SkCanvas.h` -- Canvas 操作
- `include/core/SkPoint.h` -- 点类型
- `include/private/base/SkAssert.h` -- 断言

## 设计模式与设计决策

1. **类型提升策略**：当 Concat 的两个输入中有任一为 4x4 时，组合结果自动提升为 4x4。这保证了精度不丢失，但 3x3 的情况则保持轻量。

2. **匿名命名空间的内部类**：Concat 和 Inverse 不暴露在头文件中，外部代码只通过 Transform 基类的工厂方法和虚函数接口使用它们。

3. **TransformPriv 友元模式**：通过友元类提供受控的内部访问，而非暴露 asMatrix/asM44 虚函数为 public。

4. **缓存重用**：Concat 的 `fComposed` 和 Inverse 的 `fInverted` 只在 revalidate 时更新，渲染时直接使用缓存值。

5. **TODO: 4x4 revalidation**：TransformEffect::onRevalidate 中降级为 SkMatrix 进行边界计算，这是一个已知的局限性。

## 性能考量

- 矩阵组合和求逆在 revalidate 时执行一次，渲染时直接使用缓存结果。
- `SkAutoCanvasRestore` 的 save/restore 开销很小。
- 4x4 矩阵路径比 3x3 稍慢，但自动类型选择确保不需要 4x4 时使用更快的 3x3 路径。
- TransformEffect 渲染时始终使用 `concat(SkM44)`，即使底层是 3x3 矩阵（会先转换为 4x4）。
- `map` 操作将 2D 点映射为 4D 点再提取 X/Y，3D 情况下有冗余计算。

## 相关文件

- `modules/sksg/include/SkSGTransform.h` -- Transform/Matrix/TransformEffect 声明
- `modules/sksg/src/SkSGTransformPriv.h` -- TransformPriv 辅助类
- `modules/sksg/include/SkSGEffectNode.h` -- EffectNode 基类
- `modules/sksg/include/SkSGNode.h` -- Node 基类和失效机制
