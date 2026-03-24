# SkContourMeasure

> 源文件: include/core/SkContourMeasure.h, src/core/SkContourMeasure.cpp

## 概述

`SkContourMeasure` 提供路径轮廓的测量功能,可以计算轮廓长度、获取指定距离处的位置和切线、提取路径片段等。它将路径轮廓分解为一系列线段(segment),支持精确的距离到参数映射。配合 `SkContourMeasureIter` 迭代器,可以逐个测量路径中的所有轮廓。这对于路径动画、虚线绘制、路径偏移等应用场景非常有用。

## 架构位置

`SkContourMeasure` 位于 Skia 核心公共 API(include/core),是路径处理子系统的一部分。它建立在 `SkPath` 之上,提供更高级的路径度量和操作功能。该类使用引用计数管理内存,与路径迭代器和路径构建器配合使用。

## 主要类与结构体

### SkContourMeasure

| 特性 | 说明 |
|------|------|
| 继承关系 | 继承自 `SkRefCnt` |
| 线程安全 | 不可变对象,线程安全 |
| 内存管理 | 引用计数 |

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSegments` | `const SkTDArray<Segment>` | 线段数组,记录累积距离和参数 |
| `fPts` | `const SkTDArray<SkPoint>` | 定义线段的点数组 |
| `fLength` | `const SkScalar` | 轮廓总长度 |
| `fIsClosed` | `const bool` | 轮廓是否闭合 |

### Segment (私有)

内部结构体,表示路径的一个子段:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fDistance` | `SkScalar` | 到此点的累积距离 |
| `fPtIndex` | `unsigned` | fPts 数组中的点索引 |
| `fTValue` | `unsigned : 30` | 参数 t 的整数表示 |
| `fType` | `unsigned : 2` | 段类型(line/quad/conic/cubic) |

### VerbMeasure

公开的测量数据结构:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fDistance` | `SkScalar` | 当前动词的累积距离 |
| `fVerb` | `SkPathVerb` | 动词类型 |
| `fPts` | `SkSpan<const SkPoint>` | 动词的点 |

### SkContourMeasureIter

迭代器类,用于遍历路径中的所有轮廓:

| 特性 | 说明 |
|------|------|
| 移动语义 | 支持移动构造和移动赋值 |
| RAII | 使用 unique_ptr 管理实现 |

## 公共 API 函数

### 测量查询

```cpp
SkScalar length() const;
```
- 返回轮廓的总长度

```cpp
bool isClosed() const;
```
- 检查轮廓是否闭合

### 位置和切线

```cpp
[[nodiscard]] bool getPosTan(SkScalar distance, SkPoint* position, SkVector* tangent) const;
```
- 获取指定距离处的位置和切线
- distance 自动钳位到 [0, length()]
- 返回 false 表示失败(如 NaN 输入或零长度路径)

```cpp
[[nodiscard]] bool getMatrix(SkScalar distance, SkMatrix* matrix,
                             MatrixFlags flags = kGetPosAndTan_MatrixFlag) const;
```
- 获取指定距离处的变换矩阵
- 可选择包含位置和/或切线
- 用于沿路径放置对象

**MatrixFlags 枚举:**
- `kGetPosition_MatrixFlag`: 包含位置(平移)
- `kGetTangent_MatrixFlag`: 包含切线(旋转)
- `kGetPosAndTan_MatrixFlag`: 包含位置和切线

### 路径片段提取

```cpp
[[nodiscard]] bool getSegment(SkScalar startD, SkScalar stopD, SkPathBuilder* dst,
                              bool startWithMoveTo) const;
```
- 提取 [startD, stopD] 区间的路径片段
- startD 和 stopD 自动钳位到 [0, length()]
- 如果 startD > stopD 返回 false
- `startWithMoveTo` 控制是否以 moveTo 开始

### 动词迭代

```cpp
class ForwardVerbIterator;
ForwardVerbIterator begin() const;
ForwardVerbIterator end() const;
```
- 支持 range-based for 循环
- 遍历轮廓的每个动词及其测量数据

```cpp
for (const auto verb_measure : contour_measure) {
    // verb_measure.fDistance, verb_measure.fVerb, verb_measure.fPts
}
```

## SkContourMeasureIter API

### 构造和初始化

```cpp
SkContourMeasureIter();
SkContourMeasureIter(const SkPath& path, bool forceClosed, SkScalar resScale = 1);
```
- 默认构造函数或从路径初始化
- `forceClosed`: 强制将轮廓视为闭合
- `resScale`: 控制测量精度(> 1 增加精度,可能降低速度)

```cpp
void reset(const SkPath& path, bool forceClosed, SkScalar resScale = 1);
```
- 重置迭代器到新路径

### 迭代

```cpp
sk_sp<SkContourMeasure> next();
```
- 返回下一个轮廓的测量对象
- 仅返回非零长度轮廓
- 返回 nullptr 表示迭代结束

## 内部实现细节

### 自适应递归细分

将曲线段递归细分为线段,直到满足精度要求:

```cpp
static bool quad_too_curvy(const SkPoint pts[3], SkScalar tolerance) {
    // 比较中点距离,判断是否需要继续细分
    SkScalar dist = std::max(SkScalarAbs(dx), SkScalarAbs(dy));
    return dist > tolerance;
}
```

递归深度限制为 `kMaxRecursionDepth = 8`,防止栈溢出。

### 参数 t 的整数表示

使用 30 位整数存储参数 t:

```cpp
#define kMaxTValue  0x3FFFFFFF

static inline SkScalar tValue2Scalar(int t) {
    const SkScalar kMaxTReciprocal = 1.0f / (SkScalar)kMaxTValue;
    return t * kMaxTReciprocal;
}
```

这样可以使用整数比较,避免浮点精度问题。

### 距离到线段的映射

使用二分查找定位距离对应的线段:

```cpp
template <typename T, typename K>
int SkTKSearch(const T base[], int count, const K& key);
```

然后在相邻线段之间插值计算精确的参数 t:
```cpp
*t = startT + (seg->getScalarT() - startT) * (distance - startD) / (seg->fDistance - startD);
```

### 圆锥曲线存储

圆锥曲线的权重存储在点数组中:
```cpp
// SkConic(pts[0], pts[2], pts[3], weight = pts[1].fX)
fPts.append()->set(conic.fW, 0);  // 权重存储在 pts[1].fX
fPts.append(2, pts + 1);           // 控制点和终点
```

### 修改器表

ETC1 使用预定义的修改器表加速解压缩:
```cpp
static const int kETC1ModifierTables[8][4] = {
    { 2,    8,  -2,   -8 },
    { 5,   17,  -5,  -17 },
    // ...
};
```

### 曲线段计算

对于不同类型的曲线,使用对应的计算函数:

```cpp
void SkContourMeasure_segTo(const SkPoint pts[], unsigned segType,
                            SkScalar startT, SkScalar stopT, SkPathBuilder* dst);
```

支持:
- `kLine_SegType`: 线性插值
- `kQuad_SegType`: 二次贝塞尔曲线 chopping
- `kConic_SegType`: 圆锥曲线 chopping
- `kCubic_SegType`: 三次贝塞尔曲线 chopping

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkPath` | 输入路径 |
| `SkPathBuilder` | 构建提取的路径片段 |
| `SkMatrix` | 位置和切线的矩阵表示 |
| `SkGeometry` | 曲线求值和 chopping |
| `SkPathMeasurePriv` | 私有段类型定义 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| 路径效果 | 使用轮廓测量实现虚线等效果 |
| 动画系统 | 沿路径移动对象 |
| 文本渲染 | 沿路径排列文字 |
| 自定义绘制工具 | 路径分析和操作 |

## 设计模式与设计决策

### 迭代器模式

`SkContourMeasureIter` 和 `ForwardVerbIterator` 提供标准的迭代器接口:
- 支持 range-based for 循环
- 分离路径遍历和轮廓测量
- 便于惰性计算

### 不可变对象

`SkContourMeasure` 一旦创建就不可变:
- 线程安全
- 可以缓存和重用
- 引用计数管理内存

### Pimpl 模式

`SkContourMeasureIter` 使用 `unique_ptr<Impl>` 隐藏实现:
- 减少头文件依赖
- 可以在不破坏 ABI 的情况下修改实现
- 支持移动语义

### 自适应精度

`resScale` 参数允许调整测量精度:
- 默认值(1.0)适用于大多数场景
- 高精度应用可以增加 resScale
- 简单场景可以降低 resScale 提高性能

## 性能考量

### 预计算线段

在构造时计算所有线段:
- 查询操作(getPosTan, getSegment)非常快
- 适合多次查询的场景
- 构造成本较高,但查询成本低

### 递归深度限制

限制曲线细分递归深度为 8:
- 防止病态曲线导致的栈溢出
- 对于正常曲线已经足够精确
- 可以通过 resScale 调整精度

### 二分查找

使用二分查找定位线段:
- O(log n) 时间复杂度
- 对于长路径显著提高性能

### 容差参数

使用动态容差参数:
```cpp
fTolerance = CHEAP_DIST_LIMIT * sk_ieee_float_divide(1.0f, resScale)
```
- 基于 resScale 调整细分密度
- 避免过度细分或精度不足

### 有限性检查

在关键路径检查数值稳定性:
```cpp
if (!halfPt.isFinite() || !SkIsFinite(distance)) {
    return distance;
}
```

### 零长度优化

跳过零长度的轮廓和段:
```cpp
if (distance > prevD) {
    // 仅在距离增加时添加段
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkPath.h` | 输入 | 源路径 |
| `include/core/SkPathBuilder.h` | 输出 | 构建路径片段 |
| `include/core/SkMatrix.h` | 输出 | 变换矩阵 |
| `src/core/SkGeometry.h` | 依赖 | 曲线计算 |
| `src/core/SkPathMeasurePriv.h` | 依赖 | 私有定义 |
| `src/core/SkPathPriv.h` | 依赖 | 路径迭代 |
| `include/effects/SkDashPathEffect.h` | 使用者 | 虚线效果 |
