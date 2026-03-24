# BruteForceCrossings.h - 暴力求交接口

> 源文件: `modules/bentleyottmann/include/BruteForceCrossings.h`

## 概述

`BruteForceCrossings.h` 声明了 `bentleyottmann` 命名空间中的暴力枚举线段交点函数 `brute_force_crossings`。该函数采用 O(n^2) 的暴力方法检查所有线段对以找出交点，主要用于小规模数据集或作为 Bentley-Ottmann 算法结果的正确性验证基准。

## 架构位置

- **上层调用者**：测试代码和验证逻辑
- **同层替代**：`BentleyOttmann1.h` 提供 O((n+k) log n) 的高效替代算法
- **依赖**：`Segment.h` 中的 `Crossing` 和 `Segment` 类型，`SkSpan` 用于只读数组视图

## 主要类与结构体

无新定义的类或结构体。使用前向声明引用 `Crossing` 和 `Segment`。

## 公共 API 函数

### `brute_force_crossings(SkSpan<const Segment> segments)`
- 接受一组只读线段，返回 `std::optional<std::vector<Crossing>>`
- 检查每一对线段是否相交，收集所有交点
- 空向量表示无交点
- 返回的 `Crossing` 结构体包含两条相交线段和交点的精确坐标
- 线段对的检查顺序为 (0,1), (0,2), ..., (0,n-1), (1,2), ..., 共 C(n,2) 对

## 内部实现细节

实现在 `BruteForceCrossings.cpp` 中，使用双重循环遍历所有线段对，调用 `intersect()` 函数检测交点。算法的核心步骤为：

1. 创建空的结果向量
2. 若线段数量少于 2，直接返回空向量
3. 外层循环从第一条线段迭代到倒数第二条
4. 内层循环从外层当前线段的下一条迭代到最后一条
5. 对每一对线段调用 `intersect` 函数
6. 若 `intersect` 返回有效的交点（`std::optional` 有值），将交叉信息加入结果

与 `bentley_ottmann_1` 不同，此函数始终返回有效结果（不返回 `nullopt`），因为 `intersect` 内部使用 64 位叉积运算，可以安全处理所有 32 位输入坐标。

## 依赖关系

- `include/core/SkSpan.h` - 只读数组视图
- `<optional>`, `<vector>` - 标准库容器
- `Crossing`, `Segment`（前向声明）

## 设计模式与设计决策

### 简单优先
提供 O(n^2) 暴力算法作为基准实现，代码简洁、正确性容易验证，适合作为 Bentley-Ottmann 算法的对比测试工具。

### 与 Bentley-Ottmann 接口一致
返回类型与 `bentley_ottmann_1` 保持一致（`std::optional<std::vector<Crossing>>`），便于结果比对。

### 前向声明的使用
头文件仅使用前向声明引用 `Crossing` 和 `Segment`，而不 `#include "Segment.h"`。这减少了编译依赖，但意味着包含此头文件的翻译单元需要自行包含 `Segment.h` 才能使用返回值中的 `Crossing` 类型。

## 性能考量

- 时间复杂度 O(n^2)，仅适用于线段数量较少的场景
- 空间复杂度 O(k)，k 为发现的交叉点数量
- 无额外数据结构开销，内存使用最小
- 每次 `intersect` 调用内部会先进行包围盒预过滤，对于大量不相交的线段对可以快速跳过
- 适合作为 10-100 条线段规模的快速验证工具
- 对于超过几百条线段的场景，应使用 `bentley_ottmann_1` 替代

### 头文件保护符
头文件使用 `QuadraticCrossings_DEFINED` 作为 include guard 名称（而非 `BruteForceCrossings_DEFINED`），这可能是历史遗留命名。

### 与 Myers 暴力枚举的差异
`bentleyottmann::brute_force_crossings` 和 `myers::brute_force_crossings` 虽然名称相同，但有重要差异：前者使用 `intersect` 计算精确交点坐标，后者使用 `s0_intersects_s1` 仅判断是否相交并通过 `CrossingAccumulator` 过滤端点交叉。

## 相关文件

- `modules/bentleyottmann/src/BruteForceCrossings.cpp` - 实现文件
- `modules/bentleyottmann/include/Segment.h` - Segment 和 Crossing 定义，以及 `intersect` 函数声明
- `modules/bentleyottmann/include/BentleyOttmann1.h` - 高效替代算法（O((n+k) log n)）
- `modules/bentleyottmann/include/Myers.h` - Myers 命名空间中的独立暴力枚举实现
- `modules/bentleyottmann/include/Point.h` - 交点坐标使用的 Point 类型
- `include/core/SkSpan.h` - 输入参数使用的只读数组视图类型
