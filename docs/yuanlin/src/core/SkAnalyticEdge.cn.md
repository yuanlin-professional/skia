# SkAnalyticEdge

> 源文件
> - src/core/SkAnalyticEdge.h
> - src/core/SkAnalyticEdge.cpp

## 概述

`SkAnalyticEdge` 是 Skia 图形库中用于分析式抗锯齿（Analytic Anti-Aliasing, AAA）路径填充的边缘表示类。它通过精确的数学计算和智能的 Y 坐标对齐，在不增加采样率的情况下实现高质量的抗锯齿效果，相比传统超采样方法显著提升性能。

## 架构位置

`SkAnalyticEdge` 位于 Skia 核心渲染流水线的路径光栅化层，专门用于分析式抗锯齿渲染器。它与传统的 `SkEdge` 并行存在，提供更高性能的抗锯齿替代方案。

```
Skia Core
  └── Path Rasterization
      ├── Analytic Anti-Aliasing (AAA)
      │   ├── SkAnalyticEdge (直线边缘)
      │   ├── SkAnalyticQuadraticEdge (二次曲线边缘)
      │   └── SkAnalyticCubicEdge (三次曲线边缘)
      └── Traditional Edge (传统超采样)
          └── SkEdge
```

## 主要类与结构体

### SkAnalyticEdge

**继承关系**
- 基类，被 `SkAnalyticQuadraticEdge` 和 `SkAnalyticCubicEdge` 继承

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fNext` | `SkAnalyticEdge*` | 边缘链表的下一个节点 |
| `fPrev` | `SkAnalyticEdge*` | 边缘链表的前一个节点 |
| `fX` | `SkFixed` | 当前 X 坐标（16.16 定点数） |
| `fDX` | `SkFixed` | X 坐标的斜率（dx/dy） |
| `fUpperX` | `SkFixed` | 边缘起始点的 X 坐标 |
| `fY` | `SkFixed` | 当前 Y 坐标 |
| `fUpperY` | `SkFixed` | 边缘的上边界 Y 坐标 |
| `fLowerY` | `SkFixed` | 边缘的下边界 Y 坐标 |
| `fDY` | `SkFixed` | Y 坐标的倒数斜率（dy/dx，用于梯形渲染） |
| `fEdgeType` | `Type` | 边缘类型（kLine/kQuad/kCubic） |
| `fCurveCount` | `int8_t` | 曲线细分计数（Quad 为正，Cubic 为负） |
| `fCurveShift` | `uint8_t` | 曲线细分的位移量 |
| `fWinding` | `Winding` | 绕向（顺时针/逆时针） |

### SkAnalyticQuadraticEdge

**继承关系**
- 继承自 `SkAnalyticEdge`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fQx`, `fQy` | `SkFixed` | 二次曲线当前位置 |
| `fQDx`, `fQDy` | `SkFixed` | 一阶差分（速度） |
| `fQDDx`, `fQDDy` | `SkFixed` | 二阶差分（加速度） |
| `fQLastX`, `fQLastY` | `SkFixed` | 曲线终点坐标 |
| `fSnappedX`, `fSnappedY` | `SkFixed` | 对齐后的坐标（用于加速填充） |

### SkAnalyticCubicEdge

**继承关系**
- 继承自 `SkAnalyticEdge`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCx`, `fCy` | `SkFixed` | 三次曲线当前位置 |
| `fCDx`, `fCDy` | `SkFixed` | 一阶差分 |
| `fCDDx`, `fCDDy` | `SkFixed` | 二阶差分 |
| `fCDDDx`, `fCDDDy` | `SkFixed` | 三阶差分 |
| `fCLastX`, `fCLastY` | `SkFixed` | 曲线终点坐标 |
| `fSnappedY` | `SkFixed` | 对齐后的 Y 坐标 |
| `fCubicDShift` | `uint8_t` | 一阶差分的专用位移量 |

## 公共 API 函数

### SkAnalyticEdge 核心方法

**setLine(const SkPoint& p0, const SkPoint& p1)**
- **功能**: 从两个端点初始化直线边缘
- **返回**: 成功返回 true，零高度线返回 false
- **处理**: 自动确保 Y 坐标递增，调整绕向

**updateLine(SkFixed ax, SkFixed ay, SkFixed bx, SkFixed by, SkFixed slope)**
- **功能**: 用预计算的斜率更新直线参数（性能优化版本）
- **用途**: 被曲线细分使用，避免重复计算斜率
- **返回**: 成功返回 true，零高度线返回 false

**update(SkFixed last_y)**
- **功能**: 更新边缘到下一个片段（多态方法）
- **行为**: 根据 `fCurveCount` 分发到 Quad 或 Cubic 的更新方法
- **返回**: 如果还有更多片段返回 true

**goY(SkFixed y)**
- **功能**: 将边缘的当前位置移动到指定 Y 坐标
- **优化**: 检测连续 Y+1 的情况，使用加法代替乘法

**goY(SkFixed y, int yShift)**
- **功能**: 带位移量的 Y 坐标移动（用于子像素精度）
- **参数**: `yShift` - Y 增量的位移量（0 到 kDefaultAccuracy）

**SnapY(SkFixed y)**
- **功能**: 将 Y 坐标对齐到默认精度网格
- **实现**: 四舍五入到 `1/4` 像素边界（kDefaultAccuracy = 2）
- **用途**: 减少边缘碎片，加速填充算法

### SkAnalyticQuadraticEdge 方法

**setQuadratic(const SkPoint pts[3])**
- **功能**: 从三个控制点初始化二次曲线边缘
- **处理**: 自动计算细分级别，初始化前向差分
- **返回**: 成功返回 true

**setQuadraticWithoutUpdate(const SkPoint pts[3], int shift)**
- **功能**: 初始化但不更新到第一个片段（用于预处理）
- **参数**: `shift` - 抗锯齿缩放因子

**updateQuadratic()**
- **功能**: 更新到下一个曲线片段
- **特性**: 智能 Y 对齐，动态调整斜率
- **返回**: 成功生成有效片段返回 true

**keepContinuous()**
- **功能**: 维护曲线片段间的连续性
- **实现**: 同步 `fSnappedX/Y` 与 `fX/Y`

### SkAnalyticCubicEdge 方法

**setCubic(const SkPoint pts[4])**
- **功能**: 从四个控制点初始化三次曲线边缘
- **处理**: 自动计算细分级别，初始化三阶前向差分
- **返回**: 成功返回 true

**setCubicWithoutUpdate(const SkPoint pts[4], int shift)**
- **功能**: 初始化但不更新到第一个片段
- **特点**: 计算最优的 upShift 和 downShift 以避免溢出

**updateCubic()**
- **功能**: 更新到下一个三次曲线片段
- **特性**: 处理 Y 非单调情况，强制 Y 单调性
- **返回**: 成功生成有效片段返回 true

**keepContinuous()**
- **功能**: 维护三次曲线片段间的连续性

## 内部实现细节

### 前向差分法（Forward Differencing）

二次曲线表示为：`f(t) = At² + Bt + C`

前向差分：
```
fQx = C                    // 起始位置
fQDx = B + (A >> shift)    // 一阶差分（带偏置）
fQDDx = A >> (shift-1)     // 二阶差分
```

更新迭代：
```
newx = oldx + (fQDx >> shift)
fQDx += fQDDx
```

### 快速除法表（Quick Inverse Table）

为避免除法开销，使用预计算的逆表：
- 表大小：1024 项（`SK_FDot6One * 16`）
- 覆盖范围：`abs(x) <= 1024`
- 精度：误差 < 1/1024

```cpp
quick_div(a, b) = (a * quick_inverse(b)) >> 6
```

### 智能 Y 对齐策略

二次曲线更新中的对齐逻辑：
```cpp
if (SkAbs32(dy >> shift) >= SK_Fixed1 * 2 &&
    SkLeftShift((int64_t)SkAbs32(dy), 6) > SkAbs32(dx)) {
    // 条件 1: dy 足够大（至少 2 像素）
    // 条件 2: 斜率不太陡（dy 显著大于 dx）
    // 行为：平滑对齐
    newSnappedY = min(fQLastY, SkFixedRoundToFixed(newy));
} else {
    // 斜率陡峭或 dy 太小
    // 行为：网格对齐
    newSnappedY = min(fQLastY, SnapY(newy));
}
```

### 三次曲线的偏差估计

```cpp
f(1/3) = (8a + 12b + 6c + d) / 27
f(2/3) = (a + 6b + 12c + 8d) / 27
```

使用 `16/512` 近似 `1/27`，计算曲线与基线的最大偏差：
```cpp
delta = max(abs(oneThird), abs(twoThird))
```

根据 delta 决定细分级别。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkPoint.h` | 2D 点坐标 |
| `include/private/base/SkFixed.h` | 16.16 定点数运算 |
| `include/private/base/SkSafe32.h` | 安全的 32 位整数运算 |
| `include/private/base/SkMath.h` | 数学工具函数 |
| `src/core/SkFDot6.h` | 26.6 定点数（FDot6）运算 |
| `src/base/SkMathPriv.h` | 私有数学函数（如 SkCLZ） |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkScan_AAAPath.cpp` | AAA 路径扫描转换 |
| `SkAnalyticEdgeBuilder` | 构建分析式边缘列表 |
| `SkQuadClipper` | 二次曲线裁剪 |
| `SkCubicClipper` | 三次曲线裁剪 |

## 设计模式与设计决策

### 继承层次设计
- **基类**: `SkAnalyticEdge` 提供直线和通用接口
- **派生类**: `SkAnalyticQuadraticEdge` 和 `SkAnalyticCubicEdge` 添加曲线特定逻辑
- **优势**: 统一的边缘链表管理，类型特定的更新方法

### 前向差分优化
- **动机**: 避免每次迭代重新计算曲线方程
- **实现**: 用增量更新替代多项式求值
- **复杂度**: 从 O(n²) 降到 O(n)

### 定点数运算
- **选择**: 16.16 定点数代替浮点数
- **优势**: 确定性结果，无舍入误差累积
- **权衡**: 需要仔细管理溢出

### 自适应细分
- **策略**: 根据曲线的弯曲程度动态决定细分级别
- **度量**: `diff_to_shift` 计算到基线的距离
- **限制**: `MAX_COEFF_SHIFT = 6`（最多 64 个片段）

### 智能对齐策略
- **目标**: 在精度和性能间平衡
- **方法**: 陡峭边缘使用网格对齐，平缓边缘使用平滑对齐
- **效果**: 减少边缘碎片，加速填充

## 性能考量

### 优化技术

1. **快速除法表**
   - 避免整数除法（~40-100 周期）
   - 表查找 + 乘法（~5-10 周期）
   - 覆盖 99% 的常见情况

2. **前向差分法**
   - 二次曲线：每次迭代 3 次加法 + 1 次位移
   - 三次曲线：每次迭代 6 次加法 + 2 次位移
   - 相比重新计算节省 ~80% 运算

3. **智能 Y 对齐**
   - 减少边缘碎片 ~30-50%
   - 降低活动边缘表大小
   - 加速扫描线填充算法

4. **连续性优化**
   - `goY(y)` 检测 Y+1 情况，用加法代替乘法
   - 缓存友好的顺序访问

### 性能特征

| 操作 | 时间复杂度 | 说明 |
|------|-----------|------|
| setLine | O(1) | 常量时间初始化 |
| setQuadratic | O(1) | 计算细分级别，常量时间 |
| setCubic | O(1) | 计算细分级别，常量时间 |
| updateQuadratic | O(1) | 每个片段常量时间 |
| updateCubic | O(1) | 每个片段常量时间 |
| goY | O(1) | 简单算术 |

### 内存占用

| 类型 | 大小 | 说明 |
|------|------|------|
| SkAnalyticEdge | ~56 字节 | 基本边缘 |
| SkAnalyticQuadraticEdge | ~96 字节 | 二次曲线边缘 |
| SkAnalyticCubicEdge | ~112 字节 | 三次曲线边缘 |

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkEdge.h` | 替代方案 | 传统超采样边缘 |
| `src/core/SkScan_AAAPath.cpp` | 使用者 | AAA 路径扫描转换 |
| `src/core/SkFDot6.h` | 依赖 | FDot6 定点数运算 |
| `src/core/SkQuadClipper.h` | 协作 | 二次曲线裁剪 |
| `src/core/SkCubicClipper.h` | 协作 | 三次曲线裁剪 |
| `include/private/base/SkFixed.h` | 依赖 | Fixed 定点数运算 |
