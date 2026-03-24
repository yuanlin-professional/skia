# SkSLSampleUsage — 采样使用方式合并

> 源文件：[`src/sksl/SkSLSampleUsage.cpp`](../../src/sksl/SkSLSampleUsage.cpp)

## 概述

SkSLSampleUsage.cpp 实现了 `SampleUsage` 类的 `merge` 方法。`SampleUsage` 用于描述 SkSL 程序中对子效果（child fragment processor / shader / color filter / blender）的采样方式。`merge` 方法将两种采样使用方式合并为最具约束性的那一种，用于确定子效果最终需要的采样能力。

该文件仅 26 行，实现非常简洁。

## 架构位置

```
SkSL 运行时效果系统
  └── 采样分析
        └── SampleUsage（采样使用方式）
              ├── 头文件: include/private/SkSLSampleUsage.h
              └── 实现: src/sksl/SkSLSampleUsage.cpp（本文件）
```

`SampleUsage` 在运行时效果编译和优化中用于决定子着色器/颜色过滤器的采样策略。

## 主要类与结构体

### `SampleUsage::Kind` 枚举（定义在头文件中）

按采样复杂度递增排列：
- `kNone` — 未采样
- `kPassThrough` — 透传采样（使用输入坐标）
- `kExplicit` — 显式采样（使用指定坐标）
- `kUniformMatrix` — 矩阵变换采样（不参与 merge）

## 公共 API 函数

```cpp
SampleUsage SampleUsage::merge(const SampleUsage& other);
```
- 将当前采样使用方式与另一个合并
- 取两者中更高级别的 `Kind` 值
- 断言两者都不是 `kUniformMatrix` 类型
- 利用 `Kind` 枚举值的排序关系：`kExplicit > kPassThrough > kNone`
- 返回 `*this`（修改后的自身引用）

## 内部实现细节

### Kind 值的排序语义

```cpp
static_assert(Kind::kExplicit > Kind::kPassThrough);
static_assert(Kind::kPassThrough > Kind::kNone);
fKind = std::max(fKind, other.fKind);
```

通过 `static_assert` 确保枚举值按复杂度递增排列。`std::max` 取最大值就是取最具约束性的采样方式：
- 如果任一使用方式是 `kExplicit`，合并结果为 `kExplicit`
- 否则如果任一是 `kPassThrough`，合并结果为 `kPassThrough`
- 否则结果为 `kNone`

### kUniformMatrix 的排除

`kUniformMatrix` 表示通过 uniform 矩阵变换坐标的采样。此类型不参与 merge 操作（通过断言阻止），因为它只在特定的优化路径中使用，不应与其他采样方式合并。

## 依赖关系

- `include/private/SkSLSampleUsage.h` — `SampleUsage` 类声明和 `Kind` 枚举
- `<algorithm>` — `std::max`

## 设计模式与设计决策

- **格（Lattice）语义**：`Kind` 枚举形成一个有序格，`merge` 操作对应格上的 join（取上界）。这保证了合并操作的幂等性和交换性。
- **就地修改**：`merge` 修改 `*this` 并返回引用，支持链式调用。
- **编译时安全**：通过 `static_assert` 在编译时验证枚举值的排序关系，避免运行时错误。

## 性能考量

`merge` 操作仅包含一次 `std::max` 调用和两个断言检查，时间复杂度为 O(1)。在编译器分析阶段被频繁调用但开销可忽略。

## 相关文件

- `include/private/SkSLSampleUsage.h` — `SampleUsage` 类声明
- `src/sksl/analysis/SkSLMergeSampleUsageVisitor.cpp` — 使用 `merge` 分析采样使用方式
- `src/sksl/SkSLAnalysis.h` — 分析函数声明
