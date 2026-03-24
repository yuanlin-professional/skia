# BruteForceCrossings.cpp - 暴力线段交点检测实现

> 源文件: `modules/bentleyottmann/src/BruteForceCrossings.cpp`

## 概述

`BruteForceCrossings.cpp` 实现了 `bentleyottmann` 命名空间中的暴力枚举线段交点检测函数 `brute_force_crossings`。该实现使用 O(n^2) 的双重循环遍历所有线段对，调用 `intersect` 函数检测每一对线段是否相交，将找到的交点收集并返回。

## 架构位置

- **头文件**：`modules/bentleyottmann/include/BruteForceCrossings.h`
- **调用者**：主要用于测试验证 Bentley-Ottmann 算法的正确性
- **依赖**：`Segment.h` 中的 `intersect` 函数完成实际的交点计算

## 主要类与结构体

无新定义。使用 `Segment`、`Crossing` 和 `intersect` 函数。

## 公共 API 函数

### `brute_force_crossings(SkSpan<const Segment> segments)`
- 当线段数量少于 2 时，直接返回空向量
- 使用两层循环遍历所有 C(n,2) 个线段对
- 对每一对调用 `intersect`，若返回有效值则记录交叉
- 始终返回有效结果（不返回 `nullopt`）

## 内部实现细节

```cpp
for (auto i0 = segments.begin(); i0 != segments.end() - 1; ++i0) {
    for (auto i1 = i0 + 1; i1 != segments.end(); ++i1) {
        if (auto possiblePoint = intersect(*i0, *i1)) {
            answer.push_back({*i0, *i1, possiblePoint.value()});
        }
    }
}
```
- 内层循环从 `i0 + 1` 开始，避免重复检测和自比较
- `intersect` 返回 `std::optional<Point>`，使用 `if` 初始化语句简洁处理
- 每个交叉记录包含两条原始线段和交点坐标

## 依赖关系

- `modules/bentleyottmann/include/BruteForceCrossings.h` - 头文件
- `modules/bentleyottmann/include/Segment.h` - `Segment`、`Crossing`、`intersect`
- `<optional>`, `<vector>` - 标准库

## 设计模式与设计决策

### 参考实现
作为正确性显而易见的参考实现，用于验证更复杂的 Bentley-Ottmann 算法。代码极其简洁，逻辑一目了然。

### 无失败路径
与 `bentley_ottmann_1` 不同，此函数不检查坐标范围，始终返回有效结果。`intersect` 函数内部使用 64 位运算可以安全处理 32 位输入。

### 返回类型分析
虽然返回类型为 `std::optional<std::vector<Crossing>>`，但此实现始终返回有效值。`optional` 包装仅为了与 `bentley_ottmann_1` 的返回类型保持一致。调用者可以安全地直接解引用返回值。

### 与 myers::brute_force_crossings 的区别
`bentleyottmann::brute_force_crossings` 接受 `const` 线段数组，不修改输入数据，且使用 `intersect` 函数计算精确交点坐标。而 `myers::brute_force_crossings` 接受非 const 数组（内部排序去重），使用 `s0_intersects_s1` 谓词仅判断是否相交。

## 性能考量

- 时间复杂度：O(n^2)，每对线段调用一次 `intersect`
- 空间复杂度：O(k)，k 为交叉点数量
- 无额外数据结构开销，仅使用一个结果向量
- `intersect` 内部会先做包围盒预过滤，对于大部分不相交的线段对可以在几次整数比较内返回
- 输入为 `SkSpan<const Segment>`，不拷贝输入数据

### 迭代器使用
使用 `SkSpan` 的迭代器（`begin()`/`end()`）而非索引下标遍历线段，代码风格更符合现代 C++ 惯用法。`segments.end() - 1` 计算安全，因为前置条件检查 `segments.size() >= 2` 确保数组至少有两个元素。

### C++17 特性使用
`if (auto possiblePoint = intersect(*i0, *i1))` 使用 C++17 的 if-with-initializer 语法，将 optional 的创建和有效性检查合并为一个语句，简洁且无临时变量泄漏。

## 相关文件

- `modules/bentleyottmann/include/BruteForceCrossings.h` - 头文件
- `modules/bentleyottmann/include/Segment.h` - 交点计算函数和数据类型
- `modules/bentleyottmann/src/BentleyOttmann1.cpp` - 高效替代实现（Bentley-Ottmann 算法）
- `modules/bentleyottmann/src/Myers.cpp` - Myers 命名空间中的暴力枚举实现（使用不同的相交谓词）
