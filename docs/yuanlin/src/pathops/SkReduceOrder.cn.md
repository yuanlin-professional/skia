# SkReduceOrder

> 源文件
> - src/pathops/SkReduceOrder.h
> - src/pathops/SkReduceOrder.cpp

## 概述

`SkReduceOrder` 是 Skia PathOps 模块中用于简化曲线阶数的核心工具类。它的主要功能是将高阶曲线（如三次贝塞尔曲线和二次贝塞尔曲线）简化为更低阶的几何形状，包括线段、点或保持原有阶数。这种简化对于路径操作的性能优化和数值稳定性至关重要。

该类通过分析曲线的控制点来检测退化情况，例如：
- 所有控制点重合的情况（退化为点）
- 所有控制点共线的情况（退化为线段）
- 三次曲线可以精确表示为二次曲线的情况
- 垂直线或水平线的特殊情况

## 架构位置

`SkReduceOrder` 位于 PathOps 子系统的底层几何处理层：

```
src/pathops/
├── SkPathOpsTypes.h/cpp      // 基础类型和精度比较函数
├── SkPathOpsPoint.h           // 点的运算
├── SkPathOpsLine.h            // 线段定义
├── SkPathOpsQuad.h            // 二次曲线定义
├── SkPathOpsCubic.h           // 三次曲线定义
└── SkReduceOrder.h/cpp        // 曲线阶数简化（当前模块）
```

它被路径操作的各个算法调用，用于预处理输入曲线，消除退化情况，从而提高后续计算的鲁棒性。

## 主要类与结构体

### SkReduceOrder (union)

这是一个联合体（union），用于存储简化后的结果：

**枚举类型:**
```cpp
enum Quadratics {
    kNo_Quadratics,      // 不允许简化为二次曲线
    kAllow_Quadratics    // 允许三次曲线简化为二次曲线
};
```

**成员变量:**
```cpp
SkDLine fLine;    // 存储简化为线段的结果
SkDQuad fQuad;    // 存储简化为二次曲线的结果
SkDCubic fCubic;  // 存储简化为三次曲线的结果（或保持原样）
```

**核心方法:**
```cpp
// 实例方法：简化曲线并返回结果点的数量
int reduce(const SkDCubic& cubic, Quadratics);
int reduce(const SkDLine& line);
int reduce(const SkDQuad& quad);

// 静态方法：直接处理 SkPoint 数组
static SkPath::Verb Conic(const SkConic& conic, SkPoint* reducePts);
static SkPath::Verb Cubic(const SkPoint pts[4], SkPoint* reducePts);
static SkPath::Verb Quad(const SkPoint pts[3], SkPoint* reducePts);
```

## 公共 API 函数

### reduce() 系列方法

**SkDLine 版本:**
```cpp
int reduce(const SkDLine& line)
```
- 功能：简化线段，如果两个端点重合则返回1个点，否则返回2个点
- 返回值：有效点的数量（1或2）

**SkDQuad 版本:**
```cpp
int reduce(const SkDQuad& quad)
```
- 功能：简化二次贝塞尔曲线
- 检测：退化为点（所有点重合）、垂直线、水平线、一般直线
- 返回值：1（点）、2（线）或 3（保持二次曲线）

**SkDCubic 版本:**
```cpp
int reduce(const SkDCubic& cubic, Quadratics allowQuadratics)
```
- 功能：简化三次贝塞尔曲线
- 检测：退化为点、垂直线、水平线、一般直线、二次曲线（可选）
- 参数：`allowQuadratics` 控制是否尝试简化为二次曲线
- 返回值：1（点）、2（线）、3（二次曲线）或 4（保持三次曲线）

### 静态便捷方法

**Quad():**
```cpp
static SkPath::Verb Quad(const SkPoint a[3], SkPoint* reducePts)
```
- 将 `SkPoint` 数组形式的二次曲线转换为 `SkDQuad` 并简化
- 返回对应的路径动词（`kMove_Verb`、`kLine_Verb` 或 `kQuad_Verb`）

**Conic():**
```cpp
static SkPath::Verb Conic(const SkConic& c, SkPoint* reducePts)
```
- 简化圆锥曲线
- 如果权重为 1，则作为二次曲线处理
- 返回适当的路径动词

**Cubic():**
```cpp
static SkPath::Verb Cubic(const SkPoint a[4], SkPoint* reducePts)
```
- 特殊处理：如果四个点全部重合，直接返回 `kMove_Verb`
- 否则将三次曲线简化为更低阶形式
- 返回对应的路径动词

## 内部实现细节

### 退化检测算法

**1. 点的重合检测:**
实现使用位掩码技术快速检测哪些控制点在 X 或 Y 方向上相同：

```cpp
// 对于二次曲线（3个点）
minXSet |= 1 << index;  // 位掩码标记
if ((minXSet & 0x05) == 0x5) // 检测点0和点2是否重合
```

**2. 共线性检测:**
使用 `isLinear()` 方法检测控制点是否共线：
```cpp
if (!quad.isLinear(0, 2)) {
    return 0;
}
```

**3. 二次曲线检测（针对三次曲线）:**
使用贝塞尔曲线的数学性质进行检测：
```cpp
double dx10 = cubic[1].fX - cubic[0].fX;
double dx23 = cubic[2].fX - cubic[3].fX;
double midX = cubic[0].fX + dx10 * 3 / 2;
double sideAx = midX - cubic[3].fX;
double sideBx = dx23 * 3 / 2;
```

如果三次曲线可以精确表示为二次曲线，则：
- `midX` 和 `midY` 计算得到二次曲线的控制点
- 验证几何关系是否满足约束条件

### 精度处理

代码使用多种精度比较函数确保数值稳定性：
- `AlmostEqualUlps()` - ULP（最后一位单位）比较
- `approximately_zero()` - 近似零判断
- `approximately_equal()` - 一般近似相等
- `approximately_equal_half()` - 半精度近似相等
- `AlmostEqualUlps_Pin()` - 带钳位的 ULP 比较

对于三次曲线，使用自适应精度：
```cpp
double denom = std::max(fabs(cx), std::max(fabs(cy), ...));
double inv = 1 / denom;
if (approximately_equal_half(cx * inv, cubic[minX].fX * inv))
```

### 辅助函数

每种曲线类型都有对应的辅助函数集：
- `coincident_line()` - 处理所有点重合的情况
- `vertical_line()` - 处理垂直线
- `horizontal_line()` - 处理水平线
- `check_linear()` - 检测共线性
- `check_quadratic()` - 检测三次曲线是否为二次曲线
- `reductionLineCount()` - 计算线段的有效点数

## 依赖关系

**直接依赖:**
```cpp
#include "include/core/SkPath.h"           // SkPath::Verb 枚举
#include "src/pathops/SkPathOpsCubic.h"   // SkDCubic 类型
#include "src/pathops/SkPathOpsLine.h"    // SkDLine 类型
#include "src/pathops/SkPathOpsQuad.h"    // SkDQuad 类型
#include "src/pathops/SkPathOpsPoint.h"   // SkDPoint 类型
#include "src/pathops/SkPathOpsTypes.h"   // 精度比较函数
#include "src/core/SkGeometry.h"          // SkConic 类型
```

**被依赖:**
- PathOps 的各种路径操作算法（交集、并集、差集等）
- 路径简化算法
- 曲线分割和细分算法

## 设计模式与设计决策

### 1. 联合体设计
使用 `union` 存储不同类型的结果，节省内存空间：
- 三种曲线类型共享同一块内存
- 调用者根据返回的点数量确定实际类型

### 2. 分离的公共接口
提供两套 API：
- 实例方法：使用 `SkD*` 类型（双精度）
- 静态方法：使用 `SkPoint` 类型（单精度），更贴近 Skia 的常规使用

这种设计平衡了精度需求和易用性。

### 3. 渐进式检测策略
按照从简单到复杂的顺序进行检测：
1. 首先检测最简单的情况（所有点重合）
2. 然后检测垂直/水平线
3. 接着检测一般共线情况
4. 最后检测二次曲线降阶（如果允许）
5. 如果都不满足，保持原阶数

这种策略确保了快速路径优先执行，提高了平均性能。

### 4. 可配置的简化级别
`Quadratics` 枚举允许调用者控制是否尝试将三次曲线简化为二次曲线，提供了灵活性和性能控制。

## 性能考量

### 1. 早期退出
使用位掩码快速判断退化情况，避免复杂的数值计算：
```cpp
if (minXSet == 0x7) {  // 0x7 = 0b111，表示三个点都相同
    return vertical_line(quad, fQuad);
}
```

### 2. 自适应精度
根据坐标值的大小调整比较精度，避免在大范围坐标下出现误判：
```cpp
double denom = std::max(fabs(cx), std::max(fabs(cy), ...));
double inv = 1 / denom;
```

### 3. 内联友好的设计
小函数和简单的控制流有利于编译器内联优化。

### 4. 避免不必要的拷贝
使用引用传递大型对象，减少内存拷贝开销。

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/pathops/SkPathOpsTypes.h` | 定义精度比较函数 | 提供数值比较工具 |
| `src/pathops/SkPathOpsLine.h` | 定义 `SkDLine` 类型 | 简化结果类型 |
| `src/pathops/SkPathOpsQuad.h` | 定义 `SkDQuad` 类型 | 输入和简化结果类型 |
| `src/pathops/SkPathOpsCubic.h` | 定义 `SkDCubic` 类型 | 输入类型 |
| `src/pathops/SkPathOpsPoint.h` | 定义 `SkDPoint` 类型 | 点运算支持 |
| `src/core/SkGeometry.h` | 定义 `SkConic` 类型 | 圆锥曲线支持 |
| `include/core/SkPath.h` | 定义路径动词枚举 | 返回值类型 |
| `src/pathops/SkOpSegment.cpp` | 路径段操作 | 调用曲线简化 |
| `src/pathops/SkOpBuilder.cpp` | 路径构建器 | 使用简化功能 |
| `src/pathops/SkPathOpsSimplify.cpp` | 路径简化 | 依赖曲线简化 |
