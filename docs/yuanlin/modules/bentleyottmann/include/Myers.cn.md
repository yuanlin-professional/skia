# Myers.h - Myers 线段交点检测算法头文件

> 源文件: `modules/bentleyottmann/include/Myers.h`

## 概述

`Myers.h` 定义了基于 Myers 算法的线段交点检测系统。与同模块中的 `bentleyottmann` 命名空间不同，该文件在独立的 `myers` 命名空间中提供了一套完整的几何基础类型（`Point`、`Segment`、`Crossing`）以及两个交点检测函数。Myers 算法采用插入排序风格的扫描线方法，特别适合处理包含水平线段的场景。

## 架构位置

- **独立命名空间**：`myers` 命名空间与 `bentleyottmann` 命名空间并列，提供独立但功能类似的交点检测能力
- **被引用**：`Contour.h` 中的 `contour::Contours::segments()` 返回 `std::vector<myers::Segment>`
- **共享依赖**：使用 `bentleyottmann::Int96` 进行精确整数运算
- **实现文件**：`modules/bentleyottmann/src/Myers.cpp`

## 主要类与结构体

### `myers::Point`
```cpp
struct Point {
    int32_t x = 0;
    int32_t y = 0;
};
```
- 带默认值初始化的二维整数点
- 提供 `constexpr` 比较运算符（`<`, `==`, `!=`）
- 排序规则：(y, x) 字典序，与扫描方向一致

### `myers::Segment`
```cpp
class Segment {
public:
    constexpr Segment(Point p0, Point p1);
    const Point& upper() const;
    const Point& lower() const;
    std::tuple<int32_t, int32_t, int32_t, int32_t> bounds() const;
    bool isHorizontal() const;
    bool isVertical() const;
};
```
- 有向线段，构造时自动将点排序为 upper/lower 顺序
- 使用 `std::minmax` 确保 `fUpper < fLower`（即 upper 的 y 坐标不大于 lower）
- 断言禁止零长度线段（`fUpper != fLower`）
- 提供 `constexpr` 比较运算符
- 支持结构化绑定（通过 `std::tuple_size` 和 `std::tuple_element` 特化）

### `myers::Crossing`
```cpp
class Crossing {
public:
    Crossing(const Segment& s0, const Segment& s1);
};
```
- 记录两条相交线段，构造时自动按线段排序确保规范形式
- 使用 `std::minmax` 保证 `fHigher < fLower`，避免重复记录

## 公共 API 函数

### `myers::myers_find_crossings(SkSpan<const Segment> segments)`
使用 Myers 扫描线算法检测线段交叉。返回所有交叉的线段对（`std::vector<Crossing>`）。该函数是 Myers 算法的主入口，内部创建事件队列和扫描线，遍历所有事件并收集交叉。与 `bentleyottmann::bentley_ottmann_1` 不同，此函数不返回 `std::optional`（不会因坐标范围而失败）。

### `myers::brute_force_crossings(SkSpan<Segment> segments)`
暴力枚举法检测交叉。注意参数为非 const Span（内部需要排序和去重），与 `bentleyottmann::brute_force_crossings` 的 const 参数不同。该函数在检测前会：(1) 分离并忽略零长度线段，(2) 排序线段，(3) 去除重复线段。使用 `s0_intersects_s1` 谓词而非 `intersect` 函数检测交叉。

## 内部实现细节

### Segment 的元组支持
通过特化 `std::tuple_size<myers::Segment>` 和 `std::tuple_element<Index, myers::Segment>`，以及提供 `get<0>` 和 `get<1>` 模板函数，使 `Segment` 支持 C++17 结构化绑定：
```cpp
auto [upper, lower] = segment;
```

### Crossing 的规范化
`Crossing` 构造函数使用 `std::minmax` 对两条线段排序，确保相同的线段对无论传入顺序如何都产生相同的 `Crossing` 对象，便于去重和比较。

### 与 bentleyottmann 命名空间类型的详细对比

| 特性 | `bentleyottmann` | `myers` |
|------|-----------------|---------|
| `Point` 默认值 | 无默认初始化 | `{0, 0}` |
| `Segment` 类型 | `struct`（公有成员 p0, p1） | `class`（私有成员 fUpper, fLower） |
| `Segment` 规范化 | `upper()`/`lower()` 每次计算 | 构造时排序，存储为 fUpper/fLower |
| `Crossing` 内容 | 两条线段 + 交点坐标 | 仅两条线段（无坐标） |
| `Crossing` 规范化 | 无自动排序 | 构造时用 `minmax` 排序 |
| 比较运算符 | 非 constexpr | `constexpr` |
| 结构化绑定 | 不支持 | 通过 `std::tuple_size` 支持 |
| `Segment` 查询 | `upper()`, `lower()`, `bounds()` | 加上 `isHorizontal()`, `isVertical()` |

## 依赖关系

- `include/core/SkSpan.h` - 只读数组视图，用于函数参数
- `include/private/base/SkAssert.h` - `SkASSERT` 断言宏，用于构造函数验证
- `<algorithm>` - `std::minmax`，用于 Segment 和 Crossing 的规范化构造
- `<cstddef>` - `size_t` 类型
- `<cstdint>` - `int32_t` 坐标类型
- `<tuple>` - `std::tie` 和 `std::tuple_size/tuple_element` 特化
- `<vector>` - 返回类型 `std::vector<Crossing>`

## 设计模式与设计决策

### 不可变线段
`Segment` 的端点为私有成员，构造后不可修改，保证了数据一致性。

### 值类型规范化
`Segment` 和 `Crossing` 在构造时自动排序规范化，使得比较和去重操作简单可靠。

### 独立命名空间
`myers` 命名空间与 `bentleyottmann` 命名空间保持独立，各自定义 Point/Segment/Crossing，避免类型混淆，也允许针对不同算法优化数据结构。

### 顶层命名空间的元组特化
`std::tuple_size` 和 `std::tuple_element` 的特化必须放在顶层命名空间（`std` 命名空间），而非 `myers` 命名空间内。文件末尾的这些特化使得 `Segment` 可以像元组一样解构，这在 Myers 算法实现中大量使用。

### Segment 构造的两阶段设计
`Segment` 的公共构造函数接受两个 `Point`，通过委托构造到私有构造函数来实现排序：
```cpp
constexpr Segment(Point p0, Point p1) : Segment{std::minmax(p0, p1)} {}
```
私有构造函数接受 `std::tuple<Point, Point>` 并使用 `std::get` 提取排序后的点。这种设计确保了排序只在构造时发生一次。

### Crossing 的语义差异
与 `bentleyottmann::Crossing`（包含交点坐标）不同，`myers::Crossing` 仅记录两条交叉线段，不计算交点坐标。这是因为 Myers 算法的使用场景（路径布尔运算）只需要知道哪些线段交叉，而不需要精确的交点位置。

### Point 的默认初始化
`myers::Point` 的成员有默认值 `{0, 0}`，而 `bentleyottmann::Point` 没有。这反映了两个命名空间对未初始化安全性的不同权衡。

### inline 运算符
`Crossing` 的 `operator<` 和 `operator==` 声明为 `inline`（而非 `constexpr`），因为它们访问私有成员但不在类定义内。这些运算符在头文件中定义以避免链接问题。

### get 模板函数
`get<0>` 和 `get<1>` 是自由函数模板特化，返回 `const Point&` 引用。它们通过调用 `upper()` 和 `lower()` 成员函数实现，确保即使端点为私有成员也能通过结构化绑定访问。这些函数声明为 `inline` 以允许在头文件中定义。

## 性能考量

- `constexpr` 运算符支持编译期计算，对于常量线段可在编译时完成比较
- 比较运算符使用 `std::tie` 实现元组比较，编译器易于优化为直接的成员比较
- `Segment` 构造时排序的开销可忽略不计（仅两个点的比较和可能的交换）
- 元组支持（结构化绑定）是零开销抽象，不引入运行时间接引用
- `Point` 默认初始化为 `{0, 0}` 确保未初始化使用不会产生未定义行为
- `Crossing` 使用 `std::minmax` 而非手动比较交换，编译器可以优化为条件移动指令
- `Segment` 类大小为 16 字节（两个 Point），适合在向量中连续存储，缓存友好

## 相关文件

- `modules/bentleyottmann/src/Myers.cpp` - 完整算法实现（包含 EventQueue、SweepLine、CrossingAccumulator 内部类）
- `modules/bentleyottmann/include/Int96.h` - 精确 96 位整数运算（Myers.cpp 中的 `s0_less_than_s1_at_y` 使用）
- `modules/bentleyottmann/include/Contour.h` - 使用 `myers::Segment` 的轮廓类
- `modules/bentleyottmann/include/BentleyOttmann1.h` - 替代交叉检测算法（bentleyottmann 命名空间）
- `modules/bentleyottmann/include/Segment.h` - bentleyottmann 命名空间中的对应 Segment/Crossing 类型（对比参考）
- `modules/bentleyottmann/include/BruteForceCrossings.h` - bentleyottmann 命名空间中的暴力枚举（对比参考）
- `modules/bentleyottmann/include/Point.h` - bentleyottmann 命名空间中的 Point 类型（对比参考）
