# SkSGTransformPriv - 场景图变换节点私有访问辅助类

> 源文件: `modules/sksg/src/SkSGTransformPriv.h`

## 概述

`SkSGTransformPriv.h` 定义了 `TransformPriv` 辅助类，用于在 sksg 模块内部访问 `Transform` 类的私有方法。该类提供了两个核心能力：检查变换是否为 4x4 矩阵（`Is44`），以及将变换节点转换为 `SkMatrix`（3x3）或 `SkM44`（4x4）矩阵。通过模板特化实现类型安全的矩阵提取。

## 架构位置

`TransformPriv` 位于 sksg 模块的内部实现层，与 `NodePriv` 类似，是 Skia "Priv" 模式的实例。它作为 `Transform` 基类的私有方法访问桥梁，被几何效果节点（如 `GeometryTransform`）等内部代码使用。该类不属于公共 API。

## 主要类与结构体

### `TransformPriv`
```cpp
class TransformPriv final {
public:
    static bool Is44(const sk_sp<Transform>& t) { return t->is44(); }

    template <typename T, typename = std::enable_if<std::is_same<T, SkMatrix>::value ||
                                                    std::is_same<T, SkM44>::value>>
    static T As(const sk_sp<Transform>&);
private:
    TransformPriv() = delete;
};
```

### 模板特化
```cpp
template <>
inline SkMatrix TransformPriv::As<SkMatrix>(const sk_sp<Transform>& t) {
    return t->asMatrix();
}

template <>
inline SkM44 TransformPriv::As<SkM44>(const sk_sp<Transform>& t) {
    return t->asM44();
}
```

## 公共 API 函数

| 方法 | 说明 |
|------|------|
| `static bool Is44(const sk_sp<Transform>& t)` | 检查变换是否为 4x4 矩阵 |
| `static T As<SkMatrix>(const sk_sp<Transform>& t)` | 提取 3x3 矩阵 |
| `static T As<SkM44>(const sk_sp<Transform>& t)` | 提取 4x4 矩阵 |

## 内部实现细节

- **SFINAE 约束**: `As<T>` 方法使用 `std::enable_if` 限制模板参数只能是 `SkMatrix` 或 `SkM44`，在编译时防止误用
- **内联特化**: 两个模板特化均标记为 `inline`，确保零运行时开销
- **不可实例化**: 构造函数 `= delete` 确保仅通过静态方法使用
- **3x3 vs 4x4**: `SkMatrix` 是经典的 2D 仿射变换矩阵（3x3），`SkM44` 是完整的 4x4 变换矩阵，用于支持 3D 变换效果

## 依赖关系

- **直接依赖**: `SkM44.h`（4x4 矩阵）、`SkMatrix.h`（3x3 矩阵）、`SkSGTransform.h`（`Transform` 基类）
- **被使用**: `modules/sksg/src/SkSGGeometryEffect.cpp` 中的 `GeometryTransform` 使用 `TransformPriv::As<SkMatrix>` 来提取变换矩阵

## 设计模式与设计决策

- **Priv 模式**: 与 `NodePriv` 相同的设计模式，将对私有方法的访问集中管理
- **类型安全模板**: 使用 `std::enable_if` SFINAE 在编译时确保只有合法类型可以调用 `As<T>`，比 `void*` 或运行时类型检查更安全
- **双矩阵支持**: 同时支持 2D (SkMatrix) 和 3D (SkM44) 变换，为场景图提供维度灵活性。`Is44()` 允许调用方在需要时选择适当的精度
- **`final` 修饰**: 防止继承，强制作为纯工具类使用

## 性能考量

- 所有方法均为内联静态函数，编译时完全展开，零运行时开销
- `Is44()` 是一个简单的布尔检查，可用于在 2D 场景中避免不必要的 4x4 矩阵运算
- 矩阵提取通过直接调用 `Transform` 的虚方法完成，不涉及额外的数据复制（除了返回值）

## 相关文件

- `modules/sksg/include/SkSGTransform.h` — `Transform` 基类定义
- `include/core/SkMatrix.h` — 3x3 仿射变换矩阵
- `include/core/SkM44.h` — 4x4 变换矩阵
- `modules/sksg/src/SkSGNodePriv.h` — 类似的 Priv 模式实现
- `modules/sksg/src/SkSGGeometryEffect.cpp` — 使用 `TransformPriv` 的代码
