# SkDashPath — 虚线路径效果

> 源文件: `src/utils/SkDashPath.cpp`

## 概述

`SkDashPath.cpp` 实现了 Skia 的虚线（dash）路径效果的核心算法。虚线效果是图形绘制中的常见需求，它将一条连续路径转换为按照指定间隔模式交替显示的线段序列（例如 "画 10 像素，跳 5 像素" 的重复模式）。

该模块提供了以下关键功能：
- **虚线参数计算**: 根据相位（phase）和间隔数组计算初始虚线状态
- **路径裁剪优化**: 对于直线和矩形路径，基于裁剪矩形预先裁剪以减少绘制量
- **直线特殊优化**: 对于纯直线路径，直接生成填充矩形而非描边线段
- **通用虚线过滤**: 使用 `SkPathMeasure` 沿任意路径生成虚线段

## 架构位置

```
Skia
├── include/core/
│   ├── SkPath.h              // 路径定义
│   ├── SkPathMeasure.h       // 路径测量
│   └── SkStrokeRec.h         // 描边记录
├── src/
│   ├── core/SkPathEffectBase.h   // 路径效果基类（含 DashInfo）
│   └── utils/
│       ├── SkDashPath.cpp         // 本文件
│       └── SkDashPathPriv.h       // 头文件声明
```

`SkDashPath` 是 Skia 虚线路径效果（`SkDashPathEffect`）的底层实现，被路径效果系统调用来生成虚线化后的路径。

## 主要类与结构体

### `SpecialLineRec`

```cpp
class SpecialLineRec {
    SkPoint fPts[2];       // 线段端点
    SkVector fTangent;     // 单位切线方向
    SkVector fNormal;      // 法线方向（已缩放到半宽度）
    SkScalar fPathLength;  // 线段长度
};
```

- **用途**: 处理纯直线路径的虚线化优化
- **核心思想**: 直接生成填充矩形（4 个顶点的多边形）代替描边线段，省去后续的描边处理
- **方法**:
  - `init()`: 验证路径是否为直线且满足优化条件（非 hairline、butt cap）
  - `addSegment()`: 在线段上指定距离范围内生成矩形

## 公共 API 函数

### `void SkDashPath::CalcDashParameters(...)`

- **功能**: 计算虚线的初始参数
- **参数**:
  - `phase`: 起始相位偏移
  - `intervals`: 虚线间隔数组（交替的"画"和"跳"长度）
  - `initialDashLength` (输出): 第一段虚线的剩余长度
  - `initialDashIndex` (输出): 第一段虚线在间隔数组中的索引
  - `intervalLength` (输出): 一个完整虚线周期的总长度
  - `adjustedPhase` (输出): 归一化后的相位值

### `bool SkDashPath::FilterDashPath(...)`

- **功能**: 将源路径转换为虚线路径的高级入口
- **参数**: 目标 builder、源路径、描边记录、裁剪矩形和虚线信息
- **返回值**: `true` 表示成功生成虚线路径

### `bool SkDashPath::InternalFilter(...)`

- **功能**: 虚线路径过滤的核心实现
- **流程**: 路径裁剪 -> 特殊直线优化 -> 通用虚线化

### `bool SkDashPath::ValidDashPath(...)`

- **功能**: 验证虚线参数的有效性
- **条件**: 至少 2 个间隔、偶数个间隔、无负值间隔、总长度 > 0、所有值有限

## 内部实现细节

### 相位调整

`CalcDashParameters` 中的相位调整逻辑处理负相位和超出周期的相位：
- 负相位翻转为正：`phase = len - (-phase % len)`
- 超出周期的正相位取模：`phase = phase % len`
- 浮点精度问题：处理 `phase == len` 的边界情况（对应 crbug.com/124652）

### 路径裁剪 (`cull_path`)

对于可以裁剪的路径类型（直线和矩形），在虚线化之前先进行裁剪：
1. **直线裁剪** (`clip_line`): 仅处理水平或垂直线段，将其截断到裁剪矩形范围，并保持虚线相位正确
2. **矩形裁剪**: 将矩形拆分为 4 条边分别裁剪，使用 `double` 类型累加边长以保持相位精度

### 零长度线段处理 (`adjust_zero_length_line`)

零长度线段需要特殊处理以绘制端帽（end cap）。通过给终点添加一个微小偏移量 `SK_ScalarNearlyZero`，确保 `SkPoint::Distance()` 计算出非零长度。

### 内存安全

```cpp
static constexpr SkScalar kMaxDashCount = 1000000;
```

限制最大虚线段数为 100 万，防止极端路径长度/虚线长度比率导致的内存耗尽（对应 crbug.com/165432）。

### 闭合路径处理

对于闭合路径（如矩形），需要特殊处理首尾连接：
- 跳过第一段虚线的开头部分
- 在路径结束时补上跳过的初始段
- 对于闭合矩形，还需要处理起始点处的连接角（join）

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkDashPathPriv.h` | SkDashPath 的私有头文件声明 |
| `SkPath.h` | 路径数据结构 |
| `SkPathBuilder.h` | 路径构建器 |
| `SkPathMeasure.h` | 路径测量与沿路径取段 |
| `SkStrokeRec.h` | 描边记录（宽度、cap、join） |
| `SkRect.h` | 矩形裁剪区域 |
| `SkPointPriv.h` | `RotateCCW` 向量旋转 |
| `SkPathEffectBase.h` | `DashInfo` 结构体 |
| `SkFloatingPoint.h` | `sk_ieee_float_divide`、`SkIsFinite` |
| `SkAlign.h` | `SkIsAlign2` 偶数检查 |

## 设计模式与设计决策

1. **分层优化**: 先尝试特殊路径（直线、矩形）的快速路径，再回退到通用路径测量方案。这是图形库中常见的优化策略
2. **直线矩形化**: `SpecialLineRec` 将直线的虚线化转换为填充矩形，直接省去描边步骤，这是一个显著的性能优化
3. **裁剪前置**: 在虚线化之前进行路径裁剪，可以大幅减少不可见区域的虚线段生成
4. **相位保持**: 裁剪算法使用模运算确保裁剪后的虚线模式与原始路径保持相位一致
5. **内存限制**: 硬编码的 100 万段限制防止恶意或极端输入导致内存耗尽
6. **双精度距离**: 虚线化循环中使用 `double` 精度的 `distance` 和 `dlen`，避免在极端路径长度/虚线长度比率下因单精度舍入导致的无限循环

## 性能考量

- **裁剪优化**: 对于带有裁剪矩形的直线和矩形路径，可以大幅减少需要处理的路径长度
- **直线快速路径**: 直线虚线化直接生成填充矩形，避免了 `SkPathMeasure` 的开销
- **预分配内存**: `SpecialLineRec::init()` 预估虚线段数量并调用 `dst->incReserve(n)` 预分配内存
- **内存安全**: 100 万段上限保护，约 17MB 的最大内存开销
- **双精度循环**: 使用 `double` 避免无限循环问题，在精度和性能之间做了合理权衡
- **偶数索引检查**: `is_even()` 使用位运算，效率极高

## 相关文件

- `src/utils/SkDashPathPriv.h` — SkDashPath 头文件
- `src/effects/SkDashPathEffect.cpp` — 虚线路径效果的外层封装
- `include/core/SkPathMeasure.h` — 路径测量功能
- `include/core/SkPath.h` — 路径数据结构
- `include/core/SkStrokeRec.h` — 描边记录
- `src/core/SkPathEffectBase.h` — 路径效果基类
