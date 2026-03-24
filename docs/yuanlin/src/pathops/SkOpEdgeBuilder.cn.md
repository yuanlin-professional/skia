# SkOpEdgeBuilder - 路径到操作数据结构的转换器

> 源文件：[src/pathops/SkOpEdgeBuilder.h](../../../../src/pathops/SkOpEdgeBuilder.h)、[src/pathops/SkOpEdgeBuilder.cpp](../../../../src/pathops/SkOpEdgeBuilder.cpp)

## 概述

`SkOpEdgeBuilder` 是 Skia 路径操作模块的输入处理器，负责将 `SkPath` 转换为 PathOps 内部使用的操作数据结构（`SkOpContour` 链表）。在转换过程中，它执行预处理（降阶、退化消除、微小坐标清零、复杂三次曲线分割）以确保后续的交点计算和布尔运算能够在数值稳定的条件下执行。

## 架构位置

```
用户输入
  └── SkPath (一条或两条路径)
        ↓
  SkOpEdgeBuilder (转换和预处理) ← 本文件
        ↓
  SkOpContourHead → SkOpContour → SkOpSegment
        ↓
  PathOps 核心算法 (交叉检测, 缠绕数, 布尔运算)
```

`SkOpEdgeBuilder` 是 PathOps 处理流水线的第一个阶段，将用户提供的路径数据规范化为内部表示。

## 主要类与结构体

### `SkOpEdgeBuilder`
路径转换器。

**关键成员变量：**
- `fGlobalState`：全局状态指针。
- `fPath`：当前处理的路径。
- `fPathPts`：预取的控制点数组。
- `fWeights`：预取的圆锥曲线权重数组。
- `fPathVerbs`：预取的动词（verb）数组。
- `fContourBuilder`：轮廓构建器。
- `fContoursHead`：输出轮廓链表的头部。
- `fXorMask[2]`：两个操作数的填充规则掩码。
- `fSecondHalf`：第二个操作数在动词数组中的起始位置。
- `fOperand`：当前是否在处理第二个操作数。
- `fAllowOpenContours`：是否允许未闭合的轮廓。
- `fUnparseable`：路径是否无法解析（非有限坐标）。

## 公共 API 函数

### 构造与初始化
- 构造函数接受路径、轮廓头部和全局状态，自动调用 `init()` 进行预取。
- `init()`：设置操作数标志和填充规则掩码，执行 `preFetch()` 预处理路径。
- `addOperand(const SkPath&)`：添加第二个操作数路径。

### 处理流程
- `finish()`：执行完整的转换流程（`walk()` + `complete()`）。如果路径不可解析或转换失败，返回 false。
- `complete()`：完成当前轮廓的构建，刷新缓冲区并计算边界框。

### 查询
- `head()`：返回轮廓链表头部。
- `unparseable()`：路径是否无法解析。
- `xorMask()`：当前操作数的 XOR 掩码。

## 内部实现细节

### 预取阶段（preFetch）
`preFetch()` 将 `SkPath` 的迭代器转换为三个平坦数组（verbs、points、weights）。在此过程中执行以下预处理：

1. **有限性检查**：如果路径包含非有限浮点数，标记为不可解析。
2. **微小值清零**：`force_small_to_zero()` 将绝对值小于 `FLT_EPSILON_ORDERABLE_ERR` 的坐标设为 0，避免极小值导致数值不稳定。
3. **降阶（Reduce Order）**：
   - 二次曲线退化为直线或点时降阶。
   - 圆锥曲线在权重为 1 时降阶为二次。
   - 三次曲线退化时降阶。
4. **退化线段消除**：跳过端点近似相同的线段。
5. **轮廓闭合**：非闭合轮廓自动添加闭合线段。

### 行走阶段（walk）
`walk()` 遍历预取的数据，将其添加到 `SkOpContour` 结构中。关键处理：

1. **二次曲线分割**：当二次曲线的两个控制向量方向相反（`vec1.dot(vec2) < 0`）时，在最大曲率处分割为两段。这减少了自交叉的风险。
2. **圆锥曲线分割**：类似二次曲线，在最大曲率处分割方向相反的圆锥曲线。
3. **三次曲线复杂断裂**：使用 `SkDCubic::ComplexBreak()` 检测自交叉和高曲率区域，将三次曲线分割为最多 4 段。每段独立降阶。不可添加的退化段会被相邻段吸收。
4. **操作数切换**：当 verb 指针到达 `fSecondHalf` 位置时，自动切换到第二个操作数。
5. **轮廓管理**：遇到 move 动词时创建新轮廓，遇到 close 动词时完成当前轮廓。

### 轮廓闭合
`closeContour()` 方法在轮廓未自动闭合时添加闭合线段。如果最后一个点已经与起点近似相等，则不添加新线段而是修正最后一个点的坐标。如果最后一段是退化的（与起点重合的线段），则移除它。

### 曲线可添加性检查
`can_add_curve()` 确保非退化曲线才被添加到轮廓中。对线段要求两端点不近似相等；对 move 动词直接拒绝。

## 依赖关系

- **SkPath / SkPathPriv**：输入路径和内部迭代器。
- **SkOpContour / SkOpContourBuilder**：输出数据结构和构建器。
- **SkOpGlobalState**：全局状态。
- **SkReduceOrder**：曲线降阶（三次→二次→线段→点）。
- **SkDCubic**：`ComplexBreak` 三次曲线自交叉检测。
- **SkGeometry**：`SkChopQuadAtMaxCurvature` 二次曲线最大曲率分割。
- **SkTSort**：分割参数排序。
- **SkPathOpsPoint**：`ApproximatelyEqual` 近似相等判断。

## 设计模式与设计决策

### 两阶段处理
将路径处理分为预取（preFetch）和行走（walk）两个阶段：
- 预取阶段处理路径闭合和基本降阶，生成规范化的平坦数组。
- 行走阶段处理复杂的曲线分割和轮廓构建。

这种分离使得可以先确定第二个操作数在数据中的位置（`fSecondHalf`），并在行走时正确切换操作数标志。

### 预处理确保数值稳定性
大量的预处理（微小值清零、降阶、分割）确保后续的数值计算在稳定的条件下执行。这是 PathOps 能够处理各种实际路径（包括退化情况）的关键。

### 保守失败
`walk()` 在任何可能失败的操作上检查结果并返回 false，包括：非有限的分割结果、无法降阶的曲线等。这确保了面对异常输入时的健壮性。

## 性能考量

- **预取到平坦数组**：将 SkPath 的迭代结果预取到连续的 `SkTDArray` 中，提高后续遍历的缓存局部性。
- **条件性分割**：仅在检测到方向反转（`dot(vec1, vec2) < 0`）或复杂断裂时才分割曲线，避免不必要的开销。
- **退化消除**：预取阶段即消除退化曲线，减少后续处理的工作量。

## 相关文件

- `src/pathops/SkOpContour.h`：轮廓和轮廓构建器。
- `src/pathops/SkReduceOrder.h`：曲线降阶。
- `src/pathops/SkPathOpsCubic.h`：三次曲线复杂断裂检测。
- `src/core/SkGeometry.h`：二次曲线最大曲率计算。
- `src/pathops/SkPathWriter.h`：路径写入工具（通过 `SkOpContourBuilder`）。
