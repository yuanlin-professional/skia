# SkPathOpsTypes

> 源文件
> - src/pathops/SkPathOpsTypes.h
> - src/pathops/SkPathOpsTypes.cpp

## 概述

`SkPathOpsTypes` 是 Skia PathOps 模块的基础类型定义文件，提供了路径操作算法所需的核心类型、精度比较函数和全局状态管理。这个模块是整个 PathOps 系统的基石，定义了数值计算的精度标准和调试基础设施。

主要功能包括：
1. **精度比较函数**：提供多种精度级别的浮点数比较函数（基于 epsilon 和 ULP）
2. **全局状态管理**：`SkOpGlobalState` 类管理路径操作的全局状态和内存分配
3. **数学工具函数**：插值、符号判断、范围钳位等辅助函数
4. **调试基础设施**：为 PathOps 算法提供统一的调试宏和 ID 生成机制

## 架构位置

`SkPathOpsTypes` 位于 PathOps 模块的最底层，被所有其他 PathOps 组件依赖：

```
src/pathops/
├── SkPathOpsTypes.h/cpp       // 基础类型（当前模块）
├── SkPathOpsPoint.h           // 使用精度比较函数
├── SkPathOpsLine.h            // 使用精度比较函数
├── SkPathOpsQuad.h            // 使用精度比较函数
├── SkPathOpsCubic.h           // 使用精度比较函数
├── SkOpSegment.cpp            // 使用全局状态
├── SkOpContour.cpp            // 使用全局状态
└── SkOpBuilder.cpp            // 创建全局状态
```

## 主要类与结构体

### SkPathOpsMask 枚举

```cpp
enum SkPathOpsMask {
    kWinding_PathOpsMask = -1,
    kNo_PathOpsMask = 0,
    kEvenOdd_PathOpsMask = 1
};
```
定义路径填充规则的掩码值，用于路径操作的 winding 计算。

### SkOpPhase 枚举

```cpp
enum class SkOpPhase : char {
    kNoChange,        // 无变化
    kIntersecting,    // 计算交点阶段
    kWalking,         // 遍历路径阶段
    kFixWinding,      // 修正 winding 数阶段
};
```
表示路径操作算法的当前执行阶段，用于调试和状态跟踪。

### SkOpGlobalState 类

这是 PathOps 算法的全局状态管理器：

**核心成员变量:**
```cpp
SkArenaAlloc* fAllocator;         // 内存分配器
SkOpCoincidence* fCoincidence;    // 重合检测对象
SkOpContourHead* fContourHead;    // 轮廓链表头
int fNested;                       // 嵌套层级计数
bool fAllocatedOpSpan;            // 是否已分配 OpSpan
bool fWindingFailed;              // winding 计算是否失败
SkOpPhase fPhase;                 // 当前算法阶段
```

**调试成员（仅在 SK_DEBUG 下）:**
```cpp
const char* fDebugTestName;       // 测试名称
int fAngleID, fCoinID, fContourID, fPtTID, fSegmentID, fSpanID;
bool fDebugSkipAssert;            // 是否跳过断言
```

**主要方法:**
```cpp
SkOpGlobalState(SkOpContourHead* head, SkArenaAlloc* allocator
                SkDEBUGPARAMS(...));

// 访问器
SkArenaAlloc* allocator();
SkOpCoincidence* coincidence();
SkOpContourHead* contourHead();
SkOpPhase phase() const;

// 状态修改
void setPhase(SkOpPhase phase);
void setWindingFailed();
bool windingFailed() const;

// ID 生成（调试）
int nextAngleID();
int nextContourID();
int nextSegmentID();
int nextSpanID();
```

## 公共 API 函数

### ULP 比较函数

**基于 ULP（Units in the Last Place）的浮点数比较:**

```cpp
bool AlmostEqualUlps(float a, float b);
```
- 标准精度相等比较（16 ULP）
- 最常用的坐标比较函数

```cpp
bool AlmostEqualUlpsNoNormalCheck(float a, float b);
```
- 不检查非正规数的相等比较
- 用于性能关键路径

```cpp
bool AlmostEqualUlps_Pin(float a, float b);
```
- 检查有限性的相等比较
- 防止无穷大和 NaN 导致的问题

```cpp
bool AlmostDequalUlps(float/double a, float/double b);
```
- 更宽松的相等比较（16 ULP）
- 不检查非正规数，适合一般数值

```cpp
bool AlmostBequalUlps(float a, float b);
```
- 用于 between 运算的相等比较（2 ULP）
- 更严格的精度要求

```cpp
bool AlmostPequalUlps(float a, float b);
```
- 中等精度相等比较（8 ULP）

```cpp
bool RoughlyEqualUlps(float a, float b);
```
- 粗略相等比较（256 ULP）
- 用于快速筛选

**不相等比较:**
```cpp
bool NotAlmostEqualUlps(float a, float b);
bool NotAlmostEqualUlps_Pin(float a, float b);
bool NotAlmostDequalUlps(float/double a, float/double b);
```

**大小比较:**
```cpp
bool AlmostLessUlps(float a, float b);
bool AlmostLessOrEqualUlps(float a, float b);
```

**范围比较:**
```cpp
bool AlmostBetweenUlps(float a, float b, float c);
```
- 检查 b 是否在 a 和 c 之间（考虑精度）

**距离计算:**
```cpp
int UlpsDistance(float a, float b);
```
- 返回两个浮点数的 ULP 距离
- 用于调试和精度分析

### Epsilon 比较函数

**零值判断:**
```cpp
inline bool approximately_zero(double x);
inline bool precisely_zero(double x);
inline bool precisely_subdivide_zero(double x);
inline bool approximately_zero_half(double x);
inline bool approximately_zero_double(double x);
inline bool approximately_zero_orderable(double x);
inline bool approximately_zero_squared(double x);
inline bool approximately_zero_sqrt(double x);
inline bool roughly_zero(double x);
```

每个函数使用不同的 epsilon 阈值，适用于不同精度需求。

**相等比较:**
```cpp
inline bool approximately_equal(double x, double y);
inline bool precisely_equal(double x, double y);
inline bool approximately_equal_half(double x, double y);
inline bool approximately_equal_double(double x, double y);
inline bool approximately_equal_orderable(double x, double y);
```

**大小比较:**
```cpp
inline bool approximately_greater(double x, double y);
inline bool approximately_greater_or_equal(double x, double y);
inline bool approximately_lesser(double x, double y);
inline bool approximately_lesser_or_equal(double x, double y);
```

**范围比较:**
```cpp
inline bool approximately_between(double a, double b, double c);
inline bool precisely_between(double a, double b, double c);
inline bool between(double a, double b, double c);
```

**相对比较:**
```cpp
inline bool approximately_zero_when_compared_to(double x, double y);
inline bool precisely_zero_when_compared_to(double x, double y);
```

### 工具函数

**插值:**
```cpp
inline double SkDInterp(double A, double B, double t);
```
- 线性插值：A + (B - A) * t

**符号函数:**
```cpp
inline int SkDSign(double x);  // 返回 -1, 0, 1
inline int SKDSide(double x);  // 返回 0, 1, 2
inline int SkDSideBit(double x); // 返回 1, 2, 4
```

**钳位函数:**
```cpp
inline double SkPinT(double t);
```
- 将 t 值钳位到 [0, 1] 范围

**转换函数:**
```cpp
inline SkPath::Verb SkPathOpsPointsToVerb(int points);
inline int SkPathOpsVerbToPoints(SkPath::Verb verb);
```
- 点数量与路径动词之间的转换

## 内部实现细节

### ULP 比较的实现

ULP（Units in the Last Place）是一种精确的浮点数比较方法：

```cpp
static bool equal_ulps(float a, float b, int epsilon, int depsilon) {
    if (arguments_denormalized(a, b, depsilon)) {
        return true;  // 非正规数特殊处理
    }
    int aBits = SkFloatAs2sCompliment(a);
    int bBits = SkFloatAs2sCompliment(b);
    return aBits < bBits + epsilon && bBits < aBits + epsilon;
}
```

**关键设计:**
1. 将浮点数转换为二进制补码表示
2. 直接比较整数表示的差值
3. 特殊处理非正规数（接近零的极小值）

**非正规数检测:**
```cpp
static bool arguments_denormalized(float a, float b, int epsilon) {
    float denormalizedCheck = FLT_EPSILON * epsilon / 2;
    return fabsf(a) <= denormalizedCheck && fabsf(b) <= denormalizedCheck;
}
```

### Epsilon 常量定义

```cpp
const double FLT_EPSILON_CUBED = FLT_EPSILON * FLT_EPSILON * FLT_EPSILON;
const double FLT_EPSILON_HALF = FLT_EPSILON / 2;
const double FLT_EPSILON_DOUBLE = FLT_EPSILON * 2;
const double FLT_EPSILON_ORDERABLE_ERR = FLT_EPSILON * 16;
const double FLT_EPSILON_SQUARED = FLT_EPSILON * FLT_EPSILON;
const double FLT_EPSILON_SQRT = 0.00034526697709225118;
const double FLT_EPSILON_INVERSE = 1 / FLT_EPSILON;
const double DBL_EPSILON_ERR = DBL_EPSILON * 4;
const double DBL_EPSILON_SUBDIVIDE_ERR = DBL_EPSILON * 16;
const double ROUGH_EPSILON = FLT_EPSILON * 64;
const double MORE_ROUGH_EPSILON = FLT_EPSILON * 256;
const double WAY_ROUGH_EPSILON = FLT_EPSILON * 2048;
const double BUMP_EPSILON = FLT_EPSILON * 4096;
```

这些常量为不同应用场景提供了预定义的精度级别。

### 调试宏定义

```cpp
#ifdef SK_DEBUG
#define SkOPASSERT(cond) SkASSERT((this->globalState() && \
        this->globalState()->debugSkipAssert()) || (cond))
#else
#define SkOPASSERT(cond)
#endif
```

在 Debug 模式下，允许跳过断言以便进行鲁棒性测试。

## 依赖关系

**直接依赖:**
```cpp
#include "include/core/SkPath.h"
#include "include/core/SkScalar.h"
#include "include/private/base/SkFloatingPoint.h"
#include "include/private/base/SkMath.h"
#include "src/base/SkFloatBits.h"
#include "src/pathops/SkPathOpsDebug.h"
```

**被依赖:**
- 所有 PathOps 模块的文件
- 路径段、轮廓、角度等几何对象
- 路径操作算法实现

## 设计模式与设计决策

### 1. 多层次精度策略

提供多种精度级别，允许算法在不同阶段选择合适的精度：
- **ULP 比较**：最精确，用于坐标比较
- **标准 Epsilon**：用于 T 值比较（0-1 范围）
- **粗略 Epsilon**：用于快速筛选和预判断

### 2. 全局状态单例模式

`SkOpGlobalState` 作为算法执行期间的上下文对象：
- 避免在函数间传递大量参数
- 集中管理内存分配器
- 提供统一的调试接口

### 3. 内联函数优化

大量使用 `inline` 函数：
- 比较函数调用频繁，内联消除函数调用开销
- 编译器可以进行更好的优化

### 4. 条件编译的调试支持

使用宏隔离调试代码：
- Debug 构建提供详细的 ID 跟踪和断言
- Release 构建零开销

### 5. 双精度 ULP 比较的特殊处理

```cpp
bool AlmostDequalUlps(double a, double b) {
    if (fabs(a) < SK_ScalarMax && fabs(b) < SK_ScalarMax) {
        return AlmostDequalUlps(SkDoubleToScalar(a), SkDoubleToScalar(b));
    }
    return sk_ieee_double_divide(fabs(a - b), std::max(fabs(a), fabs(b)))
           < FLT_EPSILON * 16;
}
```
- 小数值转换为 float 进行 ULP 比较
- 大数值使用相对误差比较

## 性能考量

### 1. ULP 比较的效率

将浮点数转换为整数表示后进行比较：
- 避免了浮点运算的不确定性
- 整数比较速度快

### 2. 内联和宏定义

所有比较函数都是内联的，在 Release 构建中完全展开。

### 3. 非正规数的早期检测

```cpp
if (arguments_denormalized(a, b, depsilon)) {
    return true;
}
```
避免对极小数值进行复杂计算。

### 4. 位运算技巧

```cpp
inline SkPath::Verb SkPathOpsPointsToVerb(int points) {
    int verb = (1 << points) >> 1;
    return (SkPath::Verb)verb;
}
```
使用位移运算替代条件判断。

### 5. 内存分配器集中管理

使用 `SkArenaAlloc` 进行批量分配和快速释放。

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/pathops/SkPathOpsPoint.h` | 点类型定义 | 使用精度比较函数 |
| `src/pathops/SkPathOpsLine.h` | 线段类型 | 使用精度比较函数 |
| `src/pathops/SkPathOpsQuad.h` | 二次曲线类型 | 使用精度比较函数 |
| `src/pathops/SkPathOpsCubic.h` | 三次曲线类型 | 使用精度比较函数 |
| `src/pathops/SkOpSegment.h` | 路径段 | 使用全局状态 |
| `src/pathops/SkOpContour.h` | 轮廓 | 使用全局状态 |
| `src/pathops/SkOpCoincidence.h` | 重合检测 | 由全局状态管理 |
| `src/pathops/SkOpBuilder.cpp` | 路径操作构建器 | 创建全局状态 |
| `src/base/SkFloatBits.h` | 浮点数位操作 | 提供位转换函数 |
| `src/pathops/SkPathOpsDebug.h` | 调试工具 | 配合全局状态使用 |
| `include/private/base/SkMath.h` | 数学工具 | 提供基础数学函数 |
| `src/pathops/SkReduceOrder.cpp` | 曲线简化 | 大量使用精度比较 |
