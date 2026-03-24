# pathops - 路径布尔运算 API

## 概述

`include/pathops` 目录定义了 Skia 路径布尔运算（Path Operations）的公共 API。
路径布尔运算是计算几何中的核心功能，允许对两个或多个封闭路径执行集合运算，生成
描述相同区域的新路径。这在矢量图形编辑、剪裁、形状合成等场景中至关重要。

Skia 的路径运算模块支持五种基本的布尔运算：差集（Difference）、交集（Intersect）、
并集（Union）、异或（XOR）和反向差集（ReverseDifference）。这些运算通过全局函数
`Op()` 实现，接受两个 `SkPath` 和一个 `SkPathOp` 运算符，返回结果路径。运算过程
中会自动简化路径，将高阶曲线（三次贝塞尔）尽可能降阶为低阶曲线（二次贝塞尔或直线），
并确保输出路径由非重叠的轮廓组成。

除了基本的二元运算，模块还提供了 `Simplify()` 函数用于简化自交叉路径，将其转化为
等价的非重叠路径；`AsWinding()` 函数用于将偶奇填充规则的路径转换为等价的非零环绕
填充规则路径；以及 `SkOpBuilder` 类用于高效地批量执行路径运算，特别优化了多路径
并集操作的场景。

该模块是 Skia 中计算复杂度较高的部分之一，内部使用扫描线算法和 Bentley-Ottmann
交点检测等高级算法来正确处理路径交点和重叠区域。

## 架构图

```
+------------------------------------------------------------------+
|                       应用层                                       |
|  形状合成、剪裁、矢量图形编辑                                       |
+------------------------------------------------------------------+
         |
         v
+-------------------+-------------------+-------------------+
|   Op() 函数        |  Simplify() 函数   |  AsWinding() 函数 |
|   二元路径运算      |  路径简化           |  填充规则转换      |
+-------------------+-------------------+-------------------+
|  SkPathOp:                                                |
|  - kDifference     A - B                                  |
|  - kIntersect      A & B (交集)                           |
|  - kUnion          A | B (并集)                           |
|  - kXOR            A ^ B (异或)                           |
|  - kReverseDiff    B - A                                  |
+-----------------------------------------------------------+
         |
         v
+-------------------+
|   SkOpBuilder     |
|   批量路径运算      |
|   - add()         |  添加路径和运算符
|   - resolve()     |  计算最终结果
+-------------------+
         |
         v
+-----------------------------------------------------------+
|  内部算法                                                   |
|  - 扫描线交点检测                                           |
|  - 轮廓构建与简化                                           |
|  - 曲线降阶（三次 -> 二次 -> 直线）                          |
|  - 非重叠轮廓生成                                           |
+-----------------------------------------------------------+
```

## 目录结构

```
include/pathops/
  BUILD.bazel       # Bazel 构建配置
  SkPathOps.h       # 路径布尔运算的完整公共 API
```

## 关键类与函数

### SkPathOp - 运算类型枚举

```cpp
enum SkPathOp {
    kDifference_SkPathOp,        // 差集：从第一个路径中减去第二个路径
    kIntersect_SkPathOp,         // 交集：两个路径的重叠区域
    kUnion_SkPathOp,             // 并集：两个路径的合并区域
    kXOR_SkPathOp,               // 异或：两个路径的非重叠区域
    kReverseDifference_SkPathOp, // 反向差集：从第二个路径中减去第一个路径
};
```

### Op() - 二元路径运算

```cpp
std::optional<SkPath> Op(const SkPath& one, const SkPath& two, SkPathOp op);
```
对两个路径执行指定的布尔运算。结果路径由非重叠轮廓组成，曲线阶数尽可能简化。
运算失败时返回空的 optional。

### Simplify() - 路径简化

```cpp
std::optional<SkPath> Simplify(const SkPath& path);
```
将路径简化为等价的非重叠轮廓集合。对于自交叉或包含重叠区域的路径特别有用。
同样执行曲线降阶优化。

### AsWinding() - 填充规则转换

```cpp
std::optional<SkPath> AsWinding(const SkPath& path);
```
将使用偶奇（Even-Odd）填充规则的路径转换为等价的非零环绕（Winding）填充规则路径。
注意：对于包含自交叉或轮廓间交叉的路径，结果可能不完全等价。

### SkOpBuilder - 批量运算构建器

适用于多路径运算的优化工具，特别是多路径并集：

```cpp
class SkOpBuilder {
    void add(const SkPath& path, SkPathOp _operator);  // 添加路径和运算
    std::optional<SkPath> resolve();                     // 计算并返回结果
};
```

构建器内部优化了多次运算的执行顺序，避免中间路径的重复计算。

### TightBounds() - 紧密边界（已弃用）

```cpp
[[deprecated]] bool TightBounds(const SkPath& path, SkRect* result);
```
计算路径的精确边界矩形。现已被 `SkPath::computeTightBounds()` 替代。

## 依赖关系

- **内部依赖**：`include/core`（SkPath、SkRect）
- **内部依赖**：`include/private/base`（SkTArray、SkTDArray）
- **被依赖**：矢量图形编辑工具、路径合成、SVG 处理

## 相关文档与参考

- 路径布尔运算的经典算法（Weiler-Atherton、Greiner-Hormann 等）
- Bentley-Ottmann 扫描线交点检测算法
- SVG 路径合成操作
- 源码实现位于 `src/pathops/` 目录
