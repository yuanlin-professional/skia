# Stats - 统计计算工具

> 源文件: `tools/Stats.h`

## 概述

`Stats.h` 定义了 `Stats` 结构体,用于计算基准测试样本的统计摘要(最小值、最大值、平均值、方差、中位数)并生成 ASCII 柱状图。在 Windows 上使用点/字母字符,其他平台使用 Unicode 方块字符。

## 架构位置

属于 Skia 基准测试工具的基础组件。

## 主要类与结构体

- **`Stats`**: 统计结构体
  - `min`, `max`, `mean`, `var`, `median`: 统计值
  - `plot`: SkString 类型的 ASCII 柱状图

## 公共 API 函数

- **`Stats(samples, want_plot)`**: 构造函数,计算所有统计值并可选生成图表

## 内部实现细节

- 方差使用无偏估计(除以 n-1)
- 中位数使用排序后取中间值
- 柱状图将样本归一化到 [min, max] 范围,映射到对应的条形字符
- 使用 `sk_ieee_double_divide` 安全处理除零

## 依赖关系

- `include/core/SkString.h`
- `include/private/base/SkFloatingPoint.h`

## 设计模式与设计决策

- **平台自适应**: Windows 使用 ASCII 字符,其他平台使用 Unicode 方块
- **可选图表**: want_plot 参数控制是否生成柱状图

## 性能考量

统计计算为 O(n log n)(排序为瓶颈)。对典型基准测试样本数量(几十到几百)开销极小。

## 相关文件

- Skia 基准测试框架(bench/)
