# SkSGTransform -- 场景图变换节点

> 源文件: `modules/sksg/include/SkSGTransform.h`

## 概述

`SkSGTransform.h` 定义了 Skia Scene Graph (sksg) 模块中的变换体系，包括变换基类 `Transform`、模板化的具体矩阵节点 `Matrix<T>` 以及将变换应用到渲染子树的效果节点 `TransformEffect`。这套变换体系支持 2D（`SkMatrix`）和 3D（`SkM44`）两种矩阵类型，并提供变换组合（Concat）和逆变换（Inverse）的工厂方法，是场景图中实现空间变换的核心基础设施。

## 架构位置

变换节点在 sksg 的节点层次中处于中间层：

```
Node (基类)
├── Transform (变换数据节点，继承自 Node)
│   └── Matrix<T> (具体矩阵存储)
├── RenderNode (可渲染节点基类)
│   └── EffectNode (效果节点基类)
│       └── TransformEffect (将 Transform 绑定到渲染子树)
```

`Transform` 本身不参与渲染，仅存储和管理变换矩阵数据。`TransformEffect` 将变换数据与渲染子树关联，在渲染时将矩阵应用到 Canvas 上。这种数据与效果分离的设计允许多个效果节点共享同一个变换数据节点。

## 主要类与结构体

### `Transform`
```cpp
class Transform : public Node {
public:
    static sk_sp<Transform> MakeConcat(sk_sp<Transform> a, sk_sp<Transform> b);
    static sk_sp<Transform> MakeInverse(sk_sp<Transform> t);
protected:
    virtual bool is44() const = 0;
    virtual SkMatrix asMatrix() const = 0;
    virtual SkM44    asM44() const = 0;
};
```
变换基类，定义了获取矩阵和判断矩阵维度的纯虚接口。提供两个静态工厂方法用于创建组合变换和逆变换。

### `Matrix<T>`
```cpp
template <typename T>
class Matrix final : public Transform {
public:
    static sk_sp<Matrix> Make(const T& m);
    SG_ATTRIBUTE(Matrix, T, fMatrix)
};
```
模板化的具体矩阵节点。`T` 可以是 `SkMatrix`（3x3，2D 变换）或 `SkM44`（4x4，3D 变换）。通过 SFINAE 限制只接受这两种类型。`SG_ATTRIBUTE` 宏自动生成 `getMatrix()`/`setMatrix()` 方法，设值时自动触发失效。

### `TransformEffect`
```cpp
class TransformEffect final : public EffectNode {
public:
    static sk_sp<TransformEffect> Make(sk_sp<RenderNode> child, sk_sp<Transform> transform);
    static sk_sp<TransformEffect> Make(sk_sp<RenderNode> child, const SkMatrix& m);
    const sk_sp<Transform>& getTransform() const;
};
```
将 `Transform` 绑定到渲染子节点的效果节点。渲染时在 Canvas 上应用变换矩阵，然后渲染子节点。提供两个工厂方法：一个接受现有的 Transform 节点，另一个直接接受 SkMatrix 值（内部创建 Matrix 节点）。

## 公共 API 函数

### `Transform::MakeConcat(a, b)`
创建组合变换 T' = A x B。如果任一输入为 null，返回另一个。根据输入是否包含 4x4 矩阵自动选择 Concat 类型。

### `Transform::MakeInverse(t)`
创建逆变换 T' = Inv(T)。如果输入为 null，返回 nullptr。

### `TransformEffect::Make(child, transform)`
创建变换效果节点。child 和 transform 都不能为 null，否则返回 nullptr。通过 `sk_sp` 移动语义接管所有权。

### `TransformEffect::Make(child, m)`
便捷重载，直接接受 `SkMatrix` 值。内部先调用 `Matrix<SkMatrix>::Make(m)` 创建矩阵节点，再调用第一个重载。

### `Matrix<T>::Make(m)`
创建矩阵节点，接受初始矩阵值。返回 `sk_sp<Matrix<T>>`。

### `Matrix<T>::getMatrix() / setMatrix()`
通过 `SG_ATTRIBUTE` 宏自动生成。`setMatrix` 在新矩阵与旧矩阵不等时触发节点失效，驱动 TransformEffect 重新验证。

### `TransformEffect::getTransform()`
返回内部 `Transform` 节点的常量引用，允许外部代码查询但不修改变换。

## 内部实现细节

- **kBubbleDamage_Trait**：`Transform` 构造时传入 `kBubbleDamage_Trait`，表示变换节点不直接产生损坏（damage），而是通过祖先的 TransformEffect 传播。这是因为变换本身没有视觉输出，只有通过 TransformEffect 作用于渲染子树时才会产生可见的变化。

- **is44() 编译期判定**：`is44()` 方法通过 `std::is_same` 在编译期确定矩阵类型。对于 `Matrix<SkMatrix>` 实例，`is44()` 始终返回 `false`；对于 `Matrix<SkM44>` 实例，始终返回 `true`。`MakeConcat` 和 `MakeInverse` 在运行时通过 `TransformPriv::Is44()` 调用此方法来选择正确的内部实现类（`Concat<SkMatrix>` vs `Concat<SkM44>`）。

- **Matrix<T> 的 SFINAE 约束**：`Make` 方法通过 `std::enable_if` 模板参数限制 `T` 只能是 `SkMatrix` 或 `SkM44`，在编译时阻止其他类型的误用。

- **Matrix<T>::onRevalidate()**：返回空矩形 `SkRect::MakeEmpty()`，因为变换节点没有自己的几何边界。变换的影响体现在 TransformEffect 的边界计算中。

- **TransformEffect 渲染流程**：`onRender()` 使用 `SkAutoCanvasRestore` 保存/恢复 Canvas 状态，然后通过 `canvas->concat(SkM44)` 将变换矩阵应用到 Canvas 上（始终使用 4x4 形式以保证通用性），最后委托给 EffectNode 基类渲染子节点。

- **TransformEffect 验证流程**：`onRevalidate()` 的步骤为：(1) 先 revalidate 变换节点获取最新矩阵；(2) 将变换矩阵与当前 CTM 组合，传递给子节点进行 revalidate；(3) 用变换矩阵映射子节点边界，将结果从子节点本地坐标转换到父节点坐标系。

- **TransformEffect 命中测试**：`onNodeAt()` 使用 4x4 矩阵映射测试点，将其从父坐标系转换到子节点坐标系，然后委托给子节点。

- **Concat 和 Inverse 的缓存**：这两个内部类在 `onRevalidate` 中计算组合/逆矩阵并缓存到成员变量中。后续的 `asMatrix`/`asM44` 调用直接返回缓存值，带有 `SkASSERT(!this->hasInval())` 断言保护。

- **Inverse 的容错处理**：如果矩阵不可逆（退化矩阵），`Inverse` 将结果设为单位矩阵，而不是崩溃或返回错误值。

## 依赖关系

- `include/core/SkM44.h` -- 4x4 矩阵类型
- `include/core/SkMatrix.h` -- 3x3 矩阵类型
- `modules/sksg/include/SkSGEffectNode.h` -- TransformEffect 的基类
- `modules/sksg/include/SkSGNode.h` -- Transform 的基类
- `modules/sksg/include/SkSGRenderNode.h` -- RenderNode 相关类型
- `TransformPriv` (友元类) -- 提供访问 Transform 内部矩阵的特权接口

## 设计模式与设计决策

1. **数据/效果分离**：Transform 只是数据容器，TransformEffect 是效果应用者。这允许同一变换被多个 TransformEffect 或 GeometryTransform 共享。

2. **模板特化双类型支持**：`Matrix<SkMatrix>` 和 `Matrix<SkM44>` 在编译时生成两套代码，运行时通过 `is44()` 虚函数区分。MakeConcat/MakeInverse 会根据输入类型"提升"到 4x4。

3. **空指针安全的工厂方法**：所有 `Make` 方法检查输入参数有效性，无效时返回 nullptr 而非崩溃。

4. **友元访问模式**：通过 `TransformPriv` 友元类封装对 `asMatrix()`/`asM44()` 的访问，限制了变换数据的直接访问范围。

5. **失效传播**：TransformEffect 通过 `observeInval`/`unobserveInval` 监听变换节点的失效事件，当变换改变时自动触发重新验证。

## 性能考量

- **编译期类型判定**：`is44()` 使用 `std::is_same` 编译期常量，没有运行时分支开销。编译器可以完全消除不可达的代码路径。

- **Canvas 状态管理**：TransformEffect 在渲染时使用 `SkAutoCanvasRestore` RAII 模式，保证 Canvas 状态的正确保存和恢复，即使渲染过程中抛出异常也不会泄漏状态。

- **就地边界映射**：`onRevalidate` 中使用 `SkMatrix::mapRect(&bounds)` 就地映射边界矩形，避免了额外的临时对象分配。

- **Concat/Inverse 缓存**：组合矩阵和逆矩阵在 revalidate 时计算一次并缓存到成员变量中，后续的 `asMatrix`/`asM44` 调用直接返回缓存值，时间复杂度 O(1)。

- **类型提升的权衡**：当 3x3 和 4x4 变换组合时，自动提升为 4x4 运算。4x4 矩阵乘法和求逆比 3x3 慢约 2-3 倍，但保证了精度。对于纯 2D 场景，所有变换保持 3x3 类型可获得更好的性能。

- **TransformEffect 始终使用 SkM44 渲染**：`onRender` 中使用 `canvas->concat(SkM44)` 而非 `concat(SkMatrix)`，对纯 2D 变换有微小的额外开销（3x3 -> 4x4 转换），但保证了 3D 变换的正确性。

- **失效传播效率**：Transform 使用 `kBubbleDamage_Trait`，避免了不必要的损坏区域报告。变换改变时，损坏只在 TransformEffect 层级报告，而非在每个共享该变换的节点都报告。

## 相关文件

- `modules/sksg/src/SkSGTransform.cpp` -- Transform 体系的实现文件，包含 Concat/Inverse 内部类
- `modules/sksg/src/SkSGTransformPriv.h` -- TransformPriv 友元类定义，提供 As<T> 和 Is44 辅助方法
- `modules/sksg/include/SkSGEffectNode.h` -- EffectNode 基类
- `modules/sksg/include/SkSGGeometryEffect.h` -- GeometryTransform，几何级别的变换效果
- `modules/sksg/include/SkSGNode.h` -- Node 基类及 SG_ATTRIBUTE 宏定义
- `include/core/SkMatrix.h` -- 3x3 矩阵类型定义
- `include/core/SkM44.h` -- 4x4 矩阵类型定义
